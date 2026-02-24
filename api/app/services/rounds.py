"""Round helpers for the PoC."""
from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models import ActionProposal, Round, User


def get_active_round() -> Round:
    round_obj = Round.query.filter(Round.status.in_(["active", "resolving"])).order_by(Round.round_number).first()
    if round_obj:
        return round_obj

    # Promote first pending round to active.
    pending = Round.query.filter_by(status="pending").order_by(Round.round_number).first()
    if pending:
        pending.status = "active"
        pending.started_at = datetime.utcnow()
        db.session.add(pending)
        db.session.commit()
        return pending

    if Round.query.count() == 0:
        pending = Round(round_number=1, status="active", started_at=datetime.utcnow())
        db.session.add(pending)
        db.session.commit()
        return pending

    # No pending/active rounds remain; return the most recent resolved round.
    fallback = Round.query.order_by(Round.round_number.desc()).first()
    if fallback:
        return fallback
    pending = Round(round_number=1, status="active", started_at=datetime.utcnow())
    db.session.add(pending)
    db.session.commit()
    return pending


def list_team_proposals(user: User):
    return (
        ActionProposal.query.filter_by(team_id=user.team_id)
        .order_by(ActionProposal.slot, ActionProposal.created_at)
        .all()
    )
