"""World Engine — LLM-powered narrative generation with template fallback."""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

CATEGORY_TEMPLATES = {
    "de_escalation": {"success": "{actor} extended an olive branch to {target} via {action}.", "failure": "{actor} attempted diplomacy with {target} ({action}), but was rebuffed."},
    "status_quo": {"success": "{actor} conducted {action} successfully.", "failure": "{actor} attempted {action} but saw limited results."},
    "posturing": {"success": "{actor} flexed against {target} with {action}.", "failure": "{actor}'s show of force ({action}) against {target} fell flat."},
    "non_violent": {"success": "{actor} struck {target} with {action} — operations compromised.", "failure": "{actor} launched {action} at {target}, but defences held."},
    "violent": {"success": "{actor} unleashed {action} on {target} — devastating impact.", "failure": "{actor}'s {action} against {target} was intercepted."},
    "nuclear": {"success": "CATASTROPHIC: {actor} deployed {action} against {target}. The world will never be the same.", "failure": "{actor} attempted {action} on {target}, but the strike was neutralised."},
}


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
    lines = [f"## Round {round_number} Report\n"]
    if crisis:
        lines.append(f"**CRISIS ACTIVE:** {crisis.get('name', 'Unknown crisis')} — {crisis.get('description', '')}\n")
    for h in highlights[:8]:
        lines.append(f"- {_format_highlight(h)}")
    if not highlights:
        lines.append("An uneasy calm settled over the cyber theatre. No major operations were reported.")
    return "\n".join(lines)


def _llm_narrative(round_number: int, highlights: list[dict], crisis: dict | None = None) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        action_summary = "\n".join(
            f"- {h.get('actor','?')} used {h.get('action_name','?')} on {h.get('target','no target')} ({'SUCCESS' if h.get('success') else 'FAILED'})"
            for h in highlights
        )
        crisis_text = f"\nACTIVE CRISIS: {crisis.get('name', '')} - {crisis.get('description', '')}" if crisis else ""
        prompt = f"""You are a dramatic news broadcaster for a cyber warfare simulation game. Summarise Round {round_number} in 3-4 vivid paragraphs. Be specific about nations and actions. Use a tense, urgent tone.

Actions this round:
{action_summary}
{crisis_text}

Write the broadcast now."""
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.warning("LLM narrative failed, using template fallback: %s", e)
        return None


def generate_round_narrative(round_number: int, highlights: list[dict], crisis: dict | None = None) -> str:
    llm_result = _llm_narrative(round_number, highlights, crisis)
    if llm_result:
        return llm_result
    return _template_narrative(round_number, highlights, crisis)
