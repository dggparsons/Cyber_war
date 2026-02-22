"""WSGI entrypoint – always use socketio.run() for WebSocket support."""
from __future__ import annotations

import os

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
