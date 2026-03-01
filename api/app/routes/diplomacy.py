"""Diplomacy channel endpoints.

Channel lifecycle:  pending → accepted → (messaging)
                    pending → declined  (hidden)
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db, socketio
from ..models import DiplomacyChannel, Team, Message


diplomacy_bp = Blueprint("diplomacy", __name__, url_prefix="/api/diplomacy")


def _ensure_team():
    if not current_user.is_authenticated or not current_user.team_id:
        return None
    return db.session.get(Team, current_user.team_id)


@diplomacy_bp.get("/")
@login_required
def list_channels():
    team = _ensure_team()
    if not team:
        return jsonify([])
    channels = DiplomacyChannel.query.filter(
        ((DiplomacyChannel.team_a_id == team.id) | (DiplomacyChannel.team_b_id == team.id))
        & (DiplomacyChannel.status != "declined")
    ).all()

    payload = []
    for channel in channels:
        other_id = channel.team_b_id if channel.team_a_id == team.id else channel.team_a_id
        other = db.session.get(Team, other_id)

        # Pending channels only show to the invited team (team_b) and initiator
        is_initiator = channel.initiated_by == team.id

        history = []
        if channel.status == "accepted":
            history = (
                Message.query.filter_by(channel=f"diplomacy:{channel.id}")
                .order_by(Message.created_at.desc())
                .limit(20)
                .all()
            )

        payload.append(
            {
                "channel_id": channel.id,
                "status": channel.status,
                "is_initiator": is_initiator,
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
    body = request.get_json(silent=True) or {}
    target_id = int(body.get("target_team_id") or 0)
    if target_id == team.id:
        return jsonify({"error": "cannot_target_self"}), 400

    pair = sorted([team.id, target_id])
    channel = DiplomacyChannel.query.filter_by(team_a_id=pair[0], team_b_id=pair[1]).first()
    if channel:
        if channel.status == "declined":
            # Re-open a previously declined channel as a new request
            channel.status = "pending"
            channel.initiated_by = team.id
            db.session.commit()
        else:
            return jsonify({"channel_id": channel.id, "status": channel.status})

    if not channel:
        channel = DiplomacyChannel(
            team_a_id=pair[0], team_b_id=pair[1],
            status="pending", initiated_by=team.id,
        )
        db.session.add(channel)
        db.session.commit()

    target_team = db.session.get(Team, target_id)
    # Notify both teams
    for tid, other_tid, other_name in [
        (target_id, team.id, team.nation_name),
        (team.id, target_id, target_team.nation_name if target_team else "Unknown"),
    ]:
        socketio.emit(
            "diplomacy:channel_opened",
            {
                "channel_id": channel.id,
                "status": "pending",
                "with_team": {"id": other_tid, "nation_name": other_name},
            },
            namespace="/team",
            room=f"team:{tid}",
        )
    return jsonify({"channel_id": channel.id, "status": "pending"}), 201


@diplomacy_bp.post("/respond")
@login_required
def respond_channel():
    """Accept or decline a pending diplomacy channel."""
    team = _ensure_team()
    if not team:
        return jsonify({"error": "team_required"}), 400

    body = request.get_json(silent=True) or {}
    channel_id = int(body.get("channel_id") or 0)
    action = (body.get("action") or "").strip().lower()
    if action not in ("accept", "decline"):
        return jsonify({"error": "action must be 'accept' or 'decline'"}), 400

    channel = db.session.get(DiplomacyChannel, channel_id)
    if not channel or team.id not in {channel.team_a_id, channel.team_b_id}:
        return jsonify({"error": "channel_not_found"}), 404
    if channel.status != "pending":
        return jsonify({"error": "channel_not_pending"}), 400
    # Only the NON-initiating team can accept/decline
    if channel.initiated_by == team.id:
        return jsonify({"error": "initiator_cannot_respond"}), 400

    channel.status = "accepted" if action == "accept" else "declined"
    db.session.commit()

    initiator_team = db.session.get(Team, channel.initiated_by)
    # Notify both teams of the response
    socketio.emit(
        "diplomacy:channel_responded",
        {
            "channel_id": channel.id,
            "status": channel.status,
            "responded_by": team.nation_name,
        },
        namespace="/team",
        room=f"team:{channel.team_a_id}",
    )
    socketio.emit(
        "diplomacy:channel_responded",
        {
            "channel_id": channel.id,
            "status": channel.status,
            "responded_by": team.nation_name,
        },
        namespace="/team",
        room=f"team:{channel.team_b_id}",
    )
    return jsonify({"channel_id": channel.id, "status": channel.status})


@diplomacy_bp.post("/send")
@login_required
def send_message():
    team = _ensure_team()
    if not team:
        return jsonify({"error": "team_required"}), 400
    body = request.get_json(silent=True) or {}
    channel_id = int(body.get("channel_id") or 0)
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content_required"}), 400

    channel = db.session.get(DiplomacyChannel, channel_id)
    if not channel or team.id not in {channel.team_a_id, channel.team_b_id}:
        return jsonify({"error": "channel_not_found"}), 404
    if channel.status != "accepted":
        return jsonify({"error": "channel_not_accepted"}), 400

    message = Message(
        team_id=team.id,
        user_id=current_user.id,
        content=content,
        channel=f"diplomacy:{channel.id}",
    )
    db.session.add(message)
    db.session.commit()

    msg_payload = {
        "channel_id": channel.id,
        "team_id": team.id,
        "content": content,
        "display_name": current_user.display_name,
        "sent_at": message.created_at.isoformat(),
    }
    socketio.emit("diplomacy:message", msg_payload, namespace="/team", room=f"team:{channel.team_a_id}")
    socketio.emit("diplomacy:message", msg_payload, namespace="/team", room=f"team:{channel.team_b_id}")
    return jsonify(msg_payload)
