"""Utilities for resetting the game state to a clean slate."""
from __future__ import annotations

from typing import Iterable, Type

from ..extensions import db
from ..services.chat import chat_buffer
from ..models import (
    Action,
    ActionProposal,
    ActionVote,
    Alliance,
    CrisisEvent,
    DiplomacyChannel,
    FalseFlagPlan,
    GlobalState,
    HiddenEvent,
    IntelDrop,
    Lifeline,
    MegaChallenge,
    MegaChallengeSolve,
    Message,
    NewsEvent,
    OutcomeScoreHistory,
    Round,
    Team,
    User,
    Waitlist,
)
from ..seeds.team_data import TEAMS


ModelType = Type[db.Model]


def _bulk_delete(models: Iterable[ModelType]):
    for model in models:
        db.session.execute(db.delete(model))


def reset_game_state(round_count: int):
    """Wipe round-dependent data and recreate pending rounds."""
    # Remove any objects that reference rounds or carry over session data.
    _bulk_delete(
        [
            ActionVote,
            FalseFlagPlan,
            ActionProposal,
            Action,
            IntelDrop,
            Lifeline,
            MegaChallengeSolve,
            DiplomacyChannel,
            Alliance,
            Message,
            NewsEvent,
            OutcomeScoreHistory,
            HiddenEvent,
            CrisisEvent,
            GlobalState,
            # NOTE: AiRun and AiRoundScore are intentionally preserved across
            # resets — the AI shadow simulation is independent of player data.
        ]
    )
    db.session.commit()

    # Reset dynamic team stats/deltas back to zero.
    for team in Team.query.all():
        team.current_prosperity = 0
        team.current_security = 0
        team.current_influence = 0
        team.current_escalation = 0
        db.session.add(team)
    db.session.commit()

    # Clear in-memory chat buffer
    chat_buffer.clear()

    # Remove and recreate the canonical list of rounds.
    db.session.execute(db.delete(Round))
    db.session.commit()
    for idx in range(1, round_count + 1):
        db.session.add(Round(round_number=idx, status="pending"))
    db.session.commit()


def full_reset(round_count: int):
    """Full DB reset: wipe all game state, remove non-admin players, and re-seed teams."""
    reset_game_state(round_count)
    # Remove all non-admin/gm users and waitlist entries
    _bulk_delete([Waitlist])
    db.session.execute(
        db.delete(User).where(User.role.notin_(["admin", "gm"]))
    )
    db.session.commit()

    # Clear team assignments on remaining admin/gm users before re-seeding
    for u in User.query.filter(User.role.in_(["admin", "gm"])).all():
        u.team_id = None
    db.session.commit()

    # Re-seed teams from team_data to pick up any changes
    _bulk_delete([Team])
    db.session.commit()
    for team_data in TEAMS:
        db.session.add(Team(**team_data))
    db.session.commit()
