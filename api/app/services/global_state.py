"""Helpers for managing shared global game state."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from ..extensions import db, socketio
from ..models import GlobalState, Team


DEFAULT_THRESHOLDS = [20, 40, 60, 80]
THRESHOLD_SEVERITY = {
    20: "caution",
    40: "warning",
    60: "critical",
    80: "doom",
}


def get_global_state(create: bool = True) -> GlobalState:
    state = GlobalState.query.first()
    if state or not create:
        return state
    state = GlobalState(nuke_unlocked=False, doom_triggered=False, escalation_thresholds=DEFAULT_THRESHOLDS.copy())
    db.session.add(state)
    db.session.commit()
    return state


def serialize_global_state(state: GlobalState | None = None) -> Dict[str, Any]:
    state = state or get_global_state()
    payload = {
        "nuke_unlocked": bool(state.nuke_unlocked),
        "doom_triggered": bool(state.doom_triggered),
        "doom_message": state.doom_message,
        "active_crisis": state.active_crisis_payload,
        "last_crisis_at": state.last_crisis_at.isoformat() if state.last_crisis_at else None,
        "escalation_thresholds": state.escalation_thresholds or DEFAULT_THRESHOLDS.copy(),
        "total_escalation": compute_global_escalation(),
    }
    return payload


def set_nuke_unlocked(unlocked: bool) -> Dict[str, Any]:
    state = get_global_state()
    changed = state.nuke_unlocked != unlocked
    state.nuke_unlocked = unlocked
    db.session.add(state)
    db.session.commit()
    payload = {"nuke_unlocked": state.nuke_unlocked}
    if changed:
        _broadcast("game:nuke_state", payload)
    return payload


def trigger_doom(message: str | None = None) -> Dict[str, Any]:
    state = get_global_state()
    if state.doom_triggered:
        return {"doom_triggered": True, "message": state.doom_message}
    state.doom_triggered = True
    state.doom_message = message or "A catastrophic strike ended the scenario. Everyone loses."
    db.session.add(state)
    db.session.commit()
    payload = {"doom_triggered": True, "message": state.doom_message}
    _broadcast("game:over", payload)
    return payload


def clear_doom_flag():
    state = get_global_state()
    if not state.doom_triggered:
        return serialize_global_state(state)
    state.doom_triggered = False
    state.doom_message = None
    db.session.add(state)
    db.session.commit()
    return serialize_global_state(state)


def set_active_crisis(code: str, payload: Dict[str, Any]):
    state = get_global_state()
    state.active_crisis_code = code
    state.active_crisis_payload = payload
    state.last_crisis_at = datetime.now(timezone.utc)
    db.session.add(state)
    db.session.commit()
    _broadcast("crisis:injected", payload)


def clear_active_crisis():
    state = get_global_state()
    state.active_crisis_code = None
    state.active_crisis_payload = None
    db.session.add(state)
    db.session.commit()
    _broadcast("crisis:cleared", {})


def _broadcast(event: str, payload: Dict[str, Any]):
    socketio.emit(event, payload, namespace="/global")
    socketio.emit(event, payload, namespace="/team")


def compute_global_escalation() -> int:
    total = db.session.query(db.func.sum(Team.current_escalation)).scalar()
    return int(total or 0)


def pending_thresholds(state: GlobalState | None = None) -> list[int]:
    state = state or get_global_state()
    thresholds = state.escalation_thresholds or DEFAULT_THRESHOLDS.copy()
    return [value for value in thresholds if value > 0]


def mark_threshold_triggered(value: int, state: GlobalState | None = None):
    state = state or get_global_state()
    thresholds = state.escalation_thresholds or DEFAULT_THRESHOLDS.copy()
    thresholds = [v for v in thresholds if v > value]
    state.escalation_thresholds = thresholds
    db.session.add(state)
    db.session.commit()


def check_escalation_thresholds(state: GlobalState | None = None) -> list[int]:
    state = state or get_global_state()
    thresholds = pending_thresholds(state)
    if not thresholds:
        return []
    total = compute_global_escalation()
    triggered = [value for value in thresholds if total >= value]
    for value in triggered:
        mark_threshold_triggered(value, state)
        payload = {
            "threshold": value,
            "total": total,
            "severity": THRESHOLD_SEVERITY.get(value, "caution"),
        }
        _broadcast("escalation:threshold", payload)
    return triggered
