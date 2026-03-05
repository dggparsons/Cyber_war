"""Auto-generate one intel drop per team when a round starts.

Every team gets the SAME puzzle each round. Puzzle selection cycles through
the pool in order (round 1 → puzzle 0, round 2 → puzzle 1, etc.), wrapping
around if there are more rounds than puzzles.
"""
from __future__ import annotations

from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import IntelDrop, Round, Team
from ..data.intel_puzzles import INTEL_PUZZLE_POOL


def generate_intel_for_round(round_id: int) -> int:
    """Create one intel drop per nation team for the given round.

    All teams receive the same puzzle. The puzzle is chosen deterministically
    based on the round number so each round gets a different puzzle.

    Returns the number of drops created.
    """
    round_obj = Round.query.get(round_id)
    if not round_obj:
        return 0

    teams = Team.query.filter(Team.team_type != "observer").all()
    if not teams:
        return 0

    # Don't double-generate if drops already exist for this round
    existing = IntelDrop.query.filter_by(round_id=round_id).count()
    if existing > 0:
        return 0

    # Deterministic puzzle selection: round 1 → index 0, round 2 → index 1, etc.
    idx = (round_obj.round_number - 1) % len(INTEL_PUZZLE_POOL)
    puzzle = INTEL_PUZZLE_POOL[idx]
    solution_hash = generate_password_hash(puzzle["solution"])

    count = 0
    for team in teams:
        drop = IntelDrop(
            round_id=round_id,
            team_id=team.id,
            puzzle_type=puzzle["puzzle_type"],
            clue=puzzle["clue"],
            reward=puzzle["reward"],
            solution_hash=solution_hash,
        )
        db.session.add(drop)
        count += 1

    db.session.commit()
    return count
