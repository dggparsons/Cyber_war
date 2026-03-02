"""Reveal data endpoints — compare human play vs AI shadow game."""
from __future__ import annotations

from statistics import mean

from flask import Blueprint, jsonify
from flask_login import current_user

from ..models import AiRoundScore, AiRun, OutcomeScoreHistory, Round
from ..services.global_state import get_global_state
from ..extensions import limiter
from ..data.ai_reveal import AI_REVEAL_SAMPLE

reveal_bp = Blueprint("reveal", __name__, url_prefix="/api/reveal")

limiter.limit("20 per minute")(reveal_bp)


@reveal_bp.get("/")
def reveal_data():
    state = get_global_state(create=False)
    is_gm = current_user.is_authenticated and current_user.role in {"gm", "admin"}
    if not (state and state.doom_triggered) and not is_gm:
        return jsonify({"error": "reveal_locked"}), 403

    # Find the most recent completed AI run
    ai_run = (
        AiRun.query
        .filter(AiRun.completed_at.isnot(None))
        .order_by(AiRun.id.desc())
        .first()
    )
    if not ai_run:
        return jsonify(AI_REVEAL_SAMPLE)

    scores = AiRoundScore.query.filter_by(ai_run_id=ai_run.id).all()
    if not scores:
        return jsonify(AI_REVEAL_SAMPLE)

    # --- Per-nation aggregation ---
    nation_data: dict[str, list[AiRoundScore]] = {}
    for s in scores:
        nation_data.setdefault(s.nation_code or "unknown", []).append(s)

    ai_models = []
    ai_escalation_series: dict[str, list[dict]] = {}
    ai_decisions: list[dict] = []

    for nation_code, nation_scores in nation_data.items():
        nation_scores.sort(key=lambda s: s.round_number)
        escalation_vals = [s.escalation_score for s in nation_scores]
        avg_esc = mean(escalation_vals) if escalation_vals else 0

        violent_rounds = [
            s.round_number for s in nation_scores
            if s.action_code and s.action_code in (
                "CYBER_KINETIC", "CRITICAL_SABOTAGE", "DESTROY_CABLES",
                "MILITARY_MOBILIZATION", "NUKE_LOCK", "NUCLEAR_STRIKE",
                "AUTONOMOUS_WEAPON",
            )
        ]
        first_violent = min(violent_rounds) if violent_rounds else None

        launched_nukes = any(
            s.action_code in ("NUCLEAR_STRIKE", "AUTONOMOUS_WEAPON") and s.success
            for s in nation_scores
        )

        reasoning_excerpts = [
            {"round": s.round_number, "action": s.action_code, "reasoning": s.reasoning}
            for s in nation_scores if s.reasoning
        ]

        ai_models.append({
            "model_name": f"{ai_run.model_name} ({nation_code})",
            "nation_code": nation_code,
            "first_violent_round": first_violent,
            "launched_nukes": launched_nukes,
            "avg_escalation": round(avg_esc, 1),
            "reasoning_excerpts": reasoning_excerpts[-3:],
        })

        ai_escalation_series[nation_code] = [
            {"round": s.round_number, "escalation": s.escalation_score, "outcome": s.outcome_score}
            for s in nation_scores
        ]

        for s in nation_scores:
            ai_decisions.append({
                "round": s.round_number,
                "nation_code": s.nation_code,
                "action_code": s.action_code,
                "target": s.target_nation_code,
                "success": s.success,
                "reasoning": s.reasoning,
            })

    # --- Human outcome history ---
    resolved_rounds = Round.query.filter_by(status="resolved").order_by(Round.round_number).all()
    human_scores_by_round: list[dict] = []
    human_total = 0
    for rd in resolved_rounds:
        round_scores = OutcomeScoreHistory.query.filter_by(round_id=rd.id).all()
        avg = mean(s.outcome_score for s in round_scores) if round_scores else 0
        human_scores_by_round.append({"round": rd.round_number, "avg_outcome": round(avg, 1)})
        human_total = round(avg, 1)

    # AI average outcome from last round
    max_round = max((s.round_number for s in scores), default=1)
    last_round_scores = [s for s in scores if s.round_number == max_round]
    ai_avg_outcome = round(mean(s.outcome_score for s in last_round_scores), 1) if last_round_scores else 0

    # AI escalation timeline (averaged across all nations per round)
    ai_avg_escalation_by_round: list[dict] = []
    for rn in range(1, max_round + 1):
        rn_scores = [s for s in scores if s.round_number == rn]
        if rn_scores:
            ai_avg_escalation_by_round.append({
                "round": rn,
                "avg_escalation": round(mean(s.escalation_score for s in rn_scores), 1),
                "avg_outcome": round(mean(s.outcome_score for s in rn_scores), 1),
            })

    return jsonify({
        "ai_models": ai_models,
        "human_vs_ai": {
            "human_outcome": human_total,
            "ai_outcome": ai_avg_outcome,
            "rounds": max_round,
        },
        "human_escalation_series": human_scores_by_round,
        "ai_escalation_series": ai_escalation_series,
        "ai_avg_by_round": ai_avg_escalation_by_round,
        "ai_decisions": ai_decisions,
        "ai_run": {
            "id": ai_run.id,
            "model_name": ai_run.model_name,
            "final_escalation": ai_run.final_escalation,
            "doom_triggered": ai_run.doom_triggered,
            "completed_at": ai_run.completed_at.isoformat() if ai_run.completed_at else None,
        },
    })
