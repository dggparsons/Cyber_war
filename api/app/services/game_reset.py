"""Utilities for resetting the game state to a clean slate."""
from __future__ import annotations

from typing import Iterable, Type

from ..extensions import db
from ..models import (
    Action,
    ActionProposal,
    ActionVote,
    Alliance,
    CrisisEvent,
    DiplomacyChannel,
    FalseFlagPlan,
    GlobalState,
    IntelDrop,
    Lifeline,
    MegaChallengeSolve,
    Message,
    NewsEvent,
    OutcomeScoreHistory,
    Round,
    Team,
    User,
    Waitlist,
)


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

    # Remove and recreate the canonical list of rounds.
    db.session.execute(db.delete(Round))
    db.session.commit()
    for idx in range(1, round_count + 1):
        db.session.add(Round(round_number=idx, status="pending"))
    db.session.commit()


def full_reset(round_count: int):
    """Full DB reset: wipe all game state AND remove non-admin player accounts."""
    reset_game_state(round_count)
    # Remove all non-admin/gm users and waitlist entries
    _bulk_delete([Waitlist])
    db.session.execute(
        db.delete(User).where(User.role.notin_(["admin", "gm"]))
    )
    db.session.commit()
