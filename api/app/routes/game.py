"""Game state endpoints for the PoC."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from ..data.actions import ACTIONS, ACTION_LOOKUP
from ..extensions import db, socketio, limiter
from ..models import ActionProposal, Team, IntelDrop, ActionVote, NewsEvent, Action, FalseFlagPlan, MegaChallenge, MegaChallengeSolve, Lifeline, User, Round, OutcomeScoreHistory
from ..services.rounds import get_active_round, list_team_proposals
from ..services.leaderboard import compute_outcome_scores
from ..services.team_assignment import assign_team_for_user
from ..services.world_engine import generate_round_narrative, INTRO_NARRATIVE
from ..services.alliances import list_alliances_for_team
from ..services.round_manager import round_manager
from ..services.global_state import get_global_state, serialize_global_state
from ..services.lifelines import award_lifeline, list_lifelines, consume_lifeline, queue_false_flag
from ..services.proposals import build_proposal_preview
from ..utils.passwords import verify_password


game_bp = Blueprint("game", __name__, url_prefix="/api/game")

# Apply default rate limit to all game endpoints
limiter.limit("60 per minute")(game_bp)


def _latest_narrative(current_round_number: int) -> str:
    """Return the most recent resolved round's real narrative (skipping intro text)."""
    resolved = (
        Round.query
        .filter(Round.status == "resolved", Round.narrative.isnot(None))
        .order_by(Round.round_number.desc())
        .all()
    )
    for prev in resolved:
        if prev.narrative and prev.narrative.strip() != INTRO_NARRATIVE.strip():
            return prev.narrative
    # No real narrative found — return intro for pre-game
    return generate_round_narrative(current_round_number, [])


def _dynamic_briefing(team, round_num: int) -> dict:
    """Build a briefing that reflects the live game state — alliances, attacks, scores."""
    from ..services.alliances import list_alliances_for_team

    base = BRIEFING_TEMPLATES.get(team.nation_code, DEFAULT_BRIEFING)
    briefing = {**base}  # shallow copy

    all_teams = {t.id: t for t in Team.query.all()}
    scores = {t.id: t.current_prosperity + t.current_security + t.current_influence for t in all_teams.values()}

    # --- Dynamic allies: active alliances + original briefing allies ---
    alliances = list_alliances_for_team(team.id)
    active_allies = []
    for a in alliances:
        if a.get("status") != "active":
            continue
        partner_id = a["team_b_id"] if a["team_a_id"] == team.id else a["team_a_id"]
        partner = all_teams.get(partner_id)
        if partner:
            active_allies.append(f"{partner.nation_name} — Active alliance (formed in-game)")

    # Keep original briefing allies that haven't attacked us
    hostile_team_ids = set()
    recent_actions = Action.query.filter(
        Action.target_team_id == team.id,
        Action.success == True,
    ).all()
    for act in recent_actions:
        adef = ACTION_LOOKUP.get(act.action_code)
        if adef and adef.category in ("non_violent", "violent", "nuclear"):
            hostile_team_ids.add(act.team_id)

    original_allies = []
    for ally_str in base.get("allies", []):
        # Check if any original ally nation has attacked us
        ally_name = ally_str.split(" — ")[0].strip()
        attacker = next((t for t in all_teams.values() if t.nation_name == ally_name and t.id in hostile_team_ids), None)
        if attacker:
            original_allies.append(f"{ally_name} — BETRAYED (attacked you in a previous round)")
        else:
            original_allies.append(ally_str)

    briefing["allies"] = active_allies + original_allies

    # --- Dynamic threats: nations that attacked us + original threats ---
    dynamic_threats = []
    seen_names = set()
    for act in recent_actions:
        adef = ACTION_LOOKUP.get(act.action_code)
        if not adef or adef.category not in ("non_violent", "violent", "nuclear"):
            continue
        attacker = all_teams.get(act.team_id)
        if not attacker or attacker.nation_name in seen_names:
            continue
        seen_names.add(attacker.nation_name)
        dynamic_threats.append(f"{attacker.nation_name} — Attacked you with {adef.name} (Round {_round_number_for_action(act)})")

    # Keep original threats not already covered
    original_threats = []
    for threat_str in base.get("threats", []):
        threat_name = threat_str.split(" — ")[0].strip()
        if threat_name not in seen_names:
            original_threats.append(threat_str)

    briefing["threats"] = dynamic_threats + original_threats

    # --- Dynamic summary based on game state ---
    my_score = scores.get(team.id, 0)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (tid, _) in enumerate(sorted_scores) if tid == team.id), 0)
    leader = all_teams.get(sorted_scores[0][0]) if sorted_scores else None

    status_line = base.get("summary", "")
    if round_num > 2:
        if rank == 1:
            status_line = f"You are leading with a score of {my_score}. Hold your position and watch for backstabs."
        elif rank <= 3:
            status_line = f"You are ranked #{rank} (score: {my_score}). {leader.nation_name if leader else 'The leader'} is ahead — close the gap."
        else:
            status_line = f"You are ranked #{rank} (score: {my_score}). Aggressive moves or smart alliances are needed to climb."

    briefing["summary"] = status_line

    # --- Dynamic consequences ---
    if team.current_escalation > 30:
        briefing["consequences"] = f"Your escalation is dangerously high ({team.current_escalation}). Further aggression risks catastrophic consequences for everyone."
    elif len(active_allies) > 0:
        partner_names = [a.split(" — ")[0] for a in active_allies]
        briefing["consequences"] = f"You have active alliances with {', '.join(partner_names)}. Attacking allies causes severe penalties. Coordinate before acting."

    return briefing


