"""Game state endpoints for the PoC."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..data.actions import ACTIONS, ACTION_LOOKUP
from ..extensions import db, socketio, limiter
from ..models import ActionProposal, Team, IntelDrop, ActionVote, NewsEvent, Action, FalseFlagPlan, MegaChallenge, MegaChallengeSolve, Lifeline, User, Round, OutcomeScoreHistory
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

# Apply default rate limit to all game endpoints
limiter.limit("60 per minute")(game_bp)


def _lifeline_type_for_intel(intel: IntelDrop) -> str:
    reward = (intel.reward or "").strip().lower()
    if reward in ("false_flag", "phone_a_friend"):
        return reward
    # Legacy text matching
    if "false" in reward and "flag" in reward:
        return "false_flag"
    if "phone" in reward or "friend" in reward:
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


def _avatar(bg: str, fg: str, icon: str, accent: str = "#0f172a") -> str:
    """Build a minimal SVG data-URI portrait."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
        f'<rect width="48" height="48" rx="6" fill="{bg}"/>'
        f'<circle cx="24" cy="18" r="9" fill="{fg}" opacity=".9"/>'
        f'<ellipse cx="24" cy="40" rx="14" ry="10" fill="{fg}" opacity=".7"/>'
        f'<text x="24" y="22" text-anchor="middle" font-size="13" fill="{accent}">{icon}</text>'
        f'</svg>'
    )
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ADVISOR_PRESETS = {
    "NEXUS": [
        {"name": "General Arkos", "mood": "hawkish", "hint": "Hit them before they regroup.",
         "avatar": _avatar("#1e3a5f", "#c0392b", "\u2694")},
        {"name": "Minister Vale", "mood": "paranoid", "hint": "Layer new defenses immediately.",
         "avatar": _avatar("#1e3a5f", "#7f8c8d", "\U0001f441")},
        {"name": "Prime Minister Rhee", "mood": "diplomatic", "hint": "Keep allies informed.",
         "avatar": _avatar("#1e3a5f", "#2ecc71", "\u2696")},
        {"name": "Public Sentiment", "mood": "anxious", "hint": "Citizens fear retaliation.",
         "avatar": _avatar("#1e3a5f", "#f39c12", "\u265a")},
    ],
    "IRON": [
        {"name": "Marshal Petrov", "mood": "aggressive", "hint": "NEXUS only understands force.",
         "avatar": _avatar("#4a1a2e", "#e74c3c", "\u2620")},
        {"name": "Chief Operative Lin", "mood": "calculated", "hint": "Use proxies to avoid attribution.",
         "avatar": _avatar("#4a1a2e", "#9b59b6", "\u2316")},
        {"name": "Commissar Irina", "mood": "propaganda", "hint": "Control the narrative before they do.",
         "avatar": _avatar("#4a1a2e", "#e67e22", "\u2691")},
        {"name": "State Council", "mood": "pragmatic", "hint": "Guard our critical utilities above all.",
         "avatar": _avatar("#4a1a2e", "#95a5a6", "\u2699")},
    ],
    "GNET": [
        {"name": "Director Saar", "mood": "innovative", "hint": "Leverage zero-days quickly.",
         "avatar": _avatar("#0d3b2e", "#1abc9c", "\u26a1")},
        {"name": "Ambassador Lior", "mood": "diplomatic", "hint": "Alliances keep us alive.",
         "avatar": _avatar("#0d3b2e", "#3498db", "\u2696")},
        {"name": "Cyber Monk", "mood": "cautious", "hint": "Defense is our best offense.",
         "avatar": _avatar("#0d3b2e", "#ecf0f1", "\u262f")},
    ],
    "CORAL": [
        {"name": "Minister Hana", "mood": "defensive", "hint": "Protect offshore infrastructure first.",
         "avatar": _avatar("#1a3c4a", "#2980b9", "\u2693")},
        {"name": "Chief of Investments", "mood": "economic", "hint": "Sanctions hurt us; avoid escalation.",
         "avatar": _avatar("#1a3c4a", "#f1c40f", "\u2b50")},
        {"name": "Energy Czar Malik", "mood": "strategic", "hint": "Target supply chains to retaliate.",
         "avatar": _avatar("#1a3c4a", "#e67e22", "\u269b")},
    ],
    "FRST": [
        {"name": "Commander Tuomi", "mood": "stoic", "hint": "Uphold treaties\u2014even when others do not.",
         "avatar": _avatar("#1a2a3a", "#bdc3c7", "\u2744")},
        {"name": "CERT Lead Aava", "mood": "paranoid", "hint": "Assume everyone is inside already.",
         "avatar": _avatar("#1a2a3a", "#e74c3c", "\U0001f6e1")},
        {"name": "Citizen Panel", "mood": "peaceful", "hint": "Public opinion punishes aggression.",
         "avatar": _avatar("#1a2a3a", "#2ecc71", "\u262e")},
    ],
    "SHDW": [
        {"name": "General Koa", "mood": "chaotic", "hint": "Strike where it hurts\u2014ethics optional.",
         "avatar": _avatar("#2c2c2c", "#e74c3c", "\U0001f525")},
        {"name": "Minister of Truth", "mood": "deceptive", "hint": "False flags keep us alive.",
         "avatar": _avatar("#2c2c2c", "#8e44ad", "\U0001f3ad")},
    ],
    "DAWN": [
        {"name": "Commander Reyes", "mood": "protective", "hint": "Shield allies to maintain credibility.",
         "avatar": _avatar("#3a2a0a", "#f39c12", "\U0001f6e1")},
        {"name": "Envoy Calderon", "mood": "calm", "hint": "Broker deals before missiles fly.",
         "avatar": _avatar("#3a2a0a", "#2ecc71", "\u2696")},
        {"name": "NGO Liaison", "mood": "humanitarian", "hint": "Civilian impact matters.",
         "avatar": _avatar("#3a2a0a", "#e74c3c", "\u2764")},
    ],
    "NEON": [
        {"name": "CEO Myles", "mood": "profit", "hint": "Attacks that scare investors must be punished.",
         "avatar": _avatar("#1a0a3a", "#00ff88", "\u2b24")},
        {"name": "City Grid AI", "mood": "analytical", "hint": "Optimize for resource gain each round.",
         "avatar": _avatar("#1a0a3a", "#3498db", "\u2b23")},
    ],
    "SKY": [
        {"name": "Admiral Vega", "mood": "watchful", "hint": "Keep orbital assets online.",
         "avatar": _avatar("#0a1a3a", "#ecf0f1", "\u2605")},
        {"name": "Telemetry Chief Inez", "mood": "precise", "hint": "Offense should blind before it burns.",
         "avatar": _avatar("#0a1a3a", "#1abc9c", "\u25ce")},
    ],
    "LOTUS": [
        {"name": "Archivist Mei", "mood": "neutral", "hint": "Information trades keep us alive.",
         "avatar": _avatar("#2a1a2a", "#dda0dd", "\u2698")},
        {"name": "Guardian AI", "mood": "defensive", "hint": "Stay invisible; punish spies quietly.",
         "avatar": _avatar("#2a1a2a", "#1abc9c", "\u2726")},
    ],
    "UN": [
        {"name": "Secretary J.B. Lyons", "mood": "diplomatic", "hint": "Broker truces when escalation spikes.",
         "avatar": _avatar("#0a2a4a", "#3498db", "\u2302")},
        {"name": "Peacekeeping Lead Sato", "mood": "firm", "hint": "Sanction nations that refuse oversight.",
         "avatar": _avatar("#0a2a4a", "#2ecc71", "\u269c")},
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
    # Admin/GM users don't play — they manage the game from the admin panel
    if current_user.role in ("admin", "gm"):
        return jsonify({"error": "admin_use_gm_panel"}), 403

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
    # Show intel drops up to and including the current round (one new per round)
    if round_obj:
        current_and_past_round_ids = [
            r.id for r in Round.query.filter(Round.round_number <= round_obj.round_number).all()
        ]
        intel_items = IntelDrop.query.filter(
            IntelDrop.team_id == current_user.team_id,
            IntelDrop.round_id.in_(current_and_past_round_ids),
        ).all()
    else:
        intel_items = []
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
            "action_slots": [{"slot": slot} for slot in (1,)],
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
            "roster": [
                {"id": u.id, "display_name": u.display_name, "role": u.role, "is_captain": u.is_captain}
                for u in User.query.filter_by(team_id=team.id).all()
            ],
        }
    )


