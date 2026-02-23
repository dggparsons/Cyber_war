"""Diplomacy channel endpoints."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db, socketio
from ..models import DiplomacyChannel, Team, Message


diplomacy_bp = Blueprint("diplomacy", __name__, url_prefix="/api/diplomacy")


def _ensure_team():
    if not current_user.is_authenticated or not current_user.team_id:
        return None
    return Team.query.get(current_user.team_id)


@diplomacy_bp.get("/")
@login_required
def list_channels():
    team = _ensure_team()
    if not team:
        return jsonify([])
    channels = DiplomacyChannel.query.filter(
        (DiplomacyChannel.team_a_id == team.id) | (DiplomacyChannel.team_b_id == team.id)
    ).all()

    payload = []
    for channel in channels:
        other_id = channel.team_b_id if channel.team_a_id == team.id else channel.team_a_id
        other = Team.query.get(other_id)
        history = (
            Message.query.filter_by(channel=f"diplomacy:{channel.id}")
            .order_by(Message.created_at.desc())
            .limit(20)
            .all()
        )
        payload.append(
            {
                "channel_id": channel.id,
                "with_team": {"id": other.id, "nation_name": other.nation_name} if other else None,
                "messages": [
                    {
                        "id": m.id,
                        "content": m.content,
                        "user_id": m.user_id,
                        "display_name": m.user.display_name if m.user else None,
                        "sent_at": m.created_at.isoformat(),
                    }
                    for m in reversed(history)
                ],
            }
        )
    return jsonify(payload)


@diplomacy_bp.post("/start")
@login_required
def start_channel():
    team = _ensure_team()
    if not team:
        return jsonify({"error": "team_required"}), 400
    payload = request.get_json(silent=True) or {}
    target_id = int(payload.get("target_team_id") or 0)
    if target_id == team.id:
        return jsonify({"error": "cannot_target_self"}), 400

    pair = sorted([team.id, target_id])
    channel = DiplomacyChannel.query.filter_by(team_a_id=pair[0], team_b_id=pair[1]).first()
    if not channel:
        channel = DiplomacyChannel(team_a_id=pair[0], team_b_id=pair[1])
        db.session.add(channel)
        db.session.commit()
    return jsonify({"channel_id": channel.id})


@diplomacy_bp.post("/send")
@login_required
def send_message():
    team = _ensure_team()
    if not team:
        return jsonify({"error": "team_required"}), 400
    payload = request.get_json(silent=True) or {}
    channel_id = int(payload.get("channel_id") or 0)
    content = (payload.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content_required"}), 400

    channel = DiplomacyChannel.query.get(channel_id)
    if not channel or team.id not in {channel.team_a_id, channel.team_b_id}:
        return jsonify({"error": "channel_not_found"}), 404

    message = Message(
        team_id=team.id,
        user_id=current_user.id,
        content=content,
        channel=f"diplomacy:{channel.id}",
    )
    db.session.add(message)
    db.session.commit()

    payload = {
        "channel_id": channel.id,
        "team_id": team.id,
        "content": content,
        "display_name": current_user.display_name,
        "sent_at": message.created_at.isoformat(),
    }
    socketio.emit("diplomacy:message", payload, namespace="/team", room=f"team:{channel.team_a_id}")
    socketio.emit("diplomacy:message", payload, namespace="/team", room=f"team:{channel.team_b_id}")
    return jsonify(payload)
