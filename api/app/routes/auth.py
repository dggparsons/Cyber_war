"""Authentication and session management endpoints."""
from __future__ import annotations

import secrets
import uuid

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, limiter, socketio
from ..models import User, Team
from ..services.team_assignment import assign_team_for_user
from ..utils.passwords import generate_random_password, hash_password, verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

TEAM_JOIN_CODES = {
    "NEXUS-OPS": "US",
    "IRON-VANGUARD": "RU",
    "GHOST-SHELL": "CN",
    "CORAL-TIDE": "BR",
    "FROST-WATCH": "EE",
    "SHADOW-VEIL": "KP",
    "DAWN-SHIELD": "UK",
    "NEON-GRID": "JP",
    "SKY-ARC": "IN",
    "LOTUS-VAULT": "IL",
    "UN-PEACE": "UN",
}


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    payload = request.get_json(silent=True) or {}
    display_name = (payload.get("display_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()

    if not display_name:
        return jsonify({"error": "display_name is required"}), 400
    if not email:
        return jsonify({"error": "email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"error": "Email already registered"}), 409

    password = generate_random_password(14)
    password_hash = hash_password(password)

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
                "status": "registered",
            }
        ),
        201,
    )


@auth_bp.post("/join")
@limiter.limit("10 per minute")
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

    # Check seat cap
    current_count = User.query.filter_by(team_id=team.id).count()
    if current_count >= team.seat_cap:
        return jsonify({"error": "team_full", "message": f"Team has reached its seat cap of {team.seat_cap}"}), 409

    # Random suffix guarantees uniqueness even with duplicate display names
    suffix = uuid.uuid4().hex[:8]
    email = f"{display_name.replace(' ', '').lower()}+{join_code.lower()}.{suffix}@join.local"
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
@limiter.limit("10 per minute")
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

    # Issue new session token and kick any existing session via Socket.IO.
    old_token = user.session_token
    user.session_token = secrets.token_hex(32)
    if old_token:
        socketio.emit(
            "session:kick",
            {"reason": "Logged in from another location."},
            namespace="/team",
            room=f"user:{user.id}",
        )

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
