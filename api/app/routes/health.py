"""Basic health/diagnostics endpoints for the PoC."""
from __future__ import annotations

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.get("/")
def healthcheck():
    return jsonify({"status": "ok"})
