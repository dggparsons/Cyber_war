"""GM/Admin routes."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from ..extensions import db, socketio, limiter
from ..models import Round, IntelDrop, MegaChallenge, Team, User
from ..utils.passwords import hash_password
from ..services.round_manager import round_manager
from ..services.resolution import resolve_round, lock_top_proposals
from ..services.global_state import serialize_global_state, set_nuke_unlocked, clear_doom_flag
from ..services.crisis import crisis_history, inject_crisis, list_available_crises, clear_crisis_state
from ..services.proposals import build_proposal_preview
from ..services.game_reset import reset_game_state, full_reset
from ..services.world_engine import generate_round_narrative
from ..models import Action

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Default rate limit for admin endpoints
limiter.limit("30 per minute")(admin_bp)


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
    if not active:
        return jsonify({"error": "no_active_round"}), 400
    lock_top_proposals(active)
    resolve_round(active)
    new_round = round_manager.advance_round()
    if not new_round:
        return jsonify({"round": active.round_number, "status": "complete"})
    return jsonify({"round": new_round.round_number, "status": "intermission"})


@admin_bp.post("/rounds/start")
@login_required
@admin_required
def start_round():
    current = round_manager.start_round()
    if not current:
        return jsonify({"error": "no_pending_rounds"}), 400
    return jsonify({"round": current.round_number})


@admin_bp.post("/rounds/reset")
@login_required
@admin_required
def reset_rounds():
    round_count = int(current_app.config.get("ROUND_COUNT", 6))
    reset_game_state(round_count)
    round_manager.reset_timer()
    socketio.emit("game:reset", {}, namespace="/global")
    return jsonify({"status": "reset"})


@admin_bp.post("/full-reset")
@login_required
@admin_required
def admin_full_reset():
    """Full reset: wipe all game state AND remove non-admin player accounts."""
    round_count = int(current_app.config.get("ROUND_COUNT", 6))
    full_reset(round_count)
    round_manager.reset_timer()
    socketio.emit("game:reset", {}, namespace="/global")
    return jsonify({"status": "full_reset"})


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
    round_obj = round_manager.current_round()
    rounds = Round.query.order_by(Round.round_number).all()
    teams = Team.query.all()
    player_count = User.query.filter(User.role.notin_(["admin", "gm"])).count()

    team_summary = []
    for t in teams:
        members = User.query.filter_by(team_id=t.id).count()
        team_summary.append({
            "id": t.id,
            "nation_name": t.nation_name,
            "nation_code": t.nation_code,
            "members": members,
            "seat_cap": t.seat_cap,
        })

    round_summary = [
        {
            "round_number": r.round_number,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
        }
        for r in rounds
    ]

    timer_data = round_manager.timer_payload(round_obj)
    payload = {
        "global": serialize_global_state(),
        "crises": crisis_history(),
        "available_crises": list_available_crises(),
        "player_count": player_count,
        "teams": team_summary,
        "rounds": round_summary,
        "current_round": round_obj.round_number if round_obj else timer_data.get("round"),
        "timer": timer_data,
    }
    if round_obj:
        payload["proposal_preview"] = build_proposal_preview(round_obj)
    return jsonify(payload)


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


@admin_bp.post("/clear-doom")
@login_required
@admin_required
def admin_clear_doom():
    result = clear_doom_flag()
    return jsonify(result)


@admin_bp.post("/intel-drops")
@login_required
@admin_required
def create_intel_drop():
    payload = request.get_json(silent=True) or {}
    required = ("round_id", "team_id", "puzzle_type", "clue", "solution")
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    drop = IntelDrop(
        round_id=payload["round_id"],
        team_id=payload["team_id"],
        puzzle_type=payload["puzzle_type"],
        clue=payload["clue"],
        reward=payload.get("reward_type", "lifeline"),
        solution_hash=hash_password(payload["solution"]),
    )
    db.session.add(drop)
    db.session.commit()
    return jsonify(
        {
            "id": drop.id,
            "round_id": drop.round_id,
            "team_id": drop.team_id,
            "puzzle_type": drop.puzzle_type,
            "clue": drop.clue,
            "reward": drop.reward,
            "solution_hash": drop.solution_hash,
            "created_at": drop.created_at.isoformat() if drop.created_at else None,
        }
    ), 201


@admin_bp.get("/intel-drops")
@login_required
@admin_required
def list_intel_drops():
    drops = IntelDrop.query.order_by(IntelDrop.id).all()
    return jsonify(
        [
            {
                "id": d.id,
                "round_id": d.round_id,
                "team_id": d.team_id,
                "puzzle_type": d.puzzle_type,
                "clue": d.clue,
                "reward": d.reward,
                "solution_hash": d.solution_hash,
                "solved_by_team_id": d.solved_by_team_id,
                "solved_at": d.solved_at.isoformat() if d.solved_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in drops
        ]
    )


@admin_bp.post("/mega-challenge")
@login_required
@admin_required
def create_mega_challenge():
    payload = request.get_json(silent=True) or {}
    description = (payload.get("description") or "").strip()
    solution = (payload.get("solution") or "").strip()
    reward_tiers = payload.get("reward_tiers", [15, 10, 5])
    if not description or not solution:
        return jsonify({"error": "description_and_solution_required"}), 400
    challenge = MegaChallenge(
        description=description,
        solution_hash=hash_password(solution),
        reward_tiers=reward_tiers,
    )
    db.session.add(challenge)
    db.session.commit()
    return jsonify({"id": challenge.id, "description": challenge.description}), 201


@admin_bp.get("/mega-challenge")
@login_required
@admin_required
def get_mega_challenge_admin():
    challenge = MegaChallenge.query.first()
    if not challenge:
        return jsonify({"active": False})
    return jsonify({
        "active": True,
        "id": challenge.id,
        "description": challenge.description,
        "reward_tiers": challenge.reward_tiers,
    })


@admin_bp.post("/narrative/rerun")
@login_required
@admin_required
def rerun_narrative():
    """Re-generate the World Engine narrative for the current round."""
    round_obj = round_manager.current_round()
    if not round_obj:
        return jsonify({"error": "no_active_round"}), 400
    actions = Action.query.filter_by(round_id=round_obj.id).all()
    entries = []
    for a in actions:
        actor = Team.query.get(a.team_id)
        target = Team.query.get(a.target_team_id) if a.target_team_id else None
        from ..data.actions import ACTION_LOOKUP
        action_def = ACTION_LOOKUP.get(a.action_code)
        entries.append({
            "actor": actor.nation_name if actor else None,
            "target": target.nation_name if target else None,
            "action_code": a.action_code,
            "action_name": action_def.name if action_def else a.action_code,
            "success": a.success,
            "category": action_def.category if action_def else None,
        })
    from ..services.global_state import get_global_state
    global_state = get_global_state()
    round_obj.narrative = generate_round_narrative(
        round_obj.round_number, entries,
        crisis=global_state.active_crisis_payload,
    )
    db.session.add(round_obj)
    db.session.commit()
    return jsonify({"narrative": round_obj.narrative})
