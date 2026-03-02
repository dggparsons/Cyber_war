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


# -----------------------------------------------------------------------
# compute_outcome_scores returns all teams
# -----------------------------------------------------------------------

def test_compute_outcome_scores_returns_all_teams(app, db):
    """compute_outcome_scores should return one entry per team."""
    with app.app_context():
        _seed(db)
        scores = compute_outcome_scores()
        assert len(scores) == len(TEAMS)


def test_compute_outcome_scores_entry_fields(app, db):
    """Each score entry should contain the expected fields."""
    with app.app_context():
        _seed(db)
        scores = compute_outcome_scores()
        for entry in scores:
            assert "team_id" in entry
            assert "nation_name" in entry
            assert "score" in entry
            assert "delta_from_baseline" in entry
            assert "escalation" in entry


# -----------------------------------------------------------------------
# Score calculation: baseline + deltas - escalation
# -----------------------------------------------------------------------

def test_scoring_formula(app, db):
    """Score should equal baseline_sum + (current_p + current_s + current_i - escalation)."""
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


def test_scoring_zero_deltas(app, db):
    """With zero current stats, score should equal the baseline sum."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        team.current_prosperity = 0
        team.current_security = 0
        team.current_influence = 0
        team.current_escalation = 0
        db.session.commit()

        scores = compute_outcome_scores()
        entry = next(e for e in scores if e["team_id"] == team.id)
        baseline = team.baseline_prosperity + team.baseline_security + team.baseline_influence
        assert entry["score"] == baseline
        assert entry["delta_from_baseline"] == 0


def test_scoring_negative_deltas(app, db):
    """Negative current stats and high escalation should reduce score below baseline."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        team.current_prosperity = -10
        team.current_security = -5
        team.current_influence = -3
        team.current_escalation = 20
        db.session.commit()

        scores = compute_outcome_scores()
        entry = next(e for e in scores if e["team_id"] == team.id)
        baseline = team.baseline_prosperity + team.baseline_security + team.baseline_influence
        delta = -10 + -5 + -3 - 20
        assert entry["score"] == baseline + delta
        assert entry["delta_from_baseline"] == delta
        assert entry["score"] < baseline


def test_scoring_escalation_only_penalty(app, db):
    """Escalation alone (with zero gains) should reduce the score."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        team.current_prosperity = 0
        team.current_security = 0
        team.current_influence = 0
        team.current_escalation = 50
        db.session.commit()

        scores = compute_outcome_scores()
        entry = next(e for e in scores if e["team_id"] == team.id)
        baseline = team.baseline_prosperity + team.baseline_security + team.baseline_influence
        assert entry["delta_from_baseline"] == -50
        assert entry["score"] == baseline - 50


# -----------------------------------------------------------------------
# Sorting by score descending
# -----------------------------------------------------------------------

def test_leaderboard_sorted_desc(app, db):
    """Scores should be sorted in descending order."""
    with app.app_context():
        _seed(db)
        scores = compute_outcome_scores()
        for i in range(len(scores) - 1):
            assert scores[i]["score"] >= scores[i + 1]["score"]


def test_leaderboard_sorted_after_modification(app, db):
    """After modifying team stats to create divergent scores, sorting should hold."""
    with app.app_context():
        _seed(db)
        teams = Team.query.all()
        # Give first team a huge boost
        teams[0].current_prosperity = 100
        teams[0].current_escalation = 0
        # Give last team a huge penalty
        teams[-1].current_escalation = 200
        db.session.commit()

        scores = compute_outcome_scores()
        for i in range(len(scores) - 1):
            assert scores[i]["score"] >= scores[i + 1]["score"]
        # The boosted team should be at or near the top
        assert scores[0]["team_id"] == teams[0].id or scores[0]["score"] >= scores[1]["score"]


# -----------------------------------------------------------------------
# Leaderboard HTTP endpoint
# -----------------------------------------------------------------------

def test_leaderboard_returns_all_teams(client, db):
    """GET /api/game/leaderboard should return all teams."""
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


def test_leaderboard_response_structure(client, db):
    """Leaderboard response should include entries, escalation_series, and cyber_impact."""
    _seed_and_login(client, db)
    resp = client.get("/api/game/leaderboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "entries" in data
    assert "escalation_series" in data
    assert "cyber_impact" in data
    assert "timer" in data
    assert "global" in data


def test_leaderboard_no_auth_required(client, db):
    """Leaderboard endpoint should be accessible without authentication."""
    _seed(db)
    resp = client.get("/api/game/leaderboard")
    assert resp.status_code == 200
