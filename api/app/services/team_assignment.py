"""Logic for deterministic, fair team assignment."""
from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ..extensions import db
from ..models import Team, User, Waitlist


def assign_team_for_user(user: User, session: Session | None = None) -> Team | None:
    """Assign the user to the team with the fewest members under its cap.

    Returns the Team if assignment succeeded, or ``None`` if all seats are full (user should
    be placed on the waitlist).
    """

    session = session or db.session

    try:
        session.execute(text("BEGIN IMMEDIATE"))
    except (OperationalError, AttributeError):
        # Databases that don't support BEGIN IMMEDIATE (e.g., Postgres) will ignore this.
        pass

    team_stmt = (
        select(Team)
        .outerjoin(User, User.team_id == Team.id)
        .group_by(Team.id)
        .having(func.count(User.id) < Team.seat_cap)
        .order_by(func.count(User.id), Team.id)
    )

    team = session.execute(team_stmt).scalars().first()
    if not team:
        wait_entry = Waitlist(user_id=user.id, status="waiting")
        session.add(wait_entry)
        session.flush()
        return None

    user.team = team
    session.add(user)
    session.flush()
    return team
