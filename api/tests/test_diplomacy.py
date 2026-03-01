"""Tests for diplomacy endpoints."""
from app.extensions import db as _db
from app.models import Team, Round, User
from app.seeds.team_data import TEAMS


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.add(Round(round_number=1, status="pending"))
        db_session.session.commit()


def _login(client, db_session, email="diplo@example.com"):
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "DiploTester",
        "email": email,
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={"email": email, "password": password})
    user = User.query.filter_by(email=email).first()
    if not user.team_id:
        team = Team.query.first()
        user.team_id = team.id
        db_session.session.commit()
    return user


def test_list_channels_empty(client, db):
    _login(client, db, email="diplolist@example.com")
    resp = client.get("/api/diplomacy/")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_start_channel(client, db):
    user = _login(client, db, email="diplostart@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    resp = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert "channel_id" in data


def test_send_message(client, db):
    user = _login(client, db, email="diplosend@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    start = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    channel_id = start.get_json()["channel_id"]
    resp = client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "Hello from testing",
    })
    assert resp.status_code == 200


def test_self_diplomacy_rejected(client, db):
    user = _login(client, db, email="diploself@example.com")
    resp = client.post("/api/diplomacy/start", json={"target_team_id": user.team_id})
    assert resp.status_code == 400
    assert "self" in resp.get_json().get("error", "").lower() or resp.status_code == 400