@game_bp.get("/leaderboard")
def leaderboard():
    from ..models import OutcomeScoreHistory, Round
    entries = compute_outcome_scores()

    # Build per-nation escalation history from OutcomeScoreHistory
    rounds = Round.query.filter(Round.status == "resolved").order_by(Round.round_number).all()
    escalation_by_nation: dict[str, list[dict]] = {}
    for team in Team.query.all():
        escalation_by_nation[team.nation_name] = []

    for rd in rounds:
        scores = OutcomeScoreHistory.query.filter_by(round_id=rd.id).all()
        score_map = {s.team_id: s for s in scores}
        for team in Team.query.all():
            entry = score_map.get(team.id)
            escalation_by_nation.setdefault(team.nation_name, []).append({
                "round": rd.round_number,
                "score": entry.outcome_score if entry else 0,
            })

    # Cyber Impact list — who attacked whom (from Action records)
    attack_actions = (
        Action.query
        .filter(Action.target_team_id.isnot(None))
        .order_by(Action.id.desc())
        .limit(50)
        .all()
    )
    cyber_impact = []
    for a in attack_actions:
        actor = Team.query.get(a.team_id)
        target = Team.query.get(a.target_team_id)
        cyber_impact.append({
            "round": a.round_id,
            "actor": actor.nation_name if actor else "Unknown",
            "target": target.nation_name if target else "Unknown",
            "action": a.action_code,
            "success": a.success,
        })

    return jsonify(
        {
            "entries": entries,
            "escalation_series": escalation_by_nation,
            "cyber_impact": cyber_impact,
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
    answer = (payload.get("answer") or "").strip().upper()
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
    team = Team.query.get(current_user.team_id)
    team_name = team.nation_name if team else "A team"
    news = NewsEvent(message=f"{team_name} cracked an intel drop ({intel.puzzle_type}) and earned a {lifeline_type.replace('_', ' ')}!")
    db.session.add(news)
    db.session.commit()
    socketio.emit("news:event", {
        "id": news.id, "message": news.message,
        "created_at": news.created_at.isoformat() if news.created_at else None,
    }, namespace="/global")
    socketio.emit("news:event", {
        "id": news.id, "message": news.message,
        "created_at": news.created_at.isoformat() if news.created_at else None,
    }, namespace="/team")
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
    team_obj = Team.query.get(proposal.team_id)
    proposal.status = "vetoed"
    proposal.vetoed_by_user_id = current_user.id
    proposal.vetoed_reason = reason or "Peace Council veto"
    db.session.add(proposal)
    team_name = team_obj.nation_name if team_obj else "a team"
    action_name = proposal.action_code
    message = f"UN Peace Council vetoed {team_name}'s Slot {proposal.slot} ({action_name})."
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
@limiter.limit("10 per minute")
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

    if slot not in (1,):
        return jsonify({"error": "slot must be 1"}), 400
    if action_code not in ACTION_LOOKUP:
        return jsonify({"error": "unknown action"}), 400

    action_def = ACTION_LOOKUP[action_code]
    if action_def.category == "nuclear" and not global_state.nuke_unlocked:
        return jsonify({"error": "nuclear_locked"}), 400

    if action_def.target_required and not target_team_id:
        return jsonify({"error": "target_required"}), 400
    if target_team_id and int(target_team_id) == current_user.team_id:
        return jsonify({"error": "cannot_target_self"}), 400

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
@limiter.limit("30 per minute")
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


# ---------------------------------------------------------------------------
# Mega Challenge
# ---------------------------------------------------------------------------

@game_bp.get("/mega-challenge")
@login_required
def get_mega_challenge():
    challenge = MegaChallenge.query.first()
    if not challenge:
        return jsonify({"active": False})

    solves = (
        MegaChallengeSolve.query
        .filter_by(challenge_id=challenge.id)
        .order_by(MegaChallengeSolve.solve_position)
        .all()
    )
    solved_teams = [
        {"team_id": s.team_id, "position": s.solve_position, "reward": s.reward_influence}
        for s in solves
    ]

    return jsonify({
        "active": True,
        "id": challenge.id,
        "description": challenge.description,
        "reward_tiers": challenge.reward_tiers,
        "solved_by": solved_teams,
        "already_solved": any(s["team_id"] == current_user.team_id for s in solved_teams),
    })


@game_bp.post("/mega-challenge/solve")
@limiter.limit("5 per minute")
@login_required
def solve_mega_challenge():
    if not current_user.team_id:
        return jsonify({"error": "team_required"}), 400

    payload = request.get_json(silent=True) or {}
    answer = (payload.get("answer") or "").strip().upper()
    if not answer:
        return jsonify({"error": "answer_required"}), 400

    challenge = MegaChallenge.query.first()
    if not challenge:
        return jsonify({"error": "no_active_challenge"}), 404

    already = MegaChallengeSolve.query.filter_by(
        challenge_id=challenge.id, team_id=current_user.team_id
    ).first()
    if already:
        return jsonify({"error": "already_solved"}), 400

    if not verify_password(challenge.solution_hash, answer):
        return jsonify({"error": "incorrect_solution"}), 400

    solve_count = MegaChallengeSolve.query.filter_by(challenge_id=challenge.id).count()
    tiers = challenge.reward_tiers or [15, 10, 5]
    reward = tiers[solve_count] if solve_count < len(tiers) else tiers[-1]

    solve = MegaChallengeSolve(
        challenge_id=challenge.id,
        team_id=current_user.team_id,
        solve_position=solve_count + 1,
        reward_influence=reward,
    )
    db.session.add(solve)

    team = Team.query.get(current_user.team_id)
    if team:
        team.current_influence += reward
        db.session.add(team)

    team_name = team.nation_name if team else "A team"
    news = NewsEvent(message=f"{team_name} cracked the Mega Challenge! (+{reward} Influence)")
    db.session.add(news)
    db.session.commit()

    socketio.emit("news:event", {
        "id": news.id, "message": news.message,
        "created_at": news.created_at.isoformat() if news.created_at else None,
    }, namespace="/global")

    return jsonify({
        "solved": True,
        "reward_influence": reward,
        "solve_position": solve_count + 1,
    })


# ---------------------------------------------------------------------------
# Phone-a-Friend Lifeline
# ---------------------------------------------------------------------------

@game_bp.post("/proposals/captain-override")
@login_required
def captain_override_proposal():
    if not current_user.team_id:
        return jsonify({"error": "team_required"}), 400
    if not (current_user.is_captain or _current_user_is_gm()):
        return jsonify({"error": "captain_only"}), 403
    payload = request.get_json(silent=True) or {}
    proposal_id = int(payload.get("proposal_id") or 0)
    if proposal_id <= 0:
        return jsonify({"error": "invalid_payload"}), 400
    proposal = ActionProposal.query.get(proposal_id)
    if not proposal or proposal.team_id != current_user.team_id:
        return jsonify({"error": "proposal_not_found"}), 404
    if proposal.status != "draft":
        return jsonify({"error": "proposal_not_draft"}), 400
    # Lock this proposal and close all other drafts for the same slot
    siblings = ActionProposal.query.filter(
        ActionProposal.round_id == proposal.round_id,
        ActionProposal.team_id == proposal.team_id,
        ActionProposal.slot == proposal.slot,
        ActionProposal.id != proposal.id,
    ).all()
    for sib in siblings:
        if sib.status == "draft":
            sib.status = "closed"
    proposal.status = "locked"
    db.session.commit()
    payload_out = {
        "team_id": proposal.team_id,
        "round_id": proposal.round_id,
        "proposals": [
            {
                "id": p.id,
                "slot": p.slot,
                "action_code": p.action_code,
                "status": p.status,
                "target_team_id": p.target_team_id,
                "votes": [{"user_id": v.voter_user_id, "value": v.value} for v in p.votes],
            }
            for p in ActionProposal.query.filter_by(round_id=proposal.round_id, team_id=proposal.team_id).all()
        ],
    }
    socketio.emit("proposals:auto_locked", payload_out, namespace="/team", room=f"team:{proposal.team_id}")
    return jsonify({"status": "locked", "proposal_id": proposal.id})


@game_bp.post("/lifelines/phone-a-friend")
@login_required
def use_phone_a_friend():
    if not current_user.team_id:
        return jsonify({"error": "team_required"}), 400

    try:
        lifeline = consume_lifeline(current_user.team_id, "phone_a_friend")
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "no_phone_a_friend_lifeline"}), 400

    # Reveal one random enemy action from the current round
    round_obj = get_active_round()
    enemy_proposals = (
        ActionProposal.query
        .filter(
            ActionProposal.round_id == round_obj.id,
            ActionProposal.team_id != current_user.team_id,
            ActionProposal.status.in_(["draft", "locked"]),
        )
        .all()
    )

    hint = None
    if enemy_proposals:
        import random as rng
        pick = rng.choice(enemy_proposals)
        enemy_team = Team.query.get(pick.team_id)
        action_def = ACTION_LOOKUP.get(pick.action_code)
        hint = {
            "team_name": enemy_team.nation_name if enemy_team else "Unknown",
            "action_name": action_def.name if action_def else pick.action_code,
            "slot": pick.slot,
        }
    else:
        hint = {"team_name": "N/A", "action_name": "No intel available", "slot": 0}

    db.session.commit()
    return jsonify({"hint": hint})


