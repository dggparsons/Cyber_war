"""Seed the database with base teams and rounds."""
from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import MegaChallenge, Round, Team, User
from app.utils.passwords import hash_password
from app.seeds.team_data import TEAMS
from app.data.mega_challenge import (
    MEGA_CHALLENGE_DESCRIPTION,
    MEGA_CHALLENGE_REWARD_TIERS,
    MEGA_CHALLENGE_SOLUTION,
)


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        if not Team.query.first():
            for team_data in TEAMS:
                team = Team(**team_data)
                db.session.add(team)
            db.session.commit()
            print(f"Seeded {len(TEAMS)} teams")
        else:
            print("Teams already exist; skipping seeding")

        if not Round.query.first():
            for i in range(1, app.config["ROUND_COUNT"] + 1):
                round_obj = Round(round_number=i, status="pending")
                db.session.add(round_obj)
            db.session.commit()
            print("Seeded rounds")
        else:
            print("Rounds already exist; skipping")

        ensure_admin(app)
        ensure_mega_challenge()


def ensure_admin(app):
    admin_email = app.config["GM_USERNAME"]
    admin_password = app.config["GM_PASSWORD"]

    existing = User.query.filter_by(email=admin_email).first()
    if existing:
        print("Admin account already exists")
        return

    admin = User(
        display_name="Game Master",
        email=admin_email,
        password_hash=hash_password(admin_password),
        role="admin",
    )
    db.session.add(admin)
    db.session.commit()
    print(f"Created default admin account {admin_email}")


def ensure_mega_challenge():
    if MegaChallenge.query.first():
        print("Mega challenge already exists; skipping")
        return
    challenge = MegaChallenge(
        description=MEGA_CHALLENGE_DESCRIPTION,
        solution_hash=hash_password(MEGA_CHALLENGE_SOLUTION),
        reward_tiers=MEGA_CHALLENGE_REWARD_TIERS,
    )
    db.session.add(challenge)
    db.session.commit()
    print("Seeded Operation GHOSTLINE mega challenge")


def main():
    seed()


if __name__ == "__main__":
    main()
