"""Resolve actions for a round."""
from __future__ import annotations

import random

from ..data.actions import ACTION_LOOKUP
from ..extensions import db, socketio
from ..models import Action, ActionProposal, ActionVote, Team, NewsEvent, Round, FalseFlagPlan
from ..services.global_state import trigger_doom, get_global_state, check_escalation_thresholds
from ..services.world_engine import generate_round_narrative
from ..services.alliances import ensure_alliance, break_alliance


def resolve_round(round_obj):
    proposals = ActionProposal.query.filter_by(round_id=round_obj.id).all()
    resolutions = []
    narrative_entries = []
    proposal_ids = [proposal.id for proposal in proposals]
    false_flag_plans = (
        {
            plan.proposal_id: plan
            for plan in FalseFlagPlan.query.filter(FalseFlagPlan.proposal_id.in_(proposal_ids)).all()
        }
        if proposal_ids
        else {}
    )
    grouped = {}
    for proposal in proposals:
        grouped.setdefault((proposal.team_id, proposal.slot), []).append(proposal)

    for (team_id, slot), items in grouped.items():
        locked_items = [item for item in items if item.status == "locked"]
        if locked_items:
            locked_items.sort(key=lambda proposal: proposal.created_at)
            winner = locked_items[0]
        else:
            draft_items = [item for item in items if item.status == "draft"]
            if not draft_items:
                continue
            winner = choose_winner(draft_items)
        action_def = ACTION_LOOKUP.get(winner.action_code)
        if not action_def:
            continue
        actor = Team.query.get(team_id)
        target = Team.query.get(winner.target_team_id) if winner.target_team_id else None
        success = execute_action(winner, action_def, actor=actor, target=target)
        action = Action(
            round_id=round_obj.id,
            team_id=team_id,
            action_code=winner.action_code,
            target_team_id=winner.target_team_id,
            action_slot=slot,
            locked_from_proposal_id=winner.id,
            resolved_by_user_id=winner.proposer_user_id,
            success=success,
        )
        plan = false_flag_plans.pop(winner.id, None)
        blamed_team = Team.query.get(plan.target_team_id) if plan else None
        if plan:
            db.session.delete(plan)
        db.session.add(action)
        describe_action(actor=actor, proposal=winner, success=success, blamed_team=blamed_team)
        resolutions.append(action)
        if success and action_def:
            if action_def.code == "FORM_ALLIANCE" and actor and target:
                ensure_alliance(actor.id, target.id)
            if action_def.code == "BREAK_ALLIANCE" and actor and target:
                break_alliance(actor.id, target.id)
        narrative_entries.append(
            {
                "actor": actor.nation_name if actor else None,
                "target": target.nation_name if target else None,
                "action_code": winner.action_code,
                "action_name": action_def.name if action_def else winner.action_code,
                "success": success,
                "category": action_def.category if action_def else None,
            }
        )

    # cleanup votes/proposals for the round after resolution
    ActionVote.query.filter(ActionVote.proposal_id.in_([p.id for p in proposals])).delete(synchronize_session=False)
    ActionProposal.query.filter_by(round_id=round_obj.id).delete()
    for leftover_plan in false_flag_plans.values():
        db.session.delete(leftover_plan)
    global_state = get_global_state()
    round_obj.narrative = generate_round_narrative(
        round_obj.round_number,
        narrative_entries,
        crisis=global_state.active_crisis_payload,
    )
    db.session.add(round_obj)
    db.session.commit()
    check_escalation_thresholds(global_state)
    return resolutions


