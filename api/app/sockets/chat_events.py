"""Chat and diplomacy events."""
from __future__ import annotations

from flask_login import current_user
from flask_socketio import emit

from ..extensions import db, socketio
from ..models import Message
from ..services.chat import chat_buffer


@socketio.on("chat:history", namespace="/team")
def chat_history():
    if not current_user.is_authenticated or not current_user.team_id:
        return
    room = f"team:{current_user.team_id}"
    items = chat_buffer.get(room)
    if not items:
        # Fallback: load recent messages from DB (e.g. after server restart)
        from ..models import User
        rows = (
            Message.query
            .filter_by(team_id=current_user.team_id, channel="team")
            .order_by(Message.created_at.desc())
            .limit(50)
            .all()
        )
        items = [
            {
                "user_id": m.user_id,
                "display_name": m.user.display_name if m.user else "Unknown",
                "role": m.user.role if m.user else "player",
                "content": m.content,
            }
            for m in reversed(rows)
        ]
        # Repopulate the buffer so subsequent requests are fast
        for item in items:
            chat_buffer.add(room, item)
    emit("chat:history", items)


@socketio.on("chat:message", namespace="/team")
def chat_message(data):
    if not current_user.is_authenticated or not current_user.team_id:
        return
    room = f"team:{current_user.team_id}"
    payload = {
        "user_id": current_user.id,
        "display_name": current_user.display_name,
        "role": current_user.role or "player",
        "content": (data.get("content") or "")[:500],
    }
    if not payload["content"]:
        return
    msg = Message(team_id=current_user.team_id, user_id=current_user.id, content=payload["content"])
    db.session.add(msg)
    db.session.commit()
    chat_buffer.add(room, payload)
    emit("chat:message", payload, room=room, include_self=True)


@socketio.on("chat:typing", namespace="/team")
def chat_typing(data):
    if not current_user.is_authenticated or not current_user.team_id:
        return
    room = f"team:{current_user.team_id}"
    emit(
        "chat:typing",
        {"user_id": current_user.id, "display_name": current_user.display_name, "typing": bool(data.get("typing"))},
        room=room,
        include_self=False,
    )
