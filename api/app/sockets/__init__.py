"""Socket.IO namespace registrations for Phase 1."""
from __future__ import annotations

from flask import abort
from flask_login import current_user
from flask_socketio import Namespace, emit, join_room, leave_room

from ..extensions import socketio

