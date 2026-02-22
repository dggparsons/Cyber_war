"""Outcome score helpers."""
from __future__ import annotations

from typing import List

from ..models import Team


def compute_outcome_scores() -> List[dict]:
    entries = []
    for team in Team.query.all():
        baseline = team.baseline_prosperity + team.baseline_security + team.baseline_influence
        deltas = team.current_prosperity + team.current_security + team.current_influence - team.current_escalation
        score = baseline + deltas
        entries.append(
            {
                "team_id": team.id,
                "nation_name": team.nation_name,
                "score": score,
                "delta_from_baseline": deltas,
                "escalation": team.current_escalation,
            }
        )
    entries.sort(key=lambda e: e["score"], reverse=True)
    return entries