def _round_number_for_action(action) -> int:
    """Get the round number for an action."""
    round_obj = Round.query.get(action.round_id)
    return round_obj.round_number if round_obj else 0


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

ROUND_1_BRIEFING_NATION = {
    "title": "Operational Briefing — Round 1",
    "summary": "Welcome, Commander. This is your war room. Here is everything you need to know before your first move.",
    "allies": [],
    "threats": [],
    "consequences": "",
    "sections": [
        {
            "heading": "Your Objective",
            "items": [
                "Your nation has four stats: Prosperity (economy), Security (defence), Influence (diplomacy), and Escalation (danger level).",
                "Score is calculated from Prosperity + Security + Influence. The higher, the better.",
                "Escalation is bad — if it climbs too high, the situation spirals out of control and everyone loses.",
            ],
        },
        {
            "heading": "How Each Round Works",
            "items": [
                "Each round, your team submits ONE action. Choose carefully — you only get one shot per round.",
                "Team members can propose different actions. The team votes, and the highest-voted proposal is locked in when the timer expires.",
                "Your captain can veto proposals and override if needed.",
            ],
        },
        {
            "heading": "Actions & Targets",
            "items": [
                "Actions range from diplomacy (sharing intel, forming alliances) to offensive operations (cyber strikes, espionage, sanctions).",
                "Some actions target another nation — choose your target wisely.",
                "Success is not guaranteed. Your security stat improves your odds; the target's security makes it harder.",
                "Some actions are COVERT — your identity stays hidden unless the target detects you. Espionage, sabotage, disinformation, supply chain attacks, and ransomware are all covert.",
                "Attacking an ally is possible but dangerous. If detected, the alliance breaks and you take a severe escalation penalty.",
            ],
        },
        {
            "heading": "Intel Drops & Mega Challenge",
            "items": [
                "Each round you receive an intel drop — a two-stage puzzle. Decode it, then solve the riddle to earn a lifeline.",
                "The Mega Challenge is a persistent multi-part investigation worth big influence. Work on it between rounds.",
            ],
        },
        {
            "heading": "Diplomacy & Communication",
            "items": [
                "Use the diplomacy panel to open channels with other nations. Negotiate, threaten, or deceive — it's up to you.",
                "Team chat is private to your nation. Use it to coordinate with your team.",
                "Alliances boost both nations' security. But breaking an alliance has consequences.",
            ],
        },
        {
            "heading": "Round 1 Advice",
            "items": [
                "Round 1 is your chance to set the tone. Defensive and diplomatic moves are safe early plays.",
                "Observe what other nations do before committing to aggression.",
                "Covert actions let you strike without immediate attribution — but detection risk scales with the target's security score. Nothing stays hidden forever.",
                "Check your intel drop — solving it early gives you a tactical advantage.",
            ],
        },
    ],
}

