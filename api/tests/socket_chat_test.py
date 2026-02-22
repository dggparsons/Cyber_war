from uuid import uuid4

from wsgi import app
from app.extensions import socketio, db
from app.models import Message


def register_and_login(client):
    email = f"socket-{uuid4()}@example.com"
    resp = client.post('/api/auth/register', json={'display_name': 'Socket User', 'email': email})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    password = resp.get_json()['password']
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, resp.get_data(as_text=True)


def test_team_chat():
    with app.test_client() as client:
        register_and_login(client)
        socket_client = socketio.test_client(app, namespace='/team', flask_test_client=client)
        assert socket_client.is_connected('/team')
        socket_client.get_received('/team')
        socket_client.emit('chat:message', {'content': 'hello world'}, namespace='/team')
        socketio.sleep(0)
        with app.app_context():
            assert Message.query.filter_by(content='hello world').count() >= 1
