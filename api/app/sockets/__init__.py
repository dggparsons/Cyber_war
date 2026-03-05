"""Socket.IO namespace registrations."""
from __future__ import annotations

from flask_login import current_user
from flask_socketio import join_room, leave_room

from ..extensions import socketio


# ── /team namespace ──────────────────────────────────────────────────────────

@socketio.on("connect", namespace="/team")
def on_team_connect():
    """Join the authenticated user to their team room and personal room on /team."""
    if not current_user.is_authenticated or not current_user.team_id:
        return False  # reject the connection
    join_room(f"team:{current_user.team_id}")
    join_room(f"user:{current_user.id}")


@socketio.on("disconnect", namespace="/team")
def on_team_disconnect():
    """Leave rooms when the user disconnects."""
    if current_user.is_authenticated and current_user.team_id:
        leave_room(f"team:{current_user.team_id}")
        leave_room(f"user:{current_user.id}")


# ── /gm namespace ────────────────────────────────────────────────────────────

@socketio.on("connect", namespace="/gm")
def on_gm_connect():
    """Only allow admin/gm users to connect to the GM namespace."""
    if not current_user.is_authenticated or current_user.role not in {"admin", "gm"}:
        return False
    join_room("gm_room")


@socketio.on("disconnect", namespace="/gm")
def on_gm_disconnect():
    if current_user.is_authenticated:
        leave_room("gm_room")


# ── /global namespace ────────────────────────────────────────────────────────

@socketio.on("connect", namespace="/global")
def on_global_connect():
    """Global namespace is open to all authenticated users for timer/news broadcasts."""
    join_room("global_room")


@socketio.on("disconnect", namespace="/global")
def on_global_disconnect():
    leave_room("global_room")


# ── /leaderboard namespace ───────────────────────────────────────────────────

@socketio.on("connect", namespace="/leaderboard")
def on_leaderboard_connect():
    """Leaderboard is open to everyone — spectators, players, GMs."""
    join_room("leaderboard_room")


@socketio.on("disconnect", namespace="/leaderboard")
def on_leaderboard_disconnect():
    leave_room("leaderboard_room")
