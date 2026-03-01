"""Tests for lifelines: phone-a-friend and intel solve."""
from app.extensions import db as _db
from app.models import Team, Round, User, IntelDrop, Lifeline
from app.seeds.team_data import TEAMS
from app.utils.passwords import hash_password


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.add(Round(round_number=1, status="active"))
        db_session.session.commit()


def _login(client, db_session, email="lifeline@example.com"):
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "LifelineTester",
        "email": email,
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={"email": email, "password": password})
    user = User.query.filter_by(email=email).first()
    # Ensure user has a team
    if not user.team_id:
        team = Team.query.first()
        user.team_id = team.id
        db_session.session.commit()
    return user


def test_phone_a_friend_no_lifeline(client, db):
    user = _login(client, db, email="nophone@example.com")
    resp = client.post("/api/game/lifelines/phone-a-friend")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_phone_a_friend_lifeline"


def test_phone_a_friend_with_lifeline(client, db):
    user = _login(client, db, email="hasphone@example.com")
    lifeline = Lifeline(
        team_id=user.team_id,
        lifeline_type="phone_a_friend",
        remaining_uses=1,
    )
    db.session.add(lifeline)
    db.session.commit()
    resp = client.post("/api/game/lifelines/phone-a-friend")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "hint" in data
    assert "team_name" in data["hint"]
    assert "action_name" in data["hint"]


def test_intel_solve_correct(client, db):
    user = _login(client, db, email="intelcorrect@example.com")
    solution = "ESCALATION"
    sol_hash = hash_password(solution)
    round_obj = Round.query.filter_by(status="active").first()
    intel = IntelDrop(
        round_id=round_obj.id if round_obj else 1,
        team_id=user.team_id,
        puzzle_type="cipher",
        clue="Test cipher clue",
        reward="false flag lifeline",
        solution_hash=sol_hash,
    )
    db.session.add(intel)
    db.session.commit()
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": intel.id,
        "answer": solution,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["intel_id"] == intel.id
    assert "lifeline" in data


def test_intel_solve_wrong(client, db):
    user = _login(client, db, email="intelwrong@example.com")
    solution = "CORRECT"
    sol_hash = hash_password(solution)
    round_obj = Round.query.filter_by(status="active").first()
    intel = IntelDrop(
        round_id=round_obj.id if round_obj else 1,
        team_id=user.team_id,
        puzzle_type="cipher",
        clue="Another clue",
        reward="phone a friend lifeline",
        solution_hash=sol_hash,
    )
    db.session.add(intel)
    db.session.commit()
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": intel.id,
        "answer": "WRONG_ANSWER",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "incorrect_solution"
