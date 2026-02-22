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
    emit("chat:history", chat_buffer.get(room))


@socketio.on("chat:message", namespace="/team")
def chat_message(data):
    if not current_user.is_authenticated or not current_user.team_id:
        return
    room = f"team:{current_user.team_id}"
    payload = {
        "user_id": current_user.id,
        "display_name": current_user.display_name,
        "content": (data.get("content") or "")[:500],
    }
    if not payload["content"]:
        return
    msg = Message(team_id=current_user.team_id, user_id=current_user.id, content=payload["content"])
    db.session.add(msg)
    db.session.commit()
    chat_buffer.add(room, payload)
    emit("chat:message", payload, room=room, include_self=True)
