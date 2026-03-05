"""Resolve actions for a round."""
from __future__ import annotations

import random

from ..data.actions import ACTION_LOOKUP
from ..extensions import db, socketio
from ..models import Action, ActionProposal, ActionVote, Team, NewsEvent, Round, FalseFlagPlan, OutcomeScoreHistory, HiddenEvent
from ..services.global_state import trigger_doom, get_global_state, check_escalation_thresholds, set_nuke_unlocked, clear_active_crisis
from ..services.world_engine import generate_round_narrative
from ..services.alliances import ensure_alliance, break_alliance, has_active_alliance
from ..services.leaderboard import compute_outcome_scores


HOSTILE_CATEGORIES = {"non_violent", "violent", "nuclear"}


def apply_betrayal(actor: Team, target: Team, round_obj):
    """Break alliance and penalise the betrayer heavily."""
    break_alliance(actor.id, target.id)
    actor.current_escalation += 15
    actor.current_influence -= 8
    db.session.add(actor)
    message = f"BETRAYAL: {actor.nation_name} struck their own ally {target.nation_name}! Alliance dissolved."
    event = NewsEvent(message=message, round_id=round_obj.id)
    db.session.add(event)
    db.session.flush()
    payload = {"id": event.id, "message": message, "created_at": event.created_at.isoformat() if event.created_at else None}
    socketio.emit("news:event", payload, namespace="/global")
    socketio.emit("news:event", payload, namespace="/team")


def process_hidden_exposures(current_round):
    """Reveal covert actions from previous rounds based on elapsed time."""
    hidden_events = HiddenEvent.query.filter_by(revealed=False).all()
    for he in hidden_events:
        original_round = Round.query.get(he.round_id)
        if not original_round:
            continue
        rounds_elapsed = current_round.round_number - original_round.round_number
        if rounds_elapsed <= 0:
            continue
        exposure_chance = 0.15 * rounds_elapsed
        if random.random() < exposure_chance:
            he.revealed = True
            he.revealed_at_round_id = current_round.id
            actor = Team.query.get(he.real_team_id)
            target = Team.query.get(he.target_team_id)
            action_def = ACTION_LOOKUP.get(he.action_code)
            if not actor or not target or not action_def:
                continue

            outcome = "SUCCESS" if he.success else "FAILED"
            msg = (f"INTELLIGENCE REPORT: The Round {original_round.round_number} "
                   f"{action_def.name} against {target.nation_name} ({outcome}) "
                   f"has been attributed to {actor.nation_name}.")
            event = NewsEvent(message=msg, round_id=current_round.id)
            db.session.add(event)
            db.session.flush()
            payload = {"id": event.id, "message": msg, "created_at": event.created_at.isoformat() if event.created_at else None}
            socketio.emit("news:event", payload, namespace="/global")
            socketio.emit("news:event", payload, namespace="/team")

            # Check for deferred alliance betrayal
            if (action_def.category in HOSTILE_CATEGORIES
                    and has_active_alliance(actor.id, target.id)):
                apply_betrayal(actor, target, current_round)


