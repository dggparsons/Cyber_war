"""Simple narrative generation for resolved rounds."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

CATEGORY_TEMPLATES = {
    "de_escalation": {
        True: "{actor} calmed tensions with {action} and offered relief to {target}.",
        False: "{actor}'s attempt at {action} faltered, leaving {target} suspicious.",
    },
    "status_quo": {
        True: "{actor} maintained posture via {action}, keeping internal focus.",
        False: "{actor} struggled to execute {action}, exposing bureaucratic cracks.",
    },
    "posturing": {
        True: "{actor} flexed with {action}, rattling {target}.",
        False: "{actor}'s {action} fizzled, emboldening {target}.",
    },
    "non_violent": {
        True: "{actor} struck quietly with {action}, eroding {target}'s position.",
        False: "{actor} misfired on {action}, giving {target} cover to regroup.",
    },
    "violent": {
        True: "{actor} escalated hard with {action}, inflicting real damage on {target}.",
        False: "{actor} failed to land {action}, and {target} is mobilising in response.",
    },
    "nuclear": {
        True: "☢ {actor} unleashed {action} against {target}. The world spiralled into doom.",
        False: "{actor}'s nuclear gambit, {action}, was foiled before impact.",
    },
}


def _format_highlight(item: dict) -> str:
    actor = item.get("actor") or "Unknown nation"
    action_name = item.get("action_name") or item.get("action_code") or "an action"
    target = item.get("target") or "global rivals"
    category = item.get("category") or "status_quo"
    success = bool(item.get("success"))

    template = CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["status_quo"])[success]
    return template.format(actor=actor, action=action_name, target=target)


def generate_round_narrative(
    round_number: int,
    highlights: List[dict],
    crisis: Optional[dict] = None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    sentences: list[str] = []

    if crisis:
        sentences.append(
            f"Crisis Update — {crisis.get('title')}: {crisis.get('summary')} ({crisis.get('effect')})."
        )

    if highlights:
        for item in highlights[:6]:
            sentences.append(_format_highlight(item))
    else:
        sentences.append("Teams largely regrouped and traded intel.")

    header = f"Round {round_number} Report ({timestamp}): "
    return header + " ".join(sentences)
