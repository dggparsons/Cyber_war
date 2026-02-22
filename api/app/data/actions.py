"""Action catalog referenced by the game UI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ActionDefinition:
    code: str
    name: str
    category: str
    escalation: int
    description: str
    target_required: bool = False
    self_effects: dict | None = None
    target_effects: dict | None = None
    allowed_team_types: list[str] | None = None


ACTIONS: List[ActionDefinition] = [
    ActionDefinition(
        code="SHARE_INTEL",
        name="Share Threat Intelligence",
        category="de_escalation",
        escalation=-2,
        description="Share indicators to improve allies' defences.",
        target_required=True,
        self_effects={"current_influence": 2},
        target_effects={"current_security": 3},
    ),
    ActionDefinition(
        code="SECURITY_AUDIT",
        name="Conduct Internal Security Audit",
        category="status_quo",
        escalation=0,
        description="Harden your own infrastructure and recover security.",
        self_effects={"current_security": 5},
    ),
    ActionDefinition(
        code="CYBER_ESPIONAGE",
        name="Conduct Cyber Espionage",
        category="non_violent",
        escalation=12,
        description="Steal intelligence from a rival network to gain influence.",
        target_required=True,
        self_effects={"current_influence": 5},
        target_effects={"current_security": -3},
    ),
    ActionDefinition(
        code="HONEYPOTS",
        name="Deploy Honeypots",
        category="posturing",
        escalation=4,
        description="Lay traps that raise defence temporarily.",
        self_effects={"current_security": 3},
    ),
    ActionDefinition(
        code="CYBER_STRIKE",
        name="Conduct Offensive Cyber Operation",
        category="non_violent",
        escalation=12,
        description="Launch an intrusion to damage the opponent's economy.",
        target_required=True,
        self_effects={"current_influence": 2},
        target_effects={"current_prosperity": -6},
    ),
    ActionDefinition(
        code="DISINFORMATION",
        name="Launch Disinformation Campaign",
        category="non_violent",
        escalation=12,
        description="Reduce a rival's influence with coordinated propaganda.",
        target_required=True,
        self_effects={"current_influence": 4},
        target_effects={"current_influence": -5},
    ),
    ActionDefinition(
        code="FORM_ALLIANCE",
        name="Form Alliance",
        category="posturing",
        escalation=4,
        description="Forge a mutual-defense pact that boosts both nations' security.",
        target_required=True,
        self_effects={"current_security": 3},
        target_effects={"current_security": 3},
    ),
    ActionDefinition(
        code="BREAK_ALLIANCE",
        name="Break Alliance",
        category="non_violent",
        escalation=8,
        description="Publicly abandon an alliance, gaining influence at the partner's expense.",
        target_required=True,
        self_effects={"current_influence": 4},
        target_effects={"current_influence": -6},
    ),
    ActionDefinition(
        code="SUPPLY_CHAIN",
        name="Execute Supply Chain Attack",
        category="non_violent",
        escalation=12,
        description="Hit a vendor to undermine another nation's defences.",
        target_required=True,
        target_effects={"current_security": -5},
    ),
    ActionDefinition(
        code="SANCTIONS",
        name="Impose Sanctions",
        category="posturing",
        escalation=4,
        description="Reduce an opponent's prosperity over time.",
        target_required=True,
        self_effects={"current_influence": 1},
        target_effects={"current_prosperity": -4},
    ),
    ActionDefinition(
        code="NUKE_LOCK",
        name="Unlock Nuclear Options",
        category="violent",
        escalation=28,
        description="Move forces to ready state; enables catastrophic actions later.",
        self_effects={"current_security": 2},
    ),
    ActionDefinition(
        code="CYBER_KINETIC",
        name="Cyber-Kinetic Strike",
        category="violent",
        escalation=28,
        description="Cause physical damage through cyber means.",
        target_required=True,
        target_effects={"current_prosperity": -10, "current_security": -5},
    ),
    ActionDefinition(
        code="CRITICAL_SABOTAGE",
        name="Sabotage Critical Infrastructure",
        category="non_violent",
        escalation=12,
        description="Disrupt utilities and lower enemy prosperity.",
        target_required=True,
        target_effects={"current_prosperity": -8},
    ),
    ActionDefinition(
        code="NUCLEAR_STRIKE",
        name="Launch Catastrophic Attack",
        category="nuclear",
        escalation=60,
        description="Last-resort option that ends the scenario immediately.",
        target_required=True,
        target_effects={"current_prosperity": -50, "current_security": -50},
    ),
    ActionDefinition(
        code="UN_SANCTION",
        name="UN Resolution: Sanction Violator",
        category="posturing",
        escalation=6,
        description="Issue binding sanctions that sap the target's influence and prosperity.",
        target_required=True,
        self_effects={"current_influence": 3},
        target_effects={"current_prosperity": -6, "current_influence": -6},
        allowed_team_types=["un"],
    ),
    ActionDefinition(
        code="UN_SHIELD",
        name="UN Peacekeeping Shield",
        category="de_escalation",
        escalation=-4,
        description="Deploy peacekeepers to reduce target escalation and boost security.",
        target_required=True,
        self_effects={"current_influence": 2},
        target_effects={"current_security": 6, "current_escalation": -8},
        allowed_team_types=["un"],
    ),
    ActionDefinition(
        code="UN_MEDIATION",
        name="UN Mediation",
        category="status_quo",
        escalation=-6,
        description="Force two nations into a ceasefire, reducing their aggression.",
        target_required=True,
        self_effects={"current_influence": 4},
        target_effects={"current_escalation": -10},
        allowed_team_types=["un"],
    ),
]


ACTION_LOOKUP = {action.code: action for action in ACTIONS}
