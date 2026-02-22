"""Crisis injection helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..data.crises import CRISIS_LIBRARY, CRISIS_LOOKUP
from ..extensions import db
from ..models import CrisisEvent, NewsEvent, Team
from .global_state import clear_active_crisis, set_active_crisis


def list_available_crises() -> List[dict]:
    return [
        {"code": crisis.code, "title": crisis.title, "summary": crisis.summary, "effect": crisis.effect}
        for crisis in CRISIS_LIBRARY
    ]


def inject_crisis(code: str, triggered_by_user_id: int | None = None) -> dict:
    crisis = CRISIS_LOOKUP.get(code.upper())
    if not crisis:
        raise ValueError("unknown_crisis")

    # Apply stat modifiers to every team
    teams = Team.query.all()
    for team in teams:
        for attr, delta in crisis.modifiers.items():
            if hasattr(team, attr):
                setattr(team, attr, getattr(team, attr) + delta)
        db.session.add(team)

    event = CrisisEvent(
        code=crisis.code,
        title=crisis.title,
        summary=crisis.summary,
        effect_text=crisis.effect,
        applied_by_user_id=triggered_by_user_id,
    )
    db.session.add(event)

    headline = NewsEvent(message=f"Crisis Declared: {crisis.title} — {crisis.summary}")
    db.session.add(headline)

    db.session.flush()
    applied_at = event.created_at or datetime.now(timezone.utc)
    payload = {
        "code": crisis.code,
        "title": crisis.title,
        "summary": crisis.summary,
        "effect": crisis.effect,
        "applied_at": applied_at.isoformat(),
    }
    event.payload = payload
    db.session.commit()

    set_active_crisis(crisis.code, payload)
    return payload


def clear_crisis_state():
    clear_active_crisis()


def crisis_history(limit: int = 5) -> List[dict]:
    items = (
        CrisisEvent.query.order_by(CrisisEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "code": item.code,
            "title": item.title,
            "summary": item.summary,
            "effect": item.effect_text,
            "applied_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]
