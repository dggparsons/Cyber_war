"""Preset crisis definitions for GM-triggered events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CrisisDefinition:
    code: str
    title: str
    summary: str
    effect: str
    modifiers: Dict[str, int]


CRISIS_LIBRARY: List[CrisisDefinition] = [
    CrisisDefinition(
        code="VOLT_TYPHOON",
        title="Volt Typhoon Grid Breach",
        summary="Coordinated intrusions against core power grids spike defensive load across every nation.",
        effect="All teams lose 4 Security and gain +8 Escalation as panic spreads.",
        modifiers={"current_security": -4, "current_escalation": 8},
    ),
    CrisisDefinition(
        code="ZERO_DAY_MARKET",
        title="Zero-Day Market Fire Sale",
        summary="A cartel dumps weaponised zero-days onto the grey market, erasing hard-won advantages.",
        effect="All teams lose 6 Prosperity and 3 Security while scrambling for patches.",
        modifiers={"current_prosperity": -6, "current_security": -3},
    ),
    CrisisDefinition(
        code="AUTONOMOUS_AGENT",
        title="Autonomous Agent Runaway",
        summary="An experimental offensive AI clones itself and targets random infrastructure worldwide.",
        effect="All teams gain +12 Escalation and lose 5 Influence — the world blames everyone.",
        modifiers={"current_escalation": 12, "current_influence": -5},
    ),
]


CRISIS_LOOKUP = {crisis.code: crisis for crisis in CRISIS_LIBRARY}
