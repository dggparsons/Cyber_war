"""Socket.IO namespace registrations."""
from __future__ import annotations

from flask_login import current_user
from flask_socketio import join_room, leave_room

from ..extensions import socketio


@socketio.on("connect", namespace="/team")
def on_team_connect():
    """Join the authenticated user to their team room on the /team namespace."""
    if not current_user.is_authenticated or not current_user.team_id:
        return False  # reject the connection
    join_room(f"team:{current_user.team_id}")


@socketio.on("disconnect", namespace="/team")
def on_team_disconnect():
    """Leave the team room when the user disconnects."""
    if current_user.is_authenticated and current_user.team_id:
        leave_room(f"team:{current_user.team_id}")
