"""Round lifecycle manager."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import time

from flask import current_app

from ..extensions import db, socketio
from ..models import Round, IntelDrop, Team
from .resolution import lock_top_proposals
from .intel_generator import generate_intel_for_round

TimerState = Literal["idle", "running", "paused", "complete"]


class RoundManager:
    def __init__(self):
        self.round_duration = 360  # default 6 minutes
        self._timer_task = None
        self._active_round_id: int | None = None
        self._remaining: int = self.round_duration
        self._timer_state: TimerState = "idle"

    def _get_duration_for_round(self, round_number: int) -> int:
        """Return duration in seconds for a given round number from config."""
        try:
            durations = current_app.config.get("ROUND_DURATIONS", [])
        except RuntimeError:
            durations = []
        idx = round_number - 1
        if durations and 0 <= idx < len(durations):
            return durations[idx] * 60
        return 360

    def _get_round_limit(self) -> int:
        try:
            return int(current_app.config.get("ROUND_COUNT", 6))
        except RuntimeError:
            return 6

    def current_round(self) -> Round | None:
        round_obj = (
            Round.query.filter(Round.status == 'active')
            .order_by(Round.round_number)
            .first()
        )
        if round_obj:
            self._active_round_id = round_obj.id
            self.round_duration = self._get_duration_for_round(round_obj.round_number)
            if not self._timer_task and self._timer_state == "idle":
                self._start_timer(round_obj, resume_from=self._compute_remaining(round_obj))
            return round_obj

        round_obj = (
            Round.query.filter(Round.status == 'pending')
            .order_by(Round.round_number)
            .first()
        )
        if round_obj:
            round_obj.status = 'active'
            round_obj.started_at = datetime.now(timezone.utc)
            db.session.add(round_obj)
            db.session.commit()
            generate_intel_for_round(round_obj.id)
            self.round_duration = self._get_duration_for_round(round_obj.round_number)
            socketio.emit('round:started', {'round': round_obj.round_number}, namespace='/global')
            self._start_timer(round_obj)
            return round_obj

        if Round.query.count() == 0:
            round_obj = Round(round_number=1, status='active', started_at=datetime.now(timezone.utc))
            db.session.add(round_obj)
            db.session.commit()
            generate_intel_for_round(round_obj.id)
            self.round_duration = self._get_duration_for_round(round_obj.round_number)
            socketio.emit('round:started', {'round': round_obj.round_number}, namespace='/global')
            self._start_timer(round_obj)
            return round_obj
        return None

    def advance_round(self) -> Round | None:
        round_obj = self.current_round()
        if not round_obj:
            return None
        round_obj.status = 'resolved'
        round_obj.ended_at = datetime.now(timezone.utc)
        db.session.add(round_obj)

        round_limit = self._get_round_limit()
        next_round_number = round_obj.round_number + 1
        next_round: Round | None = None
        if next_round_number <= round_limit:
            next_round = Round.query.filter_by(round_number=next_round_number).first()
            if not next_round:
                next_round = Round(round_number=next_round_number, status='pending')
                db.session.add(next_round)
            next_round.status = 'active'
            next_round.started_at = datetime.now(timezone.utc)
        db.session.commit()

        self._stop_timer()
        socketio.emit('round:ended', {'round': round_obj.round_number}, namespace='/global')
        if not next_round:
            self._timer_state = "complete"
            self._remaining = 0
            self._active_round_id = None
            return None

        generate_intel_for_round(next_round.id)
        self.round_duration = self._get_duration_for_round(next_round.round_number)
        socketio.emit('round:started', {'round': next_round.round_number}, namespace='/global')
        self._start_timer(next_round)
        return next_round

    def start_round(self) -> Round | None:
        active = Round.query.filter(Round.status == 'active').first()
        if active:
            self._active_round_id = active.id
            self.round_duration = self._get_duration_for_round(active.round_number)
            if not self._timer_task and self._timer_state == "idle":
                self._start_timer(active, resume_from=self._compute_remaining(active))
            return active

        round_obj = (
            Round.query.filter(Round.status == 'pending')
            .order_by(Round.round_number)
            .first()
        )
        if not round_obj:
            if Round.query.count() == 0:
                round_obj = Round(round_number=1, status='pending')
                db.session.add(round_obj)
                db.session.commit()
            else:
                return None

        round_obj.status = 'active'
        round_obj.started_at = datetime.now(timezone.utc)
        db.session.add(round_obj)
        db.session.commit()
        generate_intel_for_round(round_obj.id)
        self.round_duration = self._get_duration_for_round(round_obj.round_number)
        socketio.emit('round:started', {'round': round_obj.round_number}, namespace='/global')
        self._start_timer(round_obj)
        return round_obj

    def pause_timer(self):
        if not self._active_round_id or self._timer_state != "running":
            return None
        self._timer_state = "paused"
        payload = self.timer_payload()
        socketio.emit('round:paused', payload, namespace='/global')
        return payload

    def resume_timer(self):
        if not self._active_round_id or self._timer_state != "paused":
            return None
        self._timer_state = "running"
        payload = self.timer_payload()
        socketio.emit('round:resumed', payload, namespace='/global')
        return payload

    def reset_timer(self):
        self._stop_timer()
        self._active_round_id = None
        self._timer_state = "idle"
        self._remaining = self.round_duration

    def timer_payload(self, round_obj: Round | None = None) -> dict:
        if round_obj is None:
            round_obj = (
                Round.query.get(self._active_round_id)
                if self._active_round_id
                else Round.query.filter(Round.status == 'active').order_by(Round.round_number).first()
            )
        if not round_obj:
            return {
                "round": 1,
                "remaining": self.round_duration,
                "duration": self.round_duration,
                "state": self._timer_state,
                "server_time": datetime.now(timezone.utc).isoformat(),
            }
        remaining = self._remaining if round_obj.id == self._active_round_id and self._timer_state != "idle" else self._compute_remaining(round_obj)
        return {
            "round": round_obj.round_number,
            "remaining": max(0, remaining),
            "duration": self.round_duration,
            "state": self._timer_state,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    def submissions_open(self, round_obj: Round | None = None) -> bool:
        round_id = round_obj.id if round_obj else self._active_round_id
        if not round_id:
            return True
        if self._active_round_id and round_id != self._active_round_id:
            return False
        return self._timer_state in {"idle", "running", "paused"}

    def _start_timer(self, round_obj: Round, resume_from: int | None = None):
        if self._timer_task and self._active_round_id == round_obj.id:
            return
        if self._timer_task and self._active_round_id != round_obj.id:
            self._stop_timer()

        self._active_round_id = round_obj.id
        self._remaining = resume_from if resume_from is not None else self.round_duration
        self._timer_state = "running"

        app = current_app._get_current_object()

        def timer_loop(round_id: int, round_number: int):
            with app.app_context():
                while self._active_round_id == round_id and self._remaining >= 0:
                    if self._timer_state == "paused":
                        time.sleep(0.25)
                        continue
                    socketio.emit(
                        'round:tick',
                        {
                            'round_id': round_id,
                            'round': round_number,
                            'remaining': self._remaining,
                            'duration': self.round_duration,
                            'state': self._timer_state,
                            'server_time': datetime.now(timezone.utc).isoformat(),
                        },
                        namespace='/global',
                    )
                    time.sleep(1)
                    if self._timer_state != "running":
                        continue
                    self._remaining -= 1
                if self._active_round_id == round_id and self._timer_state == "running":
                    self._timer_state = "complete"
                    self._remaining = 0
                    lock_top_proposals(round_id=round_id)
                    socketio.emit(
                        'round:timer_end',
                        {
                            'round_id': round_id,
                            'round': round_number,
                            'state': self._timer_state,
                            'server_time': datetime.now(timezone.utc).isoformat(),
                        },
                        namespace='/global',
                    )
                self._timer_task = None

        self._timer_task = socketio.start_background_task(timer_loop, round_obj.id, round_obj.round_number)

    def _stop_timer(self):
        if not self._timer_task:
            return
        current_task = self._timer_task
        self._active_round_id = None
        self._timer_state = "idle"
        while self._timer_task is current_task:
            time.sleep(0.05)

    def _compute_remaining(self, round_obj: Round) -> int:
        if not round_obj.started_at:
            return self.round_duration
        started = round_obj.started_at
        if started.tzinfo:
            elapsed_seconds = (datetime.now(timezone.utc) - started).total_seconds()
        else:
            elapsed_seconds = (datetime.utcnow() - started).total_seconds()
        elapsed = int(elapsed_seconds)
        return max(0, self.round_duration - elapsed)


round_manager = RoundManager()
