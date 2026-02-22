"""GM/Admin routes."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Round
from ..services.round_manager import round_manager
from ..services.resolution import resolve_round, lock_top_proposals
from ..services.global_state import serialize_global_state, set_nuke_unlocked
from ..services.crisis import crisis_history, inject_crisis, list_available_crises, clear_crisis_state

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in {"admin", "gm"}:
            return jsonify({"error": "admin_only"}), 403
        return func(*args, **kwargs)

    return wrapper


@admin_bp.get("/rounds")
@login_required
@admin_required
def rounds_overview():
    rounds = Round.query.order_by(Round.round_number).all()
    return jsonify(
        [
            {
                "id": r.id,
                "round_number": r.round_number,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            }
            for r in rounds
        ]
    )


@admin_bp.post("/rounds/advance")
@login_required
@admin_required
def advance_round():
    active = round_manager.current_round()
    lock_top_proposals(active)
    resolve_round(active)
    new_round = round_manager.advance_round()
    return jsonify({"round": new_round.round_number})


@admin_bp.post("/rounds/start")
@login_required
@admin_required
def start_round():
    current = round_manager.start_round()
    return jsonify({"round": current.round_number})


@admin_bp.post("/rounds/reset")
@login_required
@admin_required
def reset_rounds():
    Round.query.update({Round.status: "pending", Round.started_at: None, Round.ended_at: None})
    db.session.commit()
    round_manager.reset_timer()
    return jsonify({"status": "reset"})


@admin_bp.post("/rounds/pause")
@login_required
@admin_required
def pause_round_timer():
    payload = round_manager.pause_timer()
    if not payload:
        return jsonify({"error": "timer_not_running"}), 400
    return jsonify(payload)


@admin_bp.post("/rounds/resume")
@login_required
@admin_required
def resume_round_timer():
    payload = round_manager.resume_timer()
    if not payload:
        return jsonify({"error": "timer_not_paused"}), 400
    return jsonify(payload)


@admin_bp.get("/status")
@login_required
@admin_required
def admin_status():
    return jsonify(
        {
            "global": serialize_global_state(),
            "crises": crisis_history(),
            "available_crises": list_available_crises(),
        }
    )


@admin_bp.post("/nukes/toggle")
@login_required
@admin_required
def toggle_nukes():
    payload = request.get_json(silent=True) or {}
    unlocked = bool(payload.get("unlocked"))
    state = set_nuke_unlocked(unlocked)
    return jsonify(state)


@admin_bp.post("/crisis/inject")
@login_required
@admin_required
def admin_inject_crisis():
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").upper()
    if not code:
        return jsonify({"error": "missing_code"}), 400
    try:
        crisis = inject_crisis(code, triggered_by_user_id=current_user.id)
    except ValueError:
        return jsonify({"error": "unknown_crisis"}), 400
    return jsonify(crisis)


@admin_bp.post("/crisis/clear")
@login_required
@admin_required
def admin_clear_crisis():
    clear_crisis_state()
    return jsonify(serialize_global_state())