ROUND_1_BRIEFING_UN = {
    "title": "Operational Briefing — Round 1",
    "summary": "Welcome to the UN Peace Council. You are the referee, the peacekeeper, and the conscience of the world.",
    "allies": [],
    "threats": [],
    "consequences": "",
    "sections": [
        {
            "heading": "Your Role",
            "items": [
                "You are NOT a nation. You cannot launch cyber attacks, deploy malware, or wage war.",
                "Your power is diplomatic: sanctions, peacekeeping, mediation, investigations, embargoes, and humanitarian aid.",
                "Your score comes from Influence — the more you shape events, the more powerful you become.",
            ],
        },
        {
            "heading": "How Each Round Works",
            "items": [
                "Each round, your team submits ONE action, just like nations.",
                "Team members propose, vote, and the captain can override if needed.",
                "Your actions target nations — choose who to help, who to punish, and who to investigate.",
            ],
        },
        {
            "heading": "Your Unique Powers",
            "items": [
                "UN Sanction — Binding sanctions that crush a nation's prosperity and influence.",
                "Peacekeeping Shield — Deploy peacekeepers to protect a nation and reduce escalation.",
                "UN Mediation — Force a ceasefire, massively dropping a nation's aggression.",
                "UN Investigation — Expose a nation's covert ops, destroying their credibility.",
                "UN Arms Embargo — Cripple a nation's military capability.",
                "UN Emergency Session — Convene the Security Council to force a nation to stand down.",
                "Humanitarian Aid — Rebuild a struggling nation's economy.",
                "Cyber Treaty — Bind a nation with international rules.",
                "Observer Mission — Deploy observers to gather intel and put a nation on notice.",
            ],
        },
        {
            "heading": "Intel Drops & Mega Challenge",
            "items": [
                "You receive intel drops each round, just like nations. Solve the two-stage puzzle to earn lifelines.",
                "The Mega Challenge is a persistent investigation worth big influence.",
            ],
        },
        {
            "heading": "Round 1 Advice",
            "items": [
                "Watch for early aggression — nations that escalate quickly are your targets for sanctions or mediation.",
                "Humanitarian Aid and Peacekeeping Shield are strong opening moves to build influence.",
                "Nations can launch covert operations that hide their identity. Watch for 'unidentified state actor' in the news — intelligence may expose them later.",
                "Open diplomacy channels with nations. Information is your greatest weapon.",
            ],
        },
    ],
}

