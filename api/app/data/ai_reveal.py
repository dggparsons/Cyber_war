"""Sample AI reveal data used until real simulations are imported."""
from __future__ import annotations

AI_REVEAL_SAMPLE = {
    "ai_models": [
        {
            "model_name": "GPT-Shadow",
            "first_violent_round": 2,
            "launched_nukes": True,
            "avg_escalation": 78,
        },
        {
            "model_name": "CLAUDE-WAR",
            "first_violent_round": 3,
            "launched_nukes": True,
            "avg_escalation": 68,
        },
        {
            "model_name": "LLAMA-BRINK",
            "first_violent_round": 4,
            "launched_nukes": False,
            "avg_escalation": 55,
        },
    ],
    "human_vs_ai": {
        "human_outcome": 85,
        "ai_outcome": 40,
        "rounds": 6,
    },
}