def resolve_round(round_obj):
    # Seed RNG deterministically so outcomes are reproducible for a given round
    random.seed(f"cyberwar-r{round_obj.id}-{round_obj.round_number}")

    # Reveal covert actions from previous rounds before resolving new ones
    process_hidden_exposures(round_obj)

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

    # Auto-fill empty proposal slots with WAIT actions
    all_teams = Team.query.all()
    for team in all_teams:
        occupied_slots = {slot for (tid, slot) in grouped if tid == team.id}
        for slot in range(1, 2):
            if slot not in occupied_slots:
                wait_proposal = ActionProposal(
                    round_id=round_obj.id,
                    team_id=team.id,
                    proposer_user_id=0,
                    slot=slot,
                    action_code="WAIT",
                    target_team_id=None,
                    rationale="Auto-filled: no proposal submitted",
                    status="locked",
                )
                db.session.add(wait_proposal)
                db.session.flush()
                grouped.setdefault((team.id, slot), []).append(wait_proposal)

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
        success, failure_reason, effects_summary = execute_action(winner, action_def, actor=actor, target=target)
        # Covert detection roll
        is_covert = action_def.visibility == "covert"
        detected = False
        if is_covert and target:
            detection_chance = max(0, target.baseline_security + target.current_security) / 200
            detected = random.random() < detection_chance
        covert_undetected = is_covert and not detected

        action = Action(
            round_id=round_obj.id,
            team_id=team_id,
            action_code=winner.action_code,
            target_team_id=winner.target_team_id,
            action_slot=slot,
            locked_from_proposal_id=winner.id,
            resolved_by_user_id=winner.proposer_user_id,
            success=success,
            covert=is_covert,
            detected=detected,
            failure_reason=failure_reason,
            effects_summary=effects_summary,
        )
        plan = false_flag_plans.pop(winner.id, None)
        blamed_team = Team.query.get(plan.target_team_id) if plan else None
        if plan:
            db.session.delete(plan)
        # False flag: transfer escalation from real actor to blamed team
        if blamed_team:
            esc_amount = action_def.escalation if success else (action_def.escalation // 2)
            if esc_amount > 0:
                actor.current_escalation -= esc_amount
                blamed_team.current_escalation += esc_amount
                db.session.add(actor)
                db.session.add(blamed_team)
        db.session.add(action)
        db.session.flush()  # get action.id for HiddenEvent FK

        # Create hidden event for undetected covert actions
        if covert_undetected and target:
            hidden = HiddenEvent(
                round_id=round_obj.id,
                action_id=action.id,
                real_team_id=actor.id,
                target_team_id=target.id,
                action_code=action_def.code,
                success=success,
            )
            db.session.add(hidden)

        if winner.action_code != "WAIT":
            describe_action(actor=actor, proposal=winner, success=success,
                            blamed_team=blamed_team, covert_undetected=covert_undetected,
                            round_id=round_obj.id)
        resolutions.append(action)
        if success and action_def:
            if action_def.code == "BREAK_ALLIANCE" and actor and target:
                break_alliance(actor.id, target.id)

        # Alliance betrayal: hostile action against an ally
        if (action_def.category in HOSTILE_CATEGORIES and target
                and has_active_alliance(actor.id, target.id)):
            if not covert_undetected:
                # Overt or detected covert — immediate betrayal
                apply_betrayal(actor, target, round_obj)
            # If covert + undetected: betrayal deferred to exposure

        # Narrative entry — respect covert attribution
        actor_label = actor.nation_name if actor else None
        if covert_undetected and not blamed_team:
            actor_label = "An unidentified state actor"
        elif blamed_team:
            actor_label = blamed_team.nation_name

        # Skip passive/WAIT actions from narrative — they're not interesting news
        if winner.action_code != "WAIT":
            narrative_entries.append(
                {
                    "actor": actor_label,
                    "target": target.nation_name if target else None,
                    "action_code": winner.action_code,
                    "action_name": action_def.name if action_def else winner.action_code,
                    "success": success,
                    "category": action_def.category if action_def else None,
                }
            )

    # --- Resolve alliances: require mutual FORM_ALLIANCE ---
    alliance_offers = {}  # team_id -> target_team_id
    for action in resolutions:
        if action.action_code == "FORM_ALLIANCE" and action.success and action.target_team_id:
            alliance_offers[action.team_id] = action.target_team_id

    for team_id, target_id in alliance_offers.items():
        # Check if the target also proposed FORM_ALLIANCE back at us
        if alliance_offers.get(target_id) == team_id:
            # Mutual — form the alliance and grant security bonus
            ensure_alliance(team_id, target_id)
            team_a = Team.query.get(team_id)
            team_b = Team.query.get(target_id)
            team_a.current_security += 5
            team_b.current_security += 5
            db.session.add(team_a)
            db.session.add(team_b)
            a_name = team_a.nation_name
            b_name = team_b.nation_name
            msg = f"ALLIANCE FORMED: {a_name} and {b_name} signed a mutual defence pact."
            event = NewsEvent(message=msg, round_id=round_obj.id)
            db.session.add(event)
            db.session.flush()
            payload = {"id": event.id, "message": msg, "created_at": event.created_at.isoformat() if event.created_at else None}
            socketio.emit("news:event", payload, namespace="/global")
            socketio.emit("news:event", payload, namespace="/team")
        else:
            # One-sided — announce the offer
            actor = Team.query.get(team_id)
            target = Team.query.get(target_id)
            if actor and target:
                msg = f"{actor.nation_name} extended an alliance offer to {target.nation_name}. Awaiting reciprocation."
                event = NewsEvent(message=msg, round_id=round_obj.id)
                db.session.add(event)
                db.session.flush()
                payload = {"id": event.id, "message": msg, "created_at": event.created_at.isoformat() if event.created_at else None}
                socketio.emit("news:event", payload, namespace="/global")
                socketio.emit("news:event", payload, namespace="/team")

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

    # Clear any active crisis at end of round — crises last one round only
    if global_state.active_crisis_payload:
        clear_active_crisis()

    check_escalation_thresholds(global_state)

    # Store outcome score history for each team
    scores = compute_outcome_scores()
    for entry in scores:
        record = OutcomeScoreHistory(
            team_id=entry["team_id"],
            round_id=round_obj.id,
            outcome_score=entry["score"],
        )
        db.session.add(record)
    db.session.commit()

    # Push leaderboard update via Socket.IO
    socketio.emit("leaderboard:update", scores, namespace="/global")

    # Broadcast updated narrative so World News refreshes without page reload
    if round_obj.narrative:
        socketio.emit(
            "news:narrative",
            {"round": round_obj.round_number, "narrative": round_obj.narrative},
            namespace="/global",
        )

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

    failure_reason = None
    effects_parts = []

    # Passive/self-only actions and diplomatic actions always succeed
    if (action_def.visibility == "passive" and not target) or action_def.visibility == "diplomatic":
        success = True
    else:
        success_chance = 0.6
        if actor and target:
            actor_sec = actor.baseline_security + actor.current_security
            target_sec = target.baseline_security + target.current_security
            success_chance += (actor_sec - target_sec) / 100
        success_chance = max(0.2, min(0.9, success_chance))
        success = random.random() < success_chance
        if not success:
            if target and (target.baseline_security + target.current_security) > (actor.baseline_security + actor.current_security):
                failure_reason = f"{target.nation_name}'s security ({target.baseline_security + target.current_security}) exceeded your capability ({actor.baseline_security + actor.current_security})"
            elif target:
                failure_reason = f"Operation failed despite favourable odds ({int(success_chance * 100)}% chance). Bad luck."
            else:
                failure_reason = "Operation did not achieve its objectives."

    if success:
        apply_effects(actor, target, action_def)
        actor.current_escalation += action_def.escalation

        # Build effects summary
        if action_def.self_effects:
            for key, value in action_def.self_effects.items():
                stat = key.replace("current_", "").capitalize()
                effects_parts.append(f"Your {stat} {'+' if value > 0 else ''}{value}")
        if target and action_def.target_effects:
            for key, value in action_def.target_effects.items():
                stat = key.replace("current_", "").capitalize()
                effects_parts.append(f"{target.nation_name} {stat} {'+' if value > 0 else ''}{value}")
        if action_def.escalation != 0:
            effects_parts.append(f"Escalation {'+' if action_def.escalation > 0 else ''}{action_def.escalation}")

        if action_def.code == "NUKE_LOCK":
            set_nuke_unlocked(True)
        db.session.add(actor)
        if target:
            db.session.add(target)
        if action_def.category == 'nuclear':
            for team in Team.query.all():
                team.current_prosperity -= 20
                team.current_security -= 10
                db.session.add(team)
            actor_name = actor.nation_name if actor else "Unknown team"
            trigger_doom(f"{actor_name} executed {action_def.name}. Everyone loses.")
    else:
        # Failed actions still add half escalation (you tried and people noticed)
        half_esc = action_def.escalation // 2
        if half_esc > 0:
            actor.current_escalation += half_esc
            effects_parts.append(f"Escalation +{half_esc} (failed attempt detected)")
            db.session.add(actor)

    effects_summary = "; ".join(effects_parts) if effects_parts else None
    return success, failure_reason, effects_summary


def apply_effects(actor: Team, target: Team | None, action_def):
    if action_def.self_effects:
        for key, value in action_def.self_effects.items():
            setattr(actor, key, getattr(actor, key) + value)
    if target and action_def.target_effects:
        for key, value in action_def.target_effects.items():
            setattr(target, key, getattr(target, key) + value)


def describe_action(actor: Team | None, proposal: ActionProposal, success: bool,
                    blamed_team: Team | None = None, covert_undetected: bool = False,
                    round_id: int | None = None):
    if not actor:
        return
    action = ACTION_LOOKUP.get(proposal.action_code)
    action_name = action.name if action else proposal.action_code
    target = Team.query.get(proposal.target_team_id) if proposal.target_team_id else None
    target_text = f" on {target.nation_name}" if target else ""
    outcome = "SUCCESS" if success else "FAILED"

    if covert_undetected and not blamed_team:
        # Covert action without false flag — hide the actor
        message = f"An unidentified state actor targeted{(' ' + target.nation_name) if target else ' unknown assets'} with {action_name} - {outcome}."
    elif blamed_team:
        # False flag — attribute to the blamed nation
        message = f"SIGINT points to {blamed_team.nation_name} attempted {action_name}{target_text} - {outcome}."
    else:
        # Normal overt attribution
        message = f"{actor.nation_name} attempted {action_name}{target_text} - {outcome}."

    event = NewsEvent(message=message, round_id=round_id)
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