def lock_top_proposals(round_obj: Round | None = None, round_id: int | None = None):
    if not round_obj and round_id:
        round_obj = Round.query.get(round_id)
    if not round_obj:
        return
    proposals = ActionProposal.query.filter_by(round_id=round_obj.id).all()
    if not proposals:
        return
    grouped: dict[tuple[int, int], list[ActionProposal]] = {}
    for proposal in proposals:
        grouped.setdefault((proposal.team_id, proposal.slot), []).append(proposal)
    teams_to_emit: set[int] = set()
    touched = False
    for (team_id, slot), items in grouped.items():
        draft_items = [item for item in items if item.status == "draft"]
        if not draft_items:
            continue
        winner = choose_winner(draft_items)
        for proposal in items:
            desired_status = "locked" if proposal.id == winner.id else "closed"
            if proposal.status != desired_status:
                proposal.status = desired_status
                touched = True
        teams_to_emit.add(team_id)

    if touched:
        db.session.commit()
        for team_id in teams_to_emit:
            payload = {
                "team_id": team_id,
                "round_id": round_obj.id,
                "proposals": serialize_team_proposals(round_obj.id, team_id),
            }
            socketio.emit(
                "proposals:auto_locked",
                payload,
                namespace="/team",
                room=f"team:{team_id}",
            )


def choose_winner(proposals):
    def score(proposal):
        total = sum(v.value for v in proposal.votes)
        return total, -proposal.created_at.timestamp()

    proposals.sort(key=score, reverse=True)
    return proposals[0]


def execute_action(proposal, action_def, actor: Team | None = None, target: Team | None = None):
    actor = actor or Team.query.get(proposal.team_id)
    target = target or (Team.query.get(proposal.target_team_id) if proposal.target_team_id else None)

    success_chance = 0.6
    if actor and target:
        success_chance += (actor.baseline_security - target.baseline_security) / 100
    success_chance = max(0.2, min(0.9, success_chance))
    success = random.random() < success_chance

    if success:
        apply_effects(actor, target, action_def)
        actor.current_escalation += action_def.escalation
        db.session.add(actor)
        if target:
            db.session.add(target)
        if action_def.category == 'nuclear':
            # global doom: drop all teams' prosperity/influence
            for team in Team.query.all():
                team.current_prosperity -= 20
                team.current_security -= 10
                db.session.add(team)
            actor_name = actor.nation_name if actor else "Unknown team"
            trigger_doom(f"{actor_name} executed {action_def.name}. Everyone loses.")
    return success


def apply_effects(actor: Team, target: Team | None, action_def):
    if action_def.self_effects:
        for key, value in action_def.self_effects.items():
            setattr(actor, key, getattr(actor, key) + value)
    if target and action_def.target_effects:
        for key, value in action_def.target_effects.items():
            setattr(target, key, getattr(target, key) + value)


def describe_action(actor: Team | None, proposal: ActionProposal, success: bool, blamed_team: Team | None = None):
    if not actor:
        return
    action = ACTION_LOOKUP.get(proposal.action_code)
    action_name = action.name if action else proposal.action_code
    actor_to_report = blamed_team or actor
    target = Team.query.get(proposal.target_team_id) if proposal.target_team_id else None
    target_text = f" on {target.nation_name}" if target else ""
    outcome = "SUCCESS" if success else "FAILED"
    prefix = ""
    if blamed_team:
        prefix = "SIGINT points to "
    message = f"{prefix}{actor_to_report.nation_name} attempted {action_name}{target_text} - {outcome}."
    event = NewsEvent(message=message)
    db.session.add(event)
    db.session.flush()
    payload = {"id": event.id, "message": message, "created_at": event.created_at.isoformat() if event.created_at else None}
    socketio.emit("news:event", payload, namespace="/global")
    socketio.emit("news:event", payload, namespace="/team")


def serialize_team_proposals(round_id: int, team_id: int):
    proposals = (
        ActionProposal.query.filter_by(round_id=round_id, team_id=team_id)
        .order_by(ActionProposal.slot, ActionProposal.created_at)
        .all()
    )
    return [
        {
            "id": proposal.id,
            "slot": proposal.slot,
            "action_code": proposal.action_code,
            "status": proposal.status,
            "target_team_id": proposal.target_team_id,
            "votes": [
                {"user_id": vote.voter_user_id, "value": vote.value}
                for vote in proposal.votes
            ],
        }
        for proposal in proposals
    ]
