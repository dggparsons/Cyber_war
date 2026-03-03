"""Flask application factory and extension wiring."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from time import time

from flask import Flask, g, request
from flask_cors import CORS

from .config import get_config
from .extensions import db, limiter, login_manager, socketio
from . import models  # noqa: F401  # ensure models are registered with SQLAlchemy
from .sockets import *  # noqa: F401,F403  # register namespaces
from .sockets import chat_events  # noqa: F401
from .routes import register_blueprints
from .services.round_manager import round_manager  # noqa: F401
from .services.schema import ensure_team_columns, ensure_global_state_columns, ensure_action_proposal_columns, ensure_ai_run_columns, ensure_ai_round_score_columns, ensure_diplomacy_columns, ensure_action_columns, ensure_news_event_columns


def create_app(env_name: str | None = None) -> Flask:
    """Application factory used by both CLI and WSGI servers."""
    from dotenv import load_dotenv
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)

    config_obj = get_config(env_name)
    app.config.from_object(config_obj)

    _configure_logging(app)
    _register_extensions(app)
    register_blueprints(app)
    with app.app_context():
        ensure_team_columns()
        ensure_global_state_columns()
        ensure_action_proposal_columns()
        ensure_ai_run_columns()
        ensure_ai_round_score_columns()
        ensure_diplomacy_columns()
        ensure_action_columns()
        ensure_news_event_columns()

    @app.before_request
    def _log_request():
        g._request_started_at = time()
        has_cookie = "cyber_war_session" in request.cookies
        origin = request.headers.get("Origin", "-")
        app.logger.info(
            "→ %s %s (%s) origin=%s cookie=%s",
            request.method, request.path, request.remote_addr,
            origin, has_cookie,
        )

    @app.after_request
    def _log_response(response):
        started = getattr(g, "_request_started_at", None)
        duration = time() - started if started else 0
        has_set_cookie = "Set-Cookie" in response.headers
        cors_origin = response.headers.get("Access-Control-Allow-Origin", "-")
        cors_creds = response.headers.get("Access-Control-Allow-Credentials", "-")
        app.logger.info(
            "← %s %s %s %.3fs set_cookie=%s cors=%s creds=%s",
            request.method, request.path, response.status, duration,
            has_set_cookie, cors_origin, cors_creds,
        )
        return response

    return app


def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)

    # Socket.IO initialisation happens last so it can read overridden CORS origins.
    cors_origins = app.config.get("CORS_ORIGINS", ["*"])
    env = os.environ.get("FLASK_ENV", "development")
    async_mode = "eventlet" if env == "production" else "threading"
    socketio.init_app(app, cors_allowed_origins=cors_origins, async_mode=async_mode)
    CORS(
        app,
        supports_credentials=True,
        resources={r"/api/*": {"origins": cors_origins}},
    )


def _configure_logging(app: Flask) -> None:
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    log_dir = app.config.get("LOG_DIR") or os.path.join(app.instance_path, "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
        if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == log_file for h in app.logger.handlers):
            file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
    except OSError:
        # Volume permissions not ready — fall back to stdout.
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
