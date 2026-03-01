"""Socket.IO team chat integration test."""
from app.extensions import socketio, db as _db
from app.models import Message, Team, User
from app.seeds.team_data import TEAMS


def _seed_and_login(client, db_session):
    """Seed teams, register a user, assign to a team, and login."""
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.commit()

    resp = client.post('/api/auth/register', json={
        'display_name': 'Socket User',
        'email': 'socketuser@example.com',
    })
    assert resp.status_code == 201, resp.get_data(as_text=True)
    password = resp.get_json()['password']

    # Assign user to first team so /team namespace connect succeeds
    user = User.query.filter_by(email='socketuser@example.com').first()
    team = Team.query.first()
    user.team_id = team.id
    db_session.session.commit()

    resp = client.post('/api/auth/login', json={
        'email': 'socketuser@example.com',
        'password': password,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)


def test_team_chat(app, client, db):
    _seed_and_login(client, db)
    socket_client = socketio.test_client(app, namespace='/team', flask_test_client=client)
    assert socket_client.is_connected('/team')
    socket_client.get_received('/team')
    socket_client.emit('chat:message', {'content': 'hello world'}, namespace='/team')
    socketio.sleep(0)
    with app.app_context():
        assert Message.query.filter_by(content='hello world').count() >= 1
    socket_client.disconnect(namespace='/team')
