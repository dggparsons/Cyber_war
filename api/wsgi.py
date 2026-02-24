"""WSGI entrypoint – use gunicorn for production, socketio.run() for dev."""
from __future__ import annotations

import os

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        # In production, gunicorn is the entrypoint (see Dockerfile CMD).
        # This branch only runs if someone executes wsgi.py directly in prod.
        socketio.run(app, host="0.0.0.0", port=port)
    else:
        # Development: allow the Werkzeug reloader for convenience.
        socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
