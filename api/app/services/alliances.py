"""Alliance management helpers."""
from __future__ import annotations

from sqlalchemy import or_, and_

from ..extensions import db
from ..models import Alliance


def _ordered_pair(team_a_id: int, team_b_id: int) -> tuple[int, int]:
    return (team_a_id, team_b_id) if team_a_id <= team_b_id else (team_b_id, team_a_id)


def ensure_alliance(team_a_id: int, team_b_id: int) -> Alliance:
    a_id, b_id = _ordered_pair(team_a_id, team_b_id)
    alliance = Alliance.query.filter_by(team_a_id=a_id, team_b_id=b_id).first()
    if alliance:
        alliance.status = "active"
        db.session.add(alliance)
        return alliance
    alliance = Alliance(team_a_id=a_id, team_b_id=b_id, status="active")
    db.session.add(alliance)
    return alliance


def has_active_alliance(team_a_id: int, team_b_id: int) -> bool:
    a_id, b_id = _ordered_pair(team_a_id, team_b_id)
    alliance = Alliance.query.filter_by(team_a_id=a_id, team_b_id=b_id, status="active").first()
    return alliance is not None


def break_alliance(team_a_id: int, team_b_id: int) -> None:
    a_id, b_id = _ordered_pair(team_a_id, team_b_id)
    alliance = Alliance.query.filter_by(team_a_id=a_id, team_b_id=b_id).first()
    if alliance:
        alliance.status = "broken"
        db.session.add(alliance)


def list_alliances_for_team(team_id: int) -> list[dict]:
    alliances = Alliance.query.filter(
        and_(
            Alliance.status == "active",
            or_(Alliance.team_a_id == team_id, Alliance.team_b_id == team_id),
        )
    ).all()
    return [
        {
            "team_a_id": alliance.team_a_id,
            "team_b_id": alliance.team_b_id,
            "status": alliance.status,
            "formed_at": alliance.created_at.isoformat() if alliance.created_at else None,
        }
        for alliance in alliances
    ]
