"""Helpers for proposal previews."""
from __future__ import annotations

from typing import Dict, Any

from ..models import ActionProposal, Team, Round


def build_proposal_preview(round_obj: Round) -> Dict[str, Any]:
    proposals = (
        ActionProposal.query.filter_by(round_id=round_obj.id)
        .order_by(ActionProposal.team_id, ActionProposal.slot, ActionProposal.created_at)
        .all()
    )
    team_cache: dict[int, dict] = {}
    veto_count = 0
    for proposal in proposals:
        if proposal.status == "vetoed":
            veto_count += 1
        if proposal.team_id not in team_cache:
            team_obj = Team.query.get(proposal.team_id)
            if not team_obj:
                continue
            team_cache[proposal.team_id] = {
                "team_id": team_obj.id,
                "nation_name": team_obj.nation_name,
                "proposals": [],
            }
        total_votes = sum(v.value for v in proposal.votes)
        team_cache[proposal.team_id]["proposals"].append(
            {
                "id": proposal.id,
                "slot": proposal.slot,
                "action_code": proposal.action_code,
                "status": proposal.status,
                "target_team_id": proposal.target_team_id,
                "votes": total_votes,
                "vetoed_by_user_id": proposal.vetoed_by_user_id,
            }
        )

    return {
        "round": round_obj.round_number,
        "limit": 1,
        "vetoes_used": veto_count,
        "teams": list(team_cache.values()),
    }