# ---------------------------------------------------------------------------
# Round Recap
# ---------------------------------------------------------------------------

@game_bp.get("/recap")
@login_required
def round_recap():
    """Return a debrief for the most recently resolved round."""
    round_num = request.args.get("round", type=int)
    if round_num:
        resolved = Round.query.filter_by(round_number=round_num, status="resolved").first()
    else:
        resolved = Round.query.filter_by(status="resolved").order_by(Round.round_number.desc()).first()

    if not resolved:
        return jsonify({"recap": None})

    teams = {t.id: t for t in Team.query.all()}

    # --- News events from this round's time window ---
    events: list[str] = []
    if resolved.started_at and resolved.ended_at:
        news_rows = (
            NewsEvent.query
            .filter(NewsEvent.created_at.between(resolved.started_at, resolved.ended_at))
            .order_by(NewsEvent.created_at.asc())
            .all()
        )
        events = [n.message for n in news_rows]

    # --- Standings with deltas ---
    cur_scores = {
        s.team_id: s.outcome_score
        for s in OutcomeScoreHistory.query.filter_by(round_id=resolved.id).all()
    }
    prev_round = Round.query.filter_by(
        round_number=resolved.round_number - 1, status="resolved"
    ).first()
    prev_scores: dict[int, int] = {}
    if prev_round:
        prev_scores = {
            s.team_id: s.outcome_score
            for s in OutcomeScoreHistory.query.filter_by(round_id=prev_round.id).all()
        }

    standings = []
    for t in sorted(teams.values(), key=lambda t: cur_scores.get(t.id, 0), reverse=True):
        baseline = t.baseline_prosperity + t.baseline_security + t.baseline_influence
        score = cur_scores.get(t.id, baseline)
        prev = prev_scores.get(t.id, baseline)
        standings.append({
            "team_id": t.id,
            "nation_name": t.nation_name,
            "score": score,
            "delta": score - prev,
            "escalation": t.current_escalation,
        })

    # --- Requesting player's own team breakdown ---
    my_team = teams.get(current_user.team_id) if current_user.team_id else None
    my_stats = None
    my_actions: list[dict] = []
    if my_team:
        my_stats = {
            "prosperity": my_team.baseline_prosperity + my_team.current_prosperity,
            "security": my_team.baseline_security + my_team.current_security,
            "influence": my_team.baseline_influence + my_team.current_influence,
            "escalation": my_team.current_escalation,
        }
        for act in Action.query.filter_by(round_id=resolved.id, team_id=my_team.id).all():
            adef = ACTION_LOOKUP.get(act.action_code)
            target = teams.get(act.target_team_id) if act.target_team_id else None
            my_actions.append({
                "slot": act.action_slot,
                "action_name": adef.name if adef else act.action_code,
                "category": adef.category if adef else "unknown",
                "target": target.nation_name if target else None,
                "success": act.success,
            })

    # --- Aggregate action stats (public, no actor revealed) ---
    all_actions = Action.query.filter_by(round_id=resolved.id).all()
    total_actions = len(all_actions)
    total_success = sum(1 for a in all_actions if a.success)
    category_counts: dict[str, int] = {}
    for a in all_actions:
        adef = ACTION_LOOKUP.get(a.action_code)
        cat = adef.category if adef else "unknown"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return jsonify({
        "recap": {
            "round_number": resolved.round_number,
            "narrative": resolved.narrative or "",
            "events": events,
            "standings": standings,
            "my_stats": my_stats,
            "my_actions": my_actions,
            "summary": {
                "total_actions": total_actions,
                "successful": total_success,
                "failed": total_actions - total_success,
                "by_category": category_counts,
            },
            "world": {
                "total_escalation": sum(t.current_escalation for t in teams.values()),
                "nuke_unlocked": any(
                    a.action_code == "NUKE_LOCK" and a.success
                    for a in all_actions
                ),
            },
        },
    })
