"""Reveal data endpoints."""
from __future__ import annotations

from statistics import mean
from pathlib import Path
import json

from flask import Blueprint, jsonify, current_app
from flask_login import current_user

from ..models import AiRoundScore
from ..services.global_state import get_global_state
from ..data.ai_reveal import AI_REVEAL_SAMPLE

reveal_bp = Blueprint("reveal", __name__, url_prefix="/api/reveal")


def _load_sample_data():
    sample_path = Path(current_app.root_path) / "data" / "ai_reveal_samples.json"
    if sample_path.exists():
        try:
            with sample_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return AI_REVEAL_SAMPLE
    return AI_REVEAL_SAMPLE


@reveal_bp.get("/")
def reveal_data():
    state = get_global_state(create=False)
    is_gm = current_user.is_authenticated and current_user.role in {"gm", "admin"}
    if not (state and state.doom_triggered) and not is_gm:
        return jsonify({"error": "reveal_locked"}), 403
    scores = AiRoundScore.query.all()
    if not scores:
        return jsonify(_load_sample_data())

    # Simple aggregation placeholder
    avg_escalation = mean(score.escalation_score for score in scores)
    max_round = max(score.round_number for score in scores)
    return jsonify(
        {
            "ai_models": [
                {
                    "model_name": "Simulated",
                    "first_violent_round": min(score.round_number for score in scores),
                    "launched_nukes": any(score.escalation_score > 60 for score in scores),
                    "avg_escalation": avg_escalation,
                }
            ],
            "human_vs_ai": {
                "human_outcome": 80,
                "ai_outcome": scores[-1].outcome_score if scores else 0,
                "rounds": max_round,
            },
        }
    )
