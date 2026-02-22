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


def ensure_team_columns():
    db.create_all()
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns('teams')}
    for column_name, column_def in TEAM_DYNAMIC_COLUMNS:
        if column_name not in existing:
            db.session.execute(text(f"ALTER TABLE teams ADD COLUMN {column_name} {column_def}"))
    db.session.commit()


def ensure_global_state_columns():
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns('global_state')}
    for column_name, column_def in GLOBAL_STATE_COLUMNS:
        if column_name not in existing:
            db.session.execute(text(f"ALTER TABLE global_state ADD COLUMN {column_name} {column_def}"))
    db.session.commit()


def ensure_action_proposal_columns():
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns('action_proposals')}
    for column_name, column_def in ACTION_PROPOSAL_COLUMNS:
        if column_name not in existing:
            db.session.execute(text(f"ALTER TABLE action_proposals ADD COLUMN {column_name} {column_def}"))
    db.session.commit()
