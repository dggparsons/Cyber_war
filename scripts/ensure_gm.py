#!/usr/bin/env python3
"""
Ensure a GM/admin account exists with credentials from environment variables.

Usage:
    GM_USERNAME=gm@example.com GM_PASSWORD=SuperSecret \
      python scripts/ensure_gm.py
"""
from __future__ import annotations

import os
import sys

from app import create_app
from app.extensions import db
from app.models import User
from app.utils.passwords import hash_password


def main():
    username = os.environ.get("GM_USERNAME")
    password = os.environ.get("GM_PASSWORD")
    if not username or not password:
        print("GM_USERNAME and GM_PASSWORD environment variables are required.", file=sys.stderr)
        raise SystemExit(1)

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=username).first()
        if user:
            user.password_hash = hash_password(password)
            user.role = "gm"
            user.display_name = user.display_name or "Game Master"
            print(f"Updated existing GM user: {username}")
        else:
            user = User(
                display_name="Game Master",
                email=username,
                password_hash=hash_password(password),
                role="gm",
                is_captain=True,
            )
            db.session.add(user)
            print(f"Created GM user: {username}")
        db.session.commit()


if __name__ == "__main__":
    main()
