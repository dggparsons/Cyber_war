"""Auto-generate one intel drop per team when a round starts."""
from __future__ import annotations

import random

from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import IntelDrop, Team
from ..data.intel_puzzles import INTEL_PUZZLE_POOL


def _used_puzzle_indices() -> set[int]:
    """Return indices of puzzles already used (by matching clue text)."""
    existing_clues = {row.clue for row in db.session.query(IntelDrop.clue).all()}
    return {i for i, p in enumerate(INTEL_PUZZLE_POOL) if p["clue"] in existing_clues}


def generate_intel_for_round(round_id: int) -> int:
    """Create one intel drop per nation team for the given round.

    Returns the number of drops created.
    """
    teams = Team.query.filter(Team.team_type != "observer").all()
    if not teams:
        return 0

    used = _used_puzzle_indices()
    available = [i for i in range(len(INTEL_PUZZLE_POOL)) if i not in used]

    if len(available) < len(teams):
        # Recycle if we've exhausted the pool
        available = list(range(len(INTEL_PUZZLE_POOL)))

    random.shuffle(available)

    count = 0
    for team in teams:
        if not available:
            break
        idx = available.pop()
        puzzle = INTEL_PUZZLE_POOL[idx]
        drop = IntelDrop(
            round_id=round_id,
            team_id=team.id,
            puzzle_type=puzzle["puzzle_type"],
            clue=puzzle["clue"],
            reward=puzzle["reward"],
            solution_hash=generate_password_hash(puzzle["solution"]),
        )
        db.session.add(drop)
        count += 1

    db.session.commit()
    return count
