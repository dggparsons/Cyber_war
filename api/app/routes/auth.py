"""Authentication and session management endpoints."""
from __future__ import annotations

import secrets

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User, Team
from ..services.team_assignment import assign_team_for_user
from ..utils.passwords import generate_random_password, hash_password, verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

TEAM_JOIN_CODES = {
    "NEXUS-OPS": "NEXUS",
    "IRON-VANGUARD": "IRON",
    "GHOST-SHELL": "GNET",
    "CORAL-TIDE": "CORAL",
    "FROST-WATCH": "FRST",
    "SHADOW-VEIL": "SHDW",
    "DAWN-SHIELD": "DAWN",
    "NEON-GRID": "NEON",
    "SKY-ARC": "SKY",
    "LOTUS-VAULT": "LOTUS",
    "UN-PEACE": "UN",
}


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    display_name = (payload.get("display_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()

    if not display_name:
        return jsonify({"error": "display_name is required"}), 400
    if not email:
        return jsonify({"error": "email is required"}), 400

    user = User.query.filter_by(email=email).first()
    status_code = 200 if user else 201
    password = generate_random_password(14)
    password_hash = hash_password(password)

    if user:
        user.display_name = display_name or user.display_name
        user.password_hash = password_hash
    else:
        user = User(display_name=display_name, email=email, password_hash=password_hash)
        db.session.add(user)

    db.session.commit()

    return (
        jsonify(
            {
                "user": {
                    "id": user.id,
                    "display_name": user.display_name,
                    "email": user.email,
                    "team_id": user.team_id,
                },
                "password": password,
                "status": "password_reset" if status_code == 200 else "registered",
            }
        ),
        status_code,
    )


@auth_bp.post("/join")
def join_with_code():
    payload = request.get_json(silent=True) or {}
    display_name = (payload.get("display_name") or "").strip()
    join_code = (payload.get("join_code") or "").strip().upper()

    if not display_name or not join_code:
        return jsonify({"error": "display_name and join_code required"}), 400

    nation_code = TEAM_JOIN_CODES.get(join_code)
    if not nation_code:
        return jsonify({"error": "invalid_join_code"}), 400

    team = Team.query.filter_by(nation_code=nation_code).first()
    if not team:
        return jsonify({"error": "team_not_found"}), 404

    email = f"{display_name.replace(' ', '').lower()}+{join_code.lower()}@join.local"
    password = generate_random_password(12)
    password_hash = hash_password(password)

    user = User(display_name=display_name, email=email, password_hash=password_hash, team_id=team.id)
    db.session.add(user)
    db.session.commit()
    login_user(user)

    return jsonify(
        {
            "user": {
                "id": user.id,
                "display_name": user.display_name,
                "email": user.email,
                "team_id": user.team_id,
            },
            "password": password,
        }
    )


@auth_bp.post("/login")
def login():
    if current_user.is_authenticated:
        return jsonify(_serialize_user(current_user)), 200

    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(user.password_hash, password):
        return jsonify({"error": "invalid credentials"}), 401

    # Issue new session token and enforce single session logic (later to extend with Socket.IO).
    user.session_token = secrets.token_hex(32)

    assigned_team = None
    if not user.team_id:
        assigned_team = assign_team_for_user(user)

    db.session.add(user)
    db.session.commit()

    login_user(user)

    response = _serialize_user(user)
    if assigned_team:
        response["team"] = {"id": assigned_team.id, "nation_name": assigned_team.nation_name}
    return jsonify(response)


@auth_bp.post("/logout")
@login_required
def logout():
    user = current_user
    user.session_token = None
    db.session.add(user)
    db.session.commit()
    logout_user()
    return jsonify({"status": "logged_out"})


@auth_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, **_serialize_user(current_user)})


def _serialize_user(user: User) -> dict:
    return {
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "team_id": user.team_id,
            "role": user.role,
            "is_captain": user.is_captain,
        },
        "session_token": user.session_token,
    }
