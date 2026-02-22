"""Chat-related Socket.IO events."""
from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room

from ..extensions import db
from ..models import Message
from ..services.chat import chat_buffer
from ..sockets import TeamNamespace


def register_chat_events(socketio):
    namespace = TeamNamespace("/team")

    @socketio.on("chat:history", namespace="/team")
    def chat_history():
        if not current_user.is_authenticated or not current_user.team_id:
            return
        room = f"team:{current_user.team_id}"
        join_room(room)
        emit("chat:history", chat_buffer.get(room))

    @socketio.on("chat:message", namespace="/team")
    def chat_message(data):
        if not current_user.is_authenticated or not current_user.team_id:
            return
        room = f"team:{current_user.team_id}"
        payload = {
            "user_id": current_user.id,
            "display_name": current_user.display_name,
            "content": data.get("content", "")[:500],
        }
        msg = Message(team_id=current_user.team_id, user_id=current_user.id, content=payload["content"])
        db.session.add(msg)
        db.session.commit()
        chat_buffer.add(room, payload)
        emit("chat:message", payload, room=room)
