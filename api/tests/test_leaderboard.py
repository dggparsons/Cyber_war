"""Tests for leaderboard endpoint and scoring."""
from app.extensions import db as _db
from app.models import Team, Round, User
from app.seeds.team_data import TEAMS
from app.services.leaderboard import compute_outcome_scores


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.add(Round(round_number=1, status="pending"))
        db_session.session.commit()


def _seed_and_login(client, db_session, email="lb@example.com"):
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "LBTester",
        "email": email,
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={"email": email, "password": password})


def test_leaderboard_returns_all_teams(client, db):
    _seed_and_login(client, db)
    resp = client.get("/api/game/leaderboard")
    assert resp.status_code == 200
    data = resp.get_json()
    entries = data["entries"]
    assert len(entries) == len(TEAMS)
    for entry in entries:
        assert "team_id" in entry
        assert "nation_name" in entry
        assert "score" in entry


def test_scoring_formula(app, db):
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        # Modify a team to verify formula
        team.current_prosperity = 10
        team.current_security = 5
        team.current_influence = 3
        team.current_escalation = 8
        db.session.commit()

        scores = compute_outcome_scores()
        entry = next(e for e in scores if e["team_id"] == team.id)
        baseline = team.baseline_prosperity + team.baseline_security + team.baseline_influence
        delta = 10 + 5 + 3 - 8
        assert entry["score"] == baseline + delta
        assert entry["delta_from_baseline"] == delta
        assert entry["escalation"] == 8


def test_leaderboard_sorted_desc(app, db):
    with app.app_context():
        _seed(db)
        scores = compute_outcome_scores()
        for i in range(len(scores) - 1):
            assert scores[i]["score"] >= scores[i + 1]["score"]
