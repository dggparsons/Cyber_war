"""Route registration helpers."""
from __future__ import annotations

from flask import Flask

from .health import health_bp
from .auth import auth_bp
from .game import game_bp
from .reveal import reveal_bp
from .diplomacy import diplomacy_bp
from .admin import admin_bp


BLUEPRINTS = (
    health_bp,
    auth_bp,
    game_bp,
    reveal_bp,
    admin_bp,
    diplomacy_bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
