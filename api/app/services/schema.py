"""Schema migration helpers for ad-hoc column additions."""
from __future__ import annotations

from sqlalchemy import inspect, text

from ..extensions import db
from ..models import DiplomacyChannel, NewsEvent  # noqa: F401


TEAM_DYNAMIC_COLUMNS = [
    ("current_prosperity", "INTEGER DEFAULT 0"),
    ("current_security", "INTEGER DEFAULT 0"),
    ("current_influence", "INTEGER DEFAULT 0"),
    ("current_escalation", "INTEGER DEFAULT 0"),
]

GLOBAL_STATE_COLUMNS = [
    ("escalation_thresholds", "JSON"),
]

ACTION_PROPOSAL_COLUMNS = [
    ("vetoed_by_user_id", "INTEGER"),
    ("vetoed_reason", "TEXT"),
]

AI_RUN_COLUMNS = [
    ("final_escalation", "INTEGER"),
    ("doom_triggered", "BOOLEAN DEFAULT 0"),
    ("completed_at", "DATETIME"),
]

AI_ROUND_SCORE_COLUMNS = [
    ("nation_code", "VARCHAR(16)"),
    ("action_code", "VARCHAR(64)"),
    ("target_nation_code", "VARCHAR(16)"),
    ("success", "BOOLEAN"),
    ("reasoning", "TEXT"),
]

DIPLOMACY_CHANNEL_COLUMNS = [
    ("initiated_by", "INTEGER"),
]

ACTION_COLUMNS = [
    ("covert", "BOOLEAN DEFAULT 0"),
    ("detected", "BOOLEAN DEFAULT 0"),
]

NEWS_EVENT_COLUMNS = [
    ("round_id", "INTEGER"),
]


def _ensure_columns(table_name: str, columns: list[tuple[str, str]]):
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns(table_name)}
    for column_name, column_def in columns:
        if column_name not in existing:
            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
    db.session.commit()


def ensure_team_columns():
    db.create_all()
    _ensure_columns('teams', TEAM_DYNAMIC_COLUMNS)


def ensure_global_state_columns():
    _ensure_columns('global_state', GLOBAL_STATE_COLUMNS)


def ensure_action_proposal_columns():
    _ensure_columns('action_proposals', ACTION_PROPOSAL_COLUMNS)


def ensure_ai_run_columns():
    _ensure_columns('ai_runs', AI_RUN_COLUMNS)


def ensure_ai_round_score_columns():
    _ensure_columns('ai_round_scores', AI_ROUND_SCORE_COLUMNS)


def ensure_diplomacy_columns():
    _ensure_columns('diplomacy_channels', DIPLOMACY_CHANNEL_COLUMNS)


def ensure_action_columns():
    _ensure_columns('actions', ACTION_COLUMNS)


def ensure_news_event_columns():
    _ensure_columns('news_events', NEWS_EVENT_COLUMNS)
