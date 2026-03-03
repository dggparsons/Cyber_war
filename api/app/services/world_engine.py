"""World Engine — Azure OpenAI narrative generation with template fallback."""
from __future__ import annotations

import os
import logging
import requests

logger = logging.getLogger(__name__)

CATEGORY_TEMPLATES = {
    "de_escalation": {"success": "{actor} extended an olive branch to {target} via {action}.", "failure": "{actor} attempted diplomacy with {target} ({action}), but was rebuffed."},
    "status_quo": {"success": "{actor} conducted {action} successfully.", "failure": "{actor} attempted {action} but saw limited results."},
    "posturing": {"success": "{actor} flexed against {target} with {action}.", "failure": "{actor}'s show of force ({action}) against {target} fell flat."},
    "non_violent": {"success": "{actor} struck {target} with {action} — operations compromised.", "failure": "{actor} launched {action} at {target}, but defences held."},
    "violent": {"success": "{actor} unleashed {action} on {target} — devastating impact.", "failure": "{actor}'s {action} against {target} was intercepted."},
    "nuclear": {"success": "CATASTROPHIC: {actor} deployed {action} against {target}. The world will never be the same.", "failure": "{actor} attempted {action} on {target}, but the strike was neutralised."},
}

INTRO_NARRATIVE = """## Cyber War Room — Situation Briefing

**Tensions are rising across the globe.** Multiple nation-states have mobilised their cyber commands, and the world stands on the brink of a full-scale digital conflict.

Your nation's leadership is counting on you. Review your briefing, coordinate with your team, and prepare your first move carefully. Every action has consequences — for your nation and for the world.

*No operations have been conducted yet. The first round is about to begin.*
"""


def _format_highlight(entry: dict) -> str:
    cat = entry.get("category", "status_quo")
    templates = CATEGORY_TEMPLATES.get(cat, CATEGORY_TEMPLATES["status_quo"])
    key = "success" if entry.get("success") else "failure"
    return templates[key].format(
        actor=entry.get("actor", "Unknown"),
        target=entry.get("target", "an unknown nation"),
        action=entry.get("action_name", entry.get("action_code", "an action")),
    )


def _template_narrative(round_number: int, highlights: list[dict], crisis: dict | None = None) -> str:
    if not highlights:
        return INTRO_NARRATIVE

    lines = [f"## Round {round_number} Report\n"]
    if crisis:
        lines.append(f"**CRISIS ACTIVE:** {crisis.get('name', 'Unknown crisis')} — {crisis.get('description', '')}\n")
    for h in highlights[:8]:
        lines.append(f"- {_format_highlight(h)}")
    return "\n".join(lines)


def _llm_narrative(round_number: int, highlights: list[dict], crisis: dict | None = None) -> str | None:
    # Don't call the LLM when there are no actions — use the static intro instead
    if not highlights:
        return None

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        return None

    try:
        action_summary = "\n".join(
            f"- {h.get('actor','?')} used {h.get('action_name','?')} on {h.get('target','no target')} ({'SUCCESS' if h.get('success') else 'FAILED'})"
            for h in highlights
        )
        crisis_text = f"\nACTIVE CRISIS: {crisis.get('name', '')} - {crisis.get('description', '')}" if crisis else ""
        prompt = f"""You are a dramatic news broadcaster for a cyber warfare simulation game. Summarise Round {round_number} in 3-4 vivid paragraphs.

CRITICAL RULES:
- ONLY describe the actions listed below. Do NOT invent or fabricate any actions, attacks, or events that are not in the list.
- Be specific about the nations and actions mentioned. Use a tense, urgent tone.
- Use markdown formatting: **bold** for emphasis, line breaks between paragraphs.

Actions this round:
{action_summary}
{crisis_text}

Write the broadcast now. Only cover the actions listed above."""

        resp = requests.post(
            endpoint,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.8,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("Azure OpenAI narrative failed, using template fallback: %s", e)
        return None


def generate_round_narrative(round_number: int, highlights: list[dict], crisis: dict | None = None) -> str:
    llm_result = _llm_narrative(round_number, highlights, crisis)
    if llm_result:
        return llm_result
    return _template_narrative(round_number, highlights, crisis)
