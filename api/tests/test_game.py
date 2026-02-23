"""Tests for game routes."""
from app.extensions import db
from app.models import Team, Round, User
from app.utils.passwords import hash_password
from app.seeds.team_data import TEAMS


def _seed_and_login(client, db_session):
    """Helper: seed teams/rounds, create user, login, return user data."""
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.add(Round(round_number=1, status="pending"))
        db_session.session.commit()
    reg = client.post("/api/auth/register", json={
        "display_name": "GameTester",
        "email": "gametester@example.com",
    })
    password = reg.get_json()["password"]
    login = client.post("/api/auth/login", json={
        "email": "gametester@example.com",
        "password": password,
    })
    return login.get_json()


def test_list_actions(client, db):
    _seed_and_login(client, db)
    resp = client.get("/api/game/actions")
    assert resp.status_code == 200
    actions = resp.get_json()
    assert len(actions) > 0
    codes = [a["code"] for a in actions]
    assert "WAIT" in codes
    assert "CYBER_STRIKE" in codes


def test_leaderboard(client, db):
    _seed_and_login(client, db)
    resp = client.get("/api/game/leaderboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "entries" in data


def test_news_feed(client, db):
    _seed_and_login(client, db)
    resp = client.get("/api/game/news")
    assert resp.status_code == 200


def test_game_state(client, db):
    _seed_and_login(client, db)
    resp = client.get("/api/game/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "team" in data
    assert "timer" in data
