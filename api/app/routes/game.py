"""Game state endpoints for the PoC."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..data.actions import ACTIONS, ACTION_LOOKUP
from ..extensions import db, socketio
from ..models import ActionProposal, Team, IntelDrop, ActionVote, NewsEvent, Action, FalseFlagPlan
from ..services.rounds import get_active_round, list_team_proposals
from ..services.leaderboard import compute_outcome_scores
from ..services.team_assignment import assign_team_for_user
from ..services.world_engine import generate_round_narrative
from ..services.alliances import list_alliances_for_team
from ..services.round_manager import round_manager
from ..services.global_state import get_global_state, serialize_global_state
from ..services.lifelines import award_lifeline, list_lifelines, consume_lifeline, queue_false_flag
from ..services.proposals import build_proposal_preview
from ..utils.passwords import verify_password


game_bp = Blueprint("game", __name__, url_prefix="/api/game")


def _lifeline_type_for_intel(intel: IntelDrop) -> str:
    reward_text = (intel.reward or "").lower()
    if "false flag" in reward_text:
        return "false_flag"
    if "phone" in reward_text or "friend" in reward_text:
        return "phone_a_friend"
    return "intel_hint"


def _is_un_team(team: Team | None) -> bool:
    if not team:
        return False
    if team.team_type and team.team_type.lower() == "un":
        return True
    return team.nation_code.upper() == "UN"


def _current_user_is_un() -> bool:
    if not current_user.is_authenticated or not current_user.team_id:
        return False
    team = Team.query.get(current_user.team_id)
    return _is_un_team(team)


def _current_user_is_gm() -> bool:
    return current_user.is_authenticated and current_user.role in {"gm", "admin"}


ADVISOR_PRESETS = {
    "NEXUS": [
        {"name": "General Arkos", "mood": "hawkish", "hint": "Hit them before they regroup."},
        {"name": "Minister Vale", "mood": "paranoid", "hint": "Layer new defenses immediately."},
        {"name": "Prime Minister Rhee", "mood": "diplomatic", "hint": "Keep allies informed."},
        {"name": "Public Sentiment", "mood": "anxious", "hint": "Citizens fear retaliation."},
    ],
    "IRON": [
        {"name": "Marshal Petrov", "mood": "aggressive", "hint": "NEXUS only understands force."},
        {"name": "Chief Operative Lin", "mood": "calculated", "hint": "Use proxies to avoid attribution."},
        {"name": "Commissar Irina", "mood": "propaganda", "hint": "Control the narrative before they do."},
        {"name": "State Council", "mood": "pragmatic", "hint": "Guard our critical utilities above all."},
    ],
    "GNET": [
        {"name": "Director Saar", "mood": "innovative", "hint": "Leverage zero-days quickly."},
        {"name": "Ambassador Lior", "mood": "diplomatic", "hint": "Alliances keep us alive."},
        {"name": "Cyber Monk", "mood": "cautious", "hint": "Defense is our best offense."},
    ],
    "CORAL": [
        {"name": "Minister Hana", "mood": "defensive", "hint": "Protect offshore infrastructure first."},
        {"name": "Chief of Investments", "mood": "economic", "hint": "Sanctions hurt us; avoid escalation."},
        {"name": "Energy Czar Malik", "mood": "strategic", "hint": "Target supply chains to retaliate."},
    ],
    "FRST": [
        {"name": "Commander Tuomi", "mood": "stoic", "hint": "Uphold treaties—even when others do not."},
        {"name": "CERT Lead Aava", "mood": "paranoid", "hint": "Assume everyone is inside already."},
        {"name": "Citizen Panel", "mood": "peaceful", "hint": "Public opinion punishes aggression."},
    ],
    "SHDW": [
        {"name": "General Koa", "mood": "chaotic", "hint": "Strike where it hurts—ethics optional."},
        {"name": "Minister of Truth", "mood": "deceptive", "hint": "False flags keep us alive."},
    ],
    "DAWN": [
        {"name": "Commander Reyes", "mood": "protective", "hint": "Shield allies to maintain credibility."},
        {"name": "Envoy Calderon", "mood": "calm", "hint": "Broker deals before missiles fly."},
        {"name": "NGO Liaison", "mood": "humanitarian", "hint": "Civilian impact matters."},
    ],
    "NEON": [
        {"name": "CEO Myles", "mood": "profit", "hint": "Attacks that scare investors must be punished."},
        {"name": "City Grid AI", "mood": "analytical", "hint": "Optimize for resource gain each round."},
    ],
    "SKY": [
        {"name": "Admiral Vega", "mood": "watchful", "hint": "Keep orbital assets online."},
        {"name": "Telemetry Chief Inez", "mood": "precise", "hint": "Offense should blind before it burns."},
    ],
    "LOTUS": [
        {"name": "Archivist Mei", "mood": "neutral", "hint": "Information trades keep us alive."},
        {"name": "Guardian AI", "mood": "defensive", "hint": "Stay invisible; punish spies quietly."},
    ],
    "UN": [
        {"name": "Secretary J.B. Lyons", "mood": "diplomatic", "hint": "Broker truces when escalation spikes."},
        {"name": "Peacekeeping Lead Sato", "mood": "firm", "hint": "Sanction nations that refuse oversight."},
    ],
}

DEFAULT_BRIEFING = {
    "title": "Round Briefing",
    "summary": "Maintain stability while preparing your cyber teams.",
    "allies": ["No standing alliances"],
    "threats": ["Intel suggests hostile probing from unknown actors."],
    "consequences": "Aggressive moves may push neutral nations into opposing blocs.",
}

BRIEFING_TEMPLATES = {
    "NEXUS": {
        "title": "NEXUS Command Update",
        "summary": "Allied SOCs report increased beaconing from IRONVEIL networks targeting our logistics cloud.",
        "allies": ["DAWNSHIELD rapid-response pact", "FROSTBYTE intelligence lane"],
        "threats": ["IRONVEIL spear-phishing against aerospace contractors", "SHADOWMERE disinformation aimed at Parliament"],
        "consequences": "If you strike IRONVEIL directly, DAWNSHIELD expects attribution proof; failure drops their support by 10 influence.",
    },
    "IRON": {
        "title": "IRONVEIL Directive",
        "summary": "NEXUS fleets manoeuvre near our subsea cables; propaganda wing requests strong retaliation narrative.",
        "allies": ["SHADOWMERE asymmetric cell"],
        "threats": ["NEXUS & DAWNSHIELD joint task force on your satellites"],
        "consequences": "Attacking FROSTBYTE will tank neutral goodwill but grants +5 intimidation against CORALHAVEN.",
    },
    "GNET": {
        "title": "GHOSTNET Situation Room",
        "summary": "Our CERT detected fresh implants on the Baltic energy grid. We suspect IRONVEIL or their proxies.",
        "allies": ["FROSTBYTE cyber-defense pact"],
        "threats": ["Possible IRONVEIL/SHADOWMERE joint ops", "NEONHAVEN courting our contractors"],
        "consequences": "If we betray FROSTBYTE, we lose their intel feed for the rest of the game.",
    },
    "CORAL": {
        "title": "CORALHAVEN Sovereign Council",
        "summary": "Market jitters are hammering our stock exchange after rumors of supply chain compromises.",
        "allies": ["NEONHAVEN investment corridor"],
        "threats": ["NEXUS regulators ready to impose export controls", "SKYWARD probing undersea cables"],
        "consequences": "A reckless strike risks capital flight (-15 prosperity) but sanctions on NEONHAVEN grant +5 influence at home.",
    },
    "FRST": {
        "title": "FROSTBYTE Arctic Brief",
        "summary": "Friendly CERTs intercepted chatter that SKYWard is mapping our satellite uplinks; our populace demands transparency.",
        "allies": ["NEXUS intelligence lane", "GHOSTNET CERT exchange"],
        "threats": ["SKYWARD orbital surveillance", "IRONVEIL influence campaigns"],
        "consequences": "Launching offensive ops without parliament approval will halve your public trust (lose 8 influence).",
    },
    "SHDW": {
        "title": "SHADOWMERE War Council",
        "summary": "Disinformation units flooded DAWNSHIELD channels with forged cables; now is the moment to sow chaos.",
        "allies": ["IRONVEIL shadow budgets"],
        "threats": ["LOTUS neutrality monitors", "UN mandates tightening"],
        "consequences": "If you get caught fabricating intel, everyone piles on: +10 escalation immediately.",
    },
    "DAWN": {
        "title": "DAWNSHIELD Ops Center",
        "summary": "Member states request clarity on retaliation thresholds. NEONHAVEN is asking for joint patrols.",
        "allies": ["NEXUS, FROSTBYTE treaty"],
        "threats": ["IRONVEIL denies involvement in subsea taps", "SHADOWMERE stirring unrest"],
        "consequences": "If you fail to defend an ally when attacked, you lose 12 influence alliance-wide.",
    },
    "NEON": {
        "title": "NEONHAVEN Boardroom Alert",
        "summary": "Share prices dipped after rumors of DAWNSHIELD audits. Investors want decisive action against saboteurs.",
        "allies": ["CORALHAVEN sovereign funds"],
        "threats": ["LOTUS leaking anonymized data on your acquisitions", "GHOSTNET poaching engineers"],
        "consequences": "Ignoring a supply-chain threat costs 10 prosperity; punishing an attacker grants +6 security.",
    },
    "SKY": {
        "title": "SKYWARD UNION Flight Deck",
        "summary": "Our orbital telescopes caught DAWNSHIELD drones trailing our comm satellites. FROSTBYTE requests transparency.",
        "allies": ["NEXUS deep-space tracking"],
        "threats": ["DAWNSHIELD drone swarm", "GHOSTNET infiltration of launch sites"],
        "consequences": "Destroying DAWNSHIELD assets triggers UN censure (+15 escalation) but buys +12 security.",
    },
    "LOTUS": {
        "title": "LOTUS SANCTUM Bulletin",
        "summary": "Intel brokers warn that multiple powers are hunting your anonymization nodes. Stay invisible or sell chaos.",
        "allies": ["GHOSTNET info brokers", "UN Peace Council neutrality pact"],
        "threats": ["NEONHAVEN light probes", "SHADOWMERE infiltration teams"],
        "consequences": "If you stay neutral for two rounds, gain +10 influence; if you betray UN trust, lose 15 security instantly.",
    },
    "UN": {
        "title": "Peace Council Situation Update",
        "summary": "Escalation ticks upward. Member states expect resolutions and targeted sanctions to calm tensions.",
        "allies": ["LOTUS neutrality network"],
        "threats": ["SHADOWMERE rogue campaigns", "IRONVEIL denial tactics"],
        "consequences": "Failing to act when escalation >40 costs you legitimacy (-12 influence).",
    },
}


@game_bp.get("/state")
@login_required
def game_state():
    if not current_user.team_id:
        assigned = assign_team_for_user(current_user)
        db.session.commit()
        if assigned is None:
            return jsonify({"error": "team_assignment_pending"}), 400

    team = Team.query.get(current_user.team_id)
    if not team:
        return jsonify({"error": "team_not_found"}), 404

    round_obj = get_active_round()
    proposals = list_team_proposals(current_user)
    if not proposals:
        pending = ActionProposal.query.filter_by(team_id=current_user.team_id, status='pending').count()
        proposal_payload = []
    intel_items = IntelDrop.query.filter_by(team_id=current_user.team_id).all()
    if not intel_items:
        intel_payload = [
            {
                "id": 0,
                "title": "Cipher Cache",
                "description": "Solve the Vigenère cipher in the PDF to unlock a False Flag token.",
                "reward": "+10 Influence",
                "status": "unsolved",
            }
        ]
    else:
        intel_payload = [
            {
                "id": intel.id,
                "title": intel.puzzle_type,
                "description": intel.clue,
                "reward": intel.reward,
                "status": "solved" if intel.solved_by_team_id else "unsolved",
            }
            for intel in intel_items
        ]

    advisors = ADVISOR_PRESETS.get(team.nation_code, [])
    proposal_ids = [proposal.id for proposal in proposals]
    plans = {
        plan.proposal_id: plan
        for plan in FalseFlagPlan.query.filter(FalseFlagPlan.proposal_id.in_(proposal_ids)).all()
    } if proposal_ids else {}
    proposal_payload = [
        {
            "id": proposal.id,
            "slot": proposal.slot,
            "action_code": proposal.action_code,
            "target_team_id": proposal.target_team_id,
            "status": proposal.status,
            "vetoed_by_user_id": proposal.vetoed_by_user_id,
            "vetoed_reason": proposal.vetoed_reason,
            "false_flag_target_team_id": plans.get(proposal.id).target_team_id if plans.get(proposal.id) else None,
            "votes": [
                {"user_id": vote.voter_user_id, "value": vote.value}
                for vote in proposal.votes
            ],
        }
        for proposal in proposals
    ]

    briefing = BRIEFING_TEMPLATES.get(team.nation_code, DEFAULT_BRIEFING)
    global_state_payload = serialize_global_state()

    return jsonify(
        {
            "team": {
                "id": team.id,
                "nation_name": team.nation_name,
                "nation_code": team.nation_code,
                "role": current_user.role,
                "team_type": team.team_type,
                "seat_cap": team.seat_cap,
            },
            "advisors": advisors,
            "timer_seconds": 6 * 60,
            "action_slots": [{"slot": slot} for slot in (1, 2, 3)],
            "round": {"id": round_obj.id, "number": round_obj.round_number},
            "proposals": proposal_payload,
            "chat_sample": [
                "[Captain] Vote espionage vs honeypots",
                "[GM] Crisis intel dropping in 1 minute",
            ],
            "narrative": round_obj.narrative or generate_round_narrative(round_obj.round_number, []),
            "intel_drops": intel_payload,
            "communications_hint": "Use the team chat to align on proposals before the timer expires.",
            "briefing": briefing,
            "timer": get_round_timer_payload(round_obj),
            "global": global_state_payload,
            "lifelines": list_lifelines(team.id),
            "alliances": list_alliances_for_team(team.id),
        }
    )


@game_bp.get("/leaderboard")
def leaderboard():
    entries = compute_outcome_scores()
    return jsonify(
        {
            "entries": entries,
            "escalation_series": [
                {"round": i, "score": 10 * i} for i in range(1, 1 + len(entries))
            ],
            "timer": get_round_timer_payload(),
            "global": serialize_global_state(),
        }
    )


@game_bp.get("/news")
def news_feed():
    events = NewsEvent.query.order_by(NewsEvent.created_at.desc()).limit(20).all()
    return jsonify([
        {"id": ev.id, "message": ev.message, "created_at": ev.created_at.isoformat()} for ev in events
    ])


@game_bp.get("/proposals/preview")
@login_required
def preview_all_proposals():
    if not (_current_user_is_un() or _current_user_is_gm()):
        return jsonify({"error": "un_only"}), 403
    round_obj = get_active_round()
    preview = build_proposal_preview(round_obj)
    return jsonify(preview)


@game_bp.post("/intel/solve")
@login_required
def solve_intel():
    if not current_user.team_id:
        return jsonify({"error": "team_required"}), 400
    payload = request.get_json(silent=True) or {}
    intel_id = int(payload.get("intel_id") or 0)
    answer = (payload.get("answer") or "").strip()
    if intel_id <= 0 or not answer:
        return jsonify({"error": "invalid_payload"}), 400
    intel = IntelDrop.query.get(intel_id)
    if not intel or intel.team_id != current_user.team_id:
        return jsonify({"error": "intel_not_found"}), 404
    if intel.solved_by_team_id:
        return jsonify({"error": "already_solved"}), 400
    if not verify_password(intel.solution_hash, answer):
        return jsonify({"error": "incorrect_solution"}), 400
    intel.solved_by_team_id = current_user.team_id
    intel.solved_at = db.func.now()
    db.session.add(intel)
    lifeline_type = _lifeline_type_for_intel(intel)
    lifeline = award_lifeline(current_user.team_id, lifeline_type, awarded_for=f"intel:{intel.id}")
    db.session.commit()
    return jsonify(
        {
            "intel_id": intel.id,
            "lifeline": {
                "id": lifeline.id,
                "lifeline_type": lifeline.lifeline_type,
                "remaining_uses": lifeline.remaining_uses,
            },
        }
    )


@game_bp.post("/lifelines/false_flag")
@login_required
def apply_false_flag():
    if not current_user.team_id:
        return jsonify({"error": "team_required"}), 400
    payload = request.get_json(silent=True) or {}
    proposal_id = int(payload.get("proposal_id") or 0)
    blame_team_id = int(payload.get("blame_team_id") or 0)
    if proposal_id <= 0 or blame_team_id <= 0:
        return jsonify({"error": "invalid_payload"}), 400
    proposal = ActionProposal.query.get(proposal_id)
    if not proposal or proposal.team_id != current_user.team_id:
        return jsonify({"error": "proposal_not_found"}), 404
    if proposal.status != "draft":
        return jsonify({"error": "proposal_locked"}), 400
    if proposal.target_team_id and proposal.target_team_id == blame_team_id:
        return jsonify({"error": "cannot_blamed_target"}), 400
    existing = FalseFlagPlan.query.filter_by(proposal_id=proposal_id).first()
    if existing:
        return jsonify({"error": "false_flag_exists"}), 400
    try:
        lifeline = consume_lifeline(current_user.team_id, "false_flag")
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "no_false_flag"}), 400
    plan = queue_false_flag(current_user.team_id, proposal_id, blame_team_id, lifeline.id)
    db.session.commit()
    return jsonify(
        {
            "proposal_id": proposal_id,
            "false_flag_target_team_id": blame_team_id,
        }
    )


@game_bp.post("/proposals/veto")
@login_required
def veto_proposal():
    if not (_current_user_is_un() or _current_user_is_gm()):
        return jsonify({"error": "un_only"}), 403
    payload = request.get_json(silent=True) or {}
    proposal_id = int(payload.get("proposal_id") or 0)
    reason = (payload.get("reason") or "").strip()
    if proposal_id <= 0:
        return jsonify({"error": "invalid_payload"}), 400
    proposal = ActionProposal.query.get(proposal_id)
    if not proposal:
        return jsonify({"error": "proposal_not_found"}), 404
    if proposal.status != "draft":
        return jsonify({"error": "proposal_locked"}), 400
    if not _current_user_is_gm():
        vetoes_used = ActionProposal.query.filter_by(round_id=proposal.round_id, status="vetoed").count()
        if vetoes_used >= 1:
            return jsonify({"error": "veto_limit_reached"}), 400
    proposal.status = "vetoed"
    proposal.vetoed_by_user_id = current_user.id
    proposal.vetoed_reason = reason or "Peace Council veto"
    db.session.add(proposal)
    message = (
        f"UN Peace Council vetoed {Team.query.get(proposal.team_id).nation_name if proposal.team_id else 'a team'}'s "
        f"proposal in Slot {proposal.slot}."
    )
    news_event = NewsEvent(message=message)
    db.session.add(news_event)
    db.session.commit()
    event_payload = {
        "proposal_id": proposal.id,
        "team_id": proposal.team_id,
        "slot": proposal.slot,
        "status": proposal.status,
        "vetoed_by_user_id": proposal.vetoed_by_user_id,
        "vetoed_reason": proposal.vetoed_reason,
    }
    socketio.emit("proposal:vetoed", event_payload, namespace="/team", room=f"team:{proposal.team_id}")
    if current_user.team_id:
        socketio.emit("proposal:vetoed", event_payload, namespace="/team", room=f"team:{current_user.team_id}")
    socketio.emit("proposal:vetoed", event_payload, namespace="/global")
    return jsonify(event_payload)


@game_bp.get("/history")
def action_history():
    limit = min(int(request.args.get("limit", 30) or 20), 100)
    actions = (
        Action.query.order_by(Action.id.desc())
        .limit(limit)
        .all()
    )
    payload = []
    for action in actions:
        actor = Team.query.get(action.team_id)
        target = Team.query.get(action.target_team_id) if action.target_team_id else None
        payload.append(
            {
                "id": action.id,
                "round": action.round_id,
                "action_code": action.action_code,
                "success": action.success,
                "actor": actor.nation_name if actor else None,
                "target": target.nation_name if target else None,
                "slot": action.action_slot,
                "created_at": action.created_at.isoformat() if action.created_at else None,
            }
        )
    return jsonify({"entries": payload})


def get_round_timer_payload(round_obj=None):
    return round_manager.timer_payload(round_obj)


@game_bp.get("/actions")
@login_required
def list_actions():
    team_type = None
    if current_user.is_authenticated:
        team = Team.query.get(current_user.team_id)
        team_type = team.team_type if team else None
    return jsonify(
        [
            {
                "code": action.code,
                "name": action.name,
                "category": action.category,
                "escalation": action.escalation,
                "description": action.description,
                "target_required": action.target_required,
            }
            for action in ACTIONS
            if action.allowed_team_types is None or (team_type and team_type in action.allowed_team_types)
        ]
    )


@game_bp.get("/proposals")
@login_required
def get_proposals():
    if not current_user.team_id:
        return jsonify({"error": "team_assignment_pending"}), 400
    proposals = list_team_proposals(current_user)
    return jsonify(
        [
            {
                "id": proposal.id,
                "slot": proposal.slot,
                "action_code": proposal.action_code,
                "status": proposal.status,
                "target_team_id": proposal.target_team_id,
            }
            for proposal in proposals
        ]
    )


@game_bp.post("/proposals")
@login_required
def submit_proposal():
    if not current_user.team_id:
        return jsonify({"error": "team_assignment_pending"}), 400

    global_state = get_global_state()
    if global_state.doom_triggered:
        return jsonify({"error": "game_over"}), 400

    payload = request.get_json(silent=True) or {}
    action_code = (payload.get("action_code") or "").upper()
    slot = int(payload.get("slot") or 0)
    target_team_id = payload.get("target_team_id")

    if slot not in (1, 2, 3):
        return jsonify({"error": "slot must be 1-3"}), 400
    if action_code not in ACTION_LOOKUP:
        return jsonify({"error": "unknown action"}), 400

    action_def = ACTION_LOOKUP[action_code]
    if action_def.category == "nuclear" and not global_state.nuke_unlocked:
        return jsonify({"error": "nuclear_locked"}), 400

    round_obj = get_active_round()
    if not round_manager.submissions_open(round_obj):
        return jsonify({"error": "round_locked"}), 400

    proposal = ActionProposal(
        round_id=round_obj.id,
        team_id=current_user.team_id,
        proposer_user_id=current_user.id,
        slot=slot,
        action_code=action_code,
        target_team_id=target_team_id,
        status="draft",
    )

    db.session.add(proposal)
    db.session.commit()

    return jsonify(
        {
            "id": proposal.id,
            "slot": proposal.slot,
            "action_code": proposal.action_code,
            "status": proposal.status,
        }
    ), 201


@game_bp.post("/votes")
@login_required
def cast_vote():
    global_state = get_global_state()
    if global_state.doom_triggered:
        return jsonify({"error": "game_over"}), 400

    payload = request.get_json(silent=True) or {}
    proposal_id = int(payload.get("proposal_id") or 0)
    value = int(payload.get("value") or 0)
    if value not in (-1, 1):
        return jsonify({"error": "invalid_vote"}), 400

    proposal = ActionProposal.query.get(proposal_id)
    if not proposal or proposal.team_id != current_user.team_id:
        return jsonify({"error": "proposal_not_found"}), 404
    if proposal.status != "draft":
        return jsonify({"error": "proposal_locked"}), 400

    round_obj = get_active_round()
    if not round_manager.submissions_open(round_obj):
        return jsonify({"error": "round_locked"}), 400

    vote = ActionVote.query.filter_by(proposal_id=proposal_id, voter_user_id=current_user.id).first()
    if vote:
        vote.value = value
    else:
        vote = ActionVote(proposal_id=proposal_id, voter_user_id=current_user.id, value=value)
        db.session.add(vote)
    db.session.commit()

    total = sum(v.value for v in proposal.votes)
    return jsonify({"proposal_id": proposal_id, "total": total})
