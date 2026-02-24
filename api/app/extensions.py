"""Shared Flask extensions."""
from __future__ import annotations

from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
login_manager.login_view = None


@login_manager.user_loader
def load_user(user_id: str):
    from .models import User

    if not user_id:
        return None
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "unauthorized"}), 401
