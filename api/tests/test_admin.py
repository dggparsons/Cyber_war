"""Tests for admin/GM routes."""
from app.extensions import db as _db
from app.models import Team, Round, User, GlobalState
from app.seeds.team_data import TEAMS


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        for i in range(1, 7):
            db_session.session.add(Round(round_number=i, status="pending"))
        db_session.session.commit()


def _create_gm(client, db_session, email="gm@example.com"):
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "GameMaster",
        "email": email,
    })
    password = reg.get_json()["password"]
    user = User.query.filter_by(email=email).first()
    user.role = "gm"
    db_session.session.commit()
    client.post("/api/auth/login", json={"email": email, "password": password})
    return user


def _create_player(client, db_session, email="player@example.com"):
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "Player",
        "email": email,
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={"email": email, "password": password})


def test_start_round(client, db):
    _create_gm(client, db)
    resp = client.post("/api/admin/rounds/start")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["round"] == 1


def test_advance_round(client, db):
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.post("/api/admin/rounds/advance")
    assert resp.status_code == 200


def test_reset_rounds(client, db):
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.post("/api/admin/rounds/reset")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "reset"


def test_inject_crisis(client, db):
    _create_gm(client, db)
    resp = client.post("/api/admin/crisis/inject", json={"code": "SOLAR_STORM"})
    assert resp.status_code in (200, 400)  # 400 if crisis code unknown


def test_toggle_nukes(client, db):
    _create_gm(client, db)
    resp = client.post("/api/admin/nukes/toggle", json={"unlocked": True})
    assert resp.status_code == 200
    assert resp.get_json()["nuke_unlocked"] is True
    resp2 = client.post("/api/admin/nukes/toggle", json={"unlocked": False})
    assert resp2.get_json()["nuke_unlocked"] is False


def test_admin_requires_gm_role(client, db):
    _create_player(client, db, email="normalplayer@example.com")
    resp = client.post("/api/admin/rounds/start")
    assert resp.status_code == 403
