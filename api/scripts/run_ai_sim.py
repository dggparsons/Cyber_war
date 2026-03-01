"""Run the AI Shadow Game simulation and persist results."""
from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.services.ai_simulation import run_ai_simulation


def main(model_name: str = "claude-shadow"):
    app = create_app()
    with app.app_context():
        db.create_all()
        ai_run = run_ai_simulation(model_name=model_name)
        print(f"AI simulation complete: run_id={ai_run.id} model={ai_run.model_name}")
        print(f"  final_escalation={ai_run.final_escalation} doom={ai_run.doom_triggered}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "claude-shadow"
    main(model_name=name)