BRIEFING_TEMPLATES = {
    "US": {
        "title": "White House Situation Room",
        "summary": "NSA reports increased beaconing from Russian networks targeting defence contractors. CYBERCOM is on alert.",
        "allies": ["UK — Five Eyes intelligence sharing", "Estonia — NATO cyber defence cooperation"],
        "threats": ["Russia — spear-phishing against aerospace and energy sectors", "North Korea — ransomware targeting financial infrastructure"],
        "consequences": "Striking Russia directly without allied consensus risks fracturing NATO support. Coordinate with the UK first.",
    },
    "RU": {
        "title": "Kremlin Cyber Directorate",
        "summary": "US carrier groups repositioning near subsea cables. State media demands a show of strength.",
        "allies": ["North Korea — asymmetric operations partnership"],
        "threats": ["US & UK joint task force targeting our satellite infrastructure", "Estonia hardening Baltic defences"],
        "consequences": "Attacking Estonia triggers NATO Article 5 discussions and massive escalation. Consider softer targets.",
    },
    "CN": {
        "title": "PLA Strategic Support Force — Briefing",
        "summary": "Our CERT detected fresh implants on South-East Asian undersea cables. Western attribution is building.",
        "allies": ["Russia — strategic cyber cooperation pact"],
        "threats": ["US leading a coalition to restrict semiconductor exports", "Japan reinforcing Pacific cyber defences"],
        "consequences": "Overt operations against Japan or India risk pushing both firmly into the US camp.",
    },
    "BR": {
        "title": "Brasilia Cyber Command",
        "summary": "Market volatility following rumours of supply chain compromises in our banking infrastructure.",
        "allies": ["Japan — technology investment corridor", "India — BRICS digital cooperation"],
        "threats": ["US regulators preparing export controls", "China probing our undersea cable infrastructure"],
        "consequences": "Reckless offensive action risks capital flight and investor panic. Diplomacy protects your economy.",
    },
    "EE": {
        "title": "Tallinn Cyber Defence Centre",
        "summary": "NATO CERT intercepted Russian reconnaissance of our e-government systems. We wrote the book on cyber defence — time to prove it.",
        "allies": ["US — NATO intelligence sharing", "UK — joint rapid response framework"],
        "threats": ["Russia — influence campaigns targeting our elections", "North Korea — probing our financial sector"],
        "consequences": "As a small nation, your strength is defence and diplomacy. Offensive operations without allies leave you exposed.",
    },
    "KP": {
        "title": "Reconnaissance General Bureau — War Room",
        "summary": "Sanctions are tightening. Cyber operations are our primary revenue stream. The Supreme Leader demands results.",
        "allies": ["Russia — shadow funding and operational cover"],
        "threats": ["US & Japan tracing our cryptocurrency operations", "UN sanctions threatening remaining trade routes"],
        "consequences": "Getting caught means more sanctions. But successful operations fund the state. High risk, high reward.",
    },
    "UK": {
        "title": "GCHQ Cyber Operations Centre",
        "summary": "NCSC reports increased Russian activity targeting UK critical national infrastructure. Five Eyes allies request coordination.",
        "allies": ["US — Five Eyes, special relationship", "Estonia — NATO rapid response"],
        "threats": ["Russia — subsea cable interference", "North Korea — ransomware hitting NHS supply chain"],
        "consequences": "Failure to defend allies when attacked damages your reputation as a security guarantor. Lead from the front.",
    },
    "JP": {
        "title": "Tokyo Cyber Defence HQ",
        "summary": "NISC detected probing from Chinese APT groups targeting our semiconductor manufacturers. Markets are nervous.",
        "allies": ["US — mutual defence treaty", "Brazil — technology investment partnership"],
        "threats": ["China — industrial espionage targeting chip fabrication", "North Korea — cryptocurrency theft operations"],
        "consequences": "Japan's strength is economic. Protect your prosperity — a market crash hurts more than any cyber strike.",
    },
    "IN": {
        "title": "New Delhi National Cyber Coordination Centre",
        "summary": "Multiple APT groups probing our digital identity infrastructure. Non-alignment gives us options but also makes us a target.",
        "allies": ["Brazil — BRICS digital infrastructure pact", "Canada — Commonwealth and Five Eyes cooperation"],
        "threats": ["China — border tensions spilling into cyber domain", "North Korea — targeting our pharmaceutical sector"],
        "consequences": "India can play all sides. But committing to an alliance means making enemies. Choose your friends wisely.",
    },
    "CA": {
        "title": "Canadian Centre for Cyber Security — Strategic Brief",
        "summary": "Five Eyes intelligence sharing has flagged increased hostile cyber activity globally. Canada's diplomatic standing gives us options — but we must protect critical infrastructure.",
        "allies": ["US — closest trading partner and Five Eyes ally", "UK — Commonwealth and intelligence cooperation"],
        "threats": ["Russia — disinformation campaigns targeting democratic institutions", "China — espionage targeting research and IP"],
        "consequences": "Canada's strength is diplomacy and alliances. Build coalitions, defend your networks, and use soft power before reaching for offensive tools.",
    },
    "UN": {
        "title": "UN Security Council — Situation Update",
        "summary": "Global escalation is climbing. Member states expect the Council to act decisively with sanctions and peacekeeping.",
        "allies": ["Neutral nations seeking stability"],
        "threats": ["North Korea — ignoring sanctions", "Russia — blocking Council resolutions"],
        "consequences": "Failing to act when escalation climbs costs you legitimacy. The world is watching — lead or be sidelined.",
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
    # Show only current round's intel drop
    if round_obj:
        intel_items = IntelDrop.query.filter(
            IntelDrop.team_id == current_user.team_id,
            IntelDrop.round_id == round_obj.id,
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

    round_num = round_obj.round_number if round_obj else 0
    if round_num <= 1:
        if team.team_type == "un":
            briefing = {**ROUND_1_BRIEFING_UN}
        else:
            briefing = {**ROUND_1_BRIEFING_NATION}
        # Include the team's starting allies/threats from briefing templates
        base = BRIEFING_TEMPLATES.get(team.nation_code, {})
        briefing["allies"] = base.get("allies", [])
        briefing["threats"] = base.get("threats", [])
    else:
        briefing = _dynamic_briefing(team, round_num)
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
            "timer_seconds": 5 * 60,
            "action_slots": [{"slot": slot} for slot in (1,)],
            "round": {"id": round_obj.id, "number": round_obj.round_number} if round_obj else None,
            "proposals": proposal_payload,
            "chat_sample": [
                "[Captain] Vote espionage vs honeypots",
                "[GM] Crisis intel dropping in 1 minute",
            ],
            "narrative": _latest_narrative(round_obj.round_number if round_obj else 1),
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
    events = NewsEvent.query.order_by(NewsEvent.created_at.desc()).limit(50).all()
    # Get latest resolved narrative
    latest_resolved = (
        Round.query
        .filter(Round.status == "resolved", Round.narrative.isnot(None))
        .order_by(Round.round_number.desc())
        .first()
    )
    return jsonify({
        "events": [
            {"id": ev.id, "message": ev.message, "created_at": ev.created_at.isoformat() if ev.created_at else None}
            for ev in events
        ],
        "narrative": latest_resolved.narrative if latest_resolved else None,
        "narrative_round": latest_resolved.round_number if latest_resolved else None,
    })


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
    # Intel drops expire at end of their round
    active_round = get_active_round()
    if not active_round or intel.round_id != active_round.id:
        return jsonify({"error": "Intel expired — you can only solve drops during their round."}), 400
    if not verify_password(intel.solution_hash, answer):
        return jsonify({"error": "incorrect_solution"}), 400
    intel.solved_by_team_id = current_user.team_id
    intel.solved_at = db.func.now()
    db.session.add(intel)

    # Award influence points — first solver gets 20, second 18, third 16, etc.
    already_solved = IntelDrop.query.filter(
        IntelDrop.round_id == intel.round_id,
        IntelDrop.solved_by_team_id.isnot(None),
        IntelDrop.id != intel.id,
    ).count()
    position = already_solved + 1  # 1-indexed
    influence_reward = max(2, 22 - (position * 2))  # 20, 18, 16, 14, ...
    team = Team.query.get(current_user.team_id)
    team.current_influence += influence_reward
    db.session.add(team)

    # Only the first 3 solvers earn a lifeline
    lifeline = None
    lifeline_type = _lifeline_type_for_intel(intel)
    if position <= 3:
        lifeline = award_lifeline(current_user.team_id, lifeline_type, awarded_for=f"intel:{intel.id}")
    team_name = team.nation_name if team else "A team"
    lifeline_text = f" and a {lifeline_type.replace('_', ' ')}" if position <= 3 else ""
    news = NewsEvent(message=f"{team_name} cracked an intel drop ({intel.puzzle_type}) — #{position} to solve! +{influence_reward} influence{lifeline_text}.")
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
            "position": position,
            "influence_reward": influence_reward,
            "lifeline": {
                "id": lifeline.id,
                "lifeline_type": lifeline.lifeline_type,
                "remaining_uses": lifeline.remaining_uses,
            } if lifeline else None,
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
                "visibility": action.visibility,
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

    # Reveal the chosen enemy's action from the current round
    payload = request.get_json(silent=True) or {}
    target_team_id = payload.get("target_team_id")
    if not target_team_id:
        db.session.rollback()
        return jsonify({"error": "Select a target nation to spy on."}), 400

    round_obj = get_active_round()
    if not round_obj:
        db.session.rollback()
        return jsonify({"error": "No active round — use this during a round."}), 400

    target_team = Team.query.get(target_team_id)
    if not target_team or target_team.id == current_user.team_id:
        db.session.rollback()
        return jsonify({"error": "Invalid target."}), 400

    enemy_proposal = (
        ActionProposal.query
        .filter(
            ActionProposal.round_id == round_obj.id,
            ActionProposal.team_id == target_team_id,
        )
        .first()
    )

    hint = None
    if enemy_proposal:
        action_def = ACTION_LOOKUP.get(enemy_proposal.action_code)
        target_of_action = Team.query.get(enemy_proposal.target_team_id) if enemy_proposal.target_team_id else None
        action_desc = action_def.name if action_def else enemy_proposal.action_code
        if target_of_action:
            action_desc += f" targeting {target_of_action.nation_name}"
        hint = {
            "team_name": target_team.nation_name,
            "action_name": action_desc,
            "slot": enemy_proposal.slot,
        }
    else:
        hint = {
            "team_name": target_team.nation_name,
            "action_name": "No action submitted yet",
            "slot": 1,
        }

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
    incoming_attacks: list[dict] = []
    if my_team:
        my_score = cur_scores.get(my_team.id, my_team.baseline_prosperity + my_team.baseline_security + my_team.baseline_influence)
        my_prev_score = prev_scores.get(my_team.id, my_team.baseline_prosperity + my_team.baseline_security + my_team.baseline_influence)
        my_stats = {
            "prosperity": my_team.baseline_prosperity + my_team.current_prosperity,
            "security": my_team.baseline_security + my_team.current_security,
            "influence": my_team.baseline_influence + my_team.current_influence,
            "escalation": my_team.current_escalation,
            "prosperity_delta": my_team.current_prosperity,
            "security_delta": my_team.current_security,
            "influence_delta": my_team.current_influence,
            "score": my_score,
            "score_delta": my_score - my_prev_score,
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
                "covert": act.covert,
                "detected": act.detected,
                "failure_reason": act.failure_reason,
                "effects": act.effects_summary,
            })

        # Incoming actions against my team this round (attacks, espionage, etc.)
        for act in Action.query.filter_by(round_id=resolved.id, target_team_id=my_team.id).all():
            adef = ACTION_LOOKUP.get(act.action_code)
            if not adef or act.action_code == "WAIT":
                continue
            attacker = teams.get(act.team_id)
            # Respect covert attribution
            if act.covert and not act.detected:
                attacker_name = "An unidentified actor"
            else:
                attacker_name = attacker.nation_name if attacker else "Unknown"
            incoming_attacks.append({
                "attacker": attacker_name,
                "action_name": adef.name,
                "category": adef.category,
                "success": act.success,
                "effects": act.effects_summary,
                "covert": act.covert,
                "detected": act.detected,
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

    round_limit = int(current_app.config.get("ROUND_COUNT", 6))
    is_final = resolved.round_number >= round_limit

    total_escalation = sum(t.current_escalation for t in teams.values())
    # Calculate previous round's total escalation for delta
    prev_total_escalation = 0
    if prev_round:
        # We need to reconstruct previous escalation from score history
        # Simpler: sum escalation contributions from this round's actions
        round_escalation_added = sum(
            (ACTION_LOOKUP.get(a.action_code).escalation if ACTION_LOOKUP.get(a.action_code) and a.success else
             (ACTION_LOOKUP.get(a.action_code).escalation // 2 if ACTION_LOOKUP.get(a.action_code) and not a.success else 0))
            for a in all_actions
        )
    else:
        round_escalation_added = total_escalation

    return jsonify({
        "recap": {
            "round_number": resolved.round_number,
            "is_final_round": is_final,
            "narrative": resolved.narrative or "",
            "events": events,
            "standings": standings,
            "my_stats": my_stats,
            "my_actions": my_actions,
            "incoming_attacks": incoming_attacks,
            "summary": {
                "total_actions": total_actions,
                "successful": total_success,
                "failed": total_actions - total_success,
                "by_category": category_counts,
            },
            "world": {
                "total_escalation": total_escalation,
                "escalation_delta": round_escalation_added,
                "nuke_unlocked": any(
                    a.action_code == "NUKE_LOCK" and a.success
                    for a in all_actions
                ),
            },
        },
    })


@game_bp.get("/final-summary")
@login_required
def final_summary():
    """Return a fun end-of-game summary with awards and stats."""
    from ..data.actions import ACTION_LOOKUP

    # Only available once all rounds are resolved
    round_limit = int(current_app.config.get("ROUND_COUNT", 6))
    resolved_count = Round.query.filter_by(status="resolved").count()
    if resolved_count < round_limit:
        return jsonify({"summary": None})

    teams = {t.id: t for t in Team.query.all()}
    all_actions = Action.query.filter(Action.action_code != "WAIT").all()
    all_alliances = db.session.execute(
        db.text("SELECT team_a_id, team_b_id FROM alliances")
    ).fetchall()
    alliance_pairs = {(r[0], r[1]) for r in all_alliances} | {(r[1], r[0]) for r in all_alliances}

    # --- Final standings ---
    scores = compute_outcome_scores()

    # --- Per-team action stats ---
    team_stats: dict[int, dict] = {t_id: {
        "hostile_actions": 0, "peaceful_actions": 0,
        "covert_ops": 0, "successful_covert": 0,
        "backstabs": 0, "alliances_formed": 0,
        "total_actions": 0, "successful_actions": 0,
        "escalation": t.current_escalation,
        "score_change": t.current_prosperity + t.current_security + t.current_influence - t.current_escalation,
    } for t_id, t in teams.items()}

    hostile_cats = {"non_violent", "violent", "nuclear"}
    peaceful_cats = {"de_escalation", "status_quo"}

    for action in all_actions:
        tid = action.team_id
        if tid not in team_stats:
            continue
        adef = ACTION_LOOKUP.get(action.action_code)
        cat = adef.category if adef else "unknown"
        team_stats[tid]["total_actions"] += 1
        if action.success:
            team_stats[tid]["successful_actions"] += 1
        if cat in hostile_cats:
            team_stats[tid]["hostile_actions"] += 1
            # Backstab = hostile action against an ally
            if action.target_team_id and (tid, action.target_team_id) in alliance_pairs:
                team_stats[tid]["backstabs"] += 1
        if cat in peaceful_cats:
            team_stats[tid]["peaceful_actions"] += 1
        if action.covert:
            team_stats[tid]["covert_ops"] += 1
            if action.success and not action.detected:
                team_stats[tid]["successful_covert"] += 1
        if action.action_code == "FORM_ALLIANCE" and action.success:
            team_stats[tid]["alliances_formed"] += 1

    # --- Score history for sparklines ---
    rounds = Round.query.filter_by(status="resolved").order_by(Round.round_number).all()
    round_ids = [r.id for r in rounds]
    history_rows = OutcomeScoreHistory.query.filter(
        OutcomeScoreHistory.round_id.in_(round_ids)
    ).all()
    score_history: dict[int, list] = {t_id: [] for t_id in teams}
    round_id_to_num = {r.id: r.round_number for r in rounds}
    for row in history_rows:
        score_history[row.team_id].append({
            "round": round_id_to_num.get(row.round_id, 0),
            "score": row.outcome_score,
        })
    for tid in score_history:
        score_history[tid].sort(key=lambda x: x["round"])

    # --- Compute awards ---
    def _best(key: str, reverse: bool = True):
        best_tid = max(team_stats, key=lambda t: team_stats[t][key]) if reverse else min(team_stats, key=lambda t: team_stats[t][key])
        return {"team_id": best_tid, "nation_name": teams[best_tid].nation_name, "value": team_stats[best_tid][key]}

    awards = []

    # Overall Winner
    if scores:
        winner = scores[0]
        awards.append({"title": "Overall Winner", "emoji": "crown", "team": winner["nation_name"], "detail": f"Final score: {winner['score']}"})
        loser = scores[-1]
        awards.append({"title": "Participation Award", "emoji": "turtle", "team": loser["nation_name"], "detail": f"Final score: {loser['score']}"})

    # Most Improved
    best_change = _best("score_change")
    if best_change["value"] != 0:
        awards.append({"title": "Most Improved", "emoji": "rocket", "team": best_change["nation_name"], "detail": f"+{best_change['value']} from baseline"})

    # Most Aggressive
    most_hostile = _best("hostile_actions")
    if most_hostile["value"] > 0:
        awards.append({"title": "Most Aggressive", "emoji": "fire", "team": most_hostile["nation_name"], "detail": f"{most_hostile['value']} hostile operations"})

    # Peace Prize
    most_peaceful = _best("peaceful_actions")
    if most_peaceful["value"] > 0:
        awards.append({"title": "Peace Prize", "emoji": "dove", "team": most_peaceful["nation_name"], "detail": f"{most_peaceful['value']} peaceful actions"})

    # Master Spy
    best_spy = _best("successful_covert")
    if best_spy["value"] > 0:
        awards.append({"title": "Master Spy", "emoji": "detective", "team": best_spy["nation_name"], "detail": f"{best_spy['value']} undetected covert ops"})

    # Backstabber
    most_backstabs = _best("backstabs")
    if most_backstabs["value"] > 0:
        awards.append({"title": "Biggest Backstabber", "emoji": "dagger", "team": most_backstabs["nation_name"], "detail": f"{most_backstabs['value']} attacks on allies"})

    # Best Diplomat
    most_alliances = _best("alliances_formed")
    if most_alliances["value"] > 0:
        awards.append({"title": "Best Diplomat", "emoji": "handshake", "team": most_alliances["nation_name"], "detail": f"{most_alliances['value']} alliances formed"})

    # Most Reckless
    most_escalation = _best("escalation")
    if most_escalation["value"] > 0:
        awards.append({"title": "Most Reckless", "emoji": "bomb", "team": most_escalation["nation_name"], "detail": f"Escalation: {most_escalation['value']}"})

    # Sharpshooter (best success rate, min 3 actions)
    success_rates = {
        tid: (s["successful_actions"] / s["total_actions"]) if s["total_actions"] >= 3 else 0
        for tid, s in team_stats.items()
    }
    best_rate_tid = max(success_rates, key=lambda t: success_rates[t])
    if success_rates[best_rate_tid] > 0:
        pct = int(success_rates[best_rate_tid] * 100)
        awards.append({"title": "Sharpshooter", "emoji": "target", "team": teams[best_rate_tid].nation_name, "detail": f"{pct}% success rate"})

    return jsonify({
        "summary": {
            "standings": scores,
            "awards": awards,
            "score_history": score_history,
            "team_stats": {
                teams[tid].nation_name: stats
                for tid, stats in team_stats.items()
            },
            "total_rounds": round_limit,
            "world": {
                "total_escalation": sum(t.current_escalation for t in teams.values()),
                "total_actions": len(all_actions),
                "total_successful": sum(1 for a in all_actions if a.success),
            },
        },
    })
