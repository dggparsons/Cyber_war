"""Configuration objects for different environments."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "instance" / "cyber_war_dev.db"


def _parse_round_durations(raw: str | None) -> list[int]:
    if not raw:
        return [6, 6, 6, 4]
    durations: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            durations.append(int(chunk))
        except ValueError:
            raise ValueError(f"ROUND_DURATIONS must be comma-separated ints, got '{raw}'") from None
    return durations or [6, 6, 6, 4]


@dataclass
class BaseConfig:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_DEFAULT_DB_PATH}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SESSION_COOKIE_NAME: str = "cyber_war_session"
    SESSION_COOKIE_SAMESITE: str = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: os.environ.get("CORS_ORIGINS", "*").split(",")
    )
    ROUND_COUNT: int = int(os.environ.get("ROUND_COUNT", "6"))
    ROUND_DURATIONS: list[int] = field(
        default_factory=lambda: _parse_round_durations(os.environ.get("ROUND_DURATIONS"))
    )
    NUKE_LOCKED_DEFAULT: bool = os.environ.get("NUKE_LOCKED_DEFAULT", "true").lower() != "false"
    GM_USERNAME: str = os.environ.get("GM_USERNAME", "gm@example.com")
    GM_PASSWORD: str = os.environ.get("GM_PASSWORD", "change-this")


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True


class ProductionConfig(BaseConfig):
    DEBUG: bool = False


class TestingConfig(BaseConfig):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


def get_config(env_name: str | None) -> type[BaseConfig]:
    mapping: dict[str, type[BaseConfig]] = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    env_key = (env_name or os.environ.get("FLASK_ENV") or "development").lower()
    return mapping.get(env_key, DevelopmentConfig)
