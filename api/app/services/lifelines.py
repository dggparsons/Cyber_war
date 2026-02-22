"""Lifeline management helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..extensions import db
from ..models import Lifeline, FalseFlagPlan


def award_lifeline(team_id: int, lifeline_type: str, awarded_for: Optional[str] = None, uses: int = 1) -> Lifeline:
    lifeline = Lifeline.query.filter_by(team_id=team_id, lifeline_type=lifeline_type).first()
    if lifeline:
        lifeline.remaining_uses += uses
        if awarded_for:
            lifeline.awarded_for = awarded_for
    else:
        lifeline = Lifeline(team_id=team_id, lifeline_type=lifeline_type, remaining_uses=uses, awarded_for=awarded_for)
        db.session.add(lifeline)
    return lifeline


def consume_lifeline(team_id: int, lifeline_type: str) -> Lifeline:
    lifeline = Lifeline.query.filter_by(team_id=team_id, lifeline_type=lifeline_type).first()
    if not lifeline or lifeline.remaining_uses < 1:
        raise ValueError("lifeline_unavailable")
    lifeline.remaining_uses -= 1
    db.session.add(lifeline)
    return lifeline


def list_lifelines(team_id: int) -> list[dict]:
    lifelines = Lifeline.query.filter_by(team_id=team_id).all()
    return [
        {
            "id": lifeline.id,
            "lifeline_type": lifeline.lifeline_type,
            "remaining_uses": lifeline.remaining_uses,
            "awarded_for": lifeline.awarded_for,
        }
        for lifeline in lifelines
        if lifeline.remaining_uses > 0
    ]


def queue_false_flag(team_id: int, proposal_id: int, target_team_id: int, lifeline_id: int) -> FalseFlagPlan:
    plan = FalseFlagPlan(team_id=team_id, proposal_id=proposal_id, target_team_id=target_team_id, lifeline_id=lifeline_id)
    db.session.add(plan)
    return plan
