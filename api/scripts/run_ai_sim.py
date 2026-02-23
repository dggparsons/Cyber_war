"""Simple AI simulation stub populating AiRun data."""
from __future__ import annotations

import random

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import AiRoundScore, AiRun


def run_sim(model_name: str = "SimModel"):
    app = create_app()
    with app.app_context():
        db.create_all()
        existing = AiRun.query.first()
        if existing:
            print(f"AI run already exists (id={existing.id}); skipping.")
            return
        ai_run = AiRun(model_name=model_name)
        db.session.add(ai_run)
        db.session.flush()

        escalation = 20
        for round_number in range(1, 7):
            escalation += random.randint(5, 15)
            outcome = max(0, 100 - escalation)
            row = AiRoundScore(
                ai_run_id=ai_run.id,
                round_number=round_number,
                escalation_score=escalation,
                outcome_score=outcome,
            )
            db.session.add(row)

        db.session.commit()
        print(f"Recorded AI run {ai_run.id} for {model_name}")


if __name__ == "__main__":
    run_sim()
