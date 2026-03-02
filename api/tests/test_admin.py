"""Tests for admin/GM routes."""
from app.extensions import db as _db
from app.models import Team, Round, User, GlobalState, Action, CrisisEvent, NewsEvent
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
    user = User.query.filter_by(email=email).first()
    team = Team.query.first()
    user.team_id = team.id
    db_session.session.commit()
    client.post("/api/auth/login", json={"email": email, "password": password})
    return user


# -----------------------------------------------------------------------
# admin_required decorator
# -----------------------------------------------------------------------

def test_admin_requires_gm_role(client, db):
    """Non-admin users should get 403 from admin-protected endpoints."""
    _create_player(client, db, email="normalplayer@example.com")
    resp = client.post("/api/admin/rounds/start")
    assert resp.status_code == 403
    data = resp.get_json()
    assert data["error"] == "admin_only"


def test_admin_requires_authentication(client, db):
    """Unauthenticated requests should be rejected (302 redirect or 401)."""
    _seed(db)
    resp = client.post("/api/admin/rounds/start")
    # Flask-Login redirects unauthenticated users (302) or returns 401
    assert resp.status_code in (302, 401, 403)


def test_admin_role_allowed(client, db):
    """Users with role='admin' should pass the admin_required decorator."""
    _seed(db)
    reg = client.post("/api/auth/register", json={
        "display_name": "AdminUser",
        "email": "admin@example.com",
    })
    password = reg.get_json()["password"]
    user = User.query.filter_by(email="admin@example.com").first()
    user.role = "admin"
    db.session.commit()
    client.post("/api/auth/login", json={"email": "admin@example.com", "password": password})
    resp = client.post("/api/admin/rounds/start")
    assert resp.status_code == 200


# -----------------------------------------------------------------------
# Start round
# -----------------------------------------------------------------------

def test_start_round(client, db):
    """Starting a round should activate round 1."""
    _create_gm(client, db)
    resp = client.post("/api/admin/rounds/start")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["round"] == 1


def test_start_round_activates_pending(client, db):
    """Starting a round should change its status from pending to active."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    round_obj = Round.query.filter_by(round_number=1).first()
    assert round_obj.status == "active"
    assert round_obj.started_at is not None


def test_start_round_idempotent(client, db):
    """Calling start when a round is already active should return that round."""
    _create_gm(client, db)
    resp1 = client.post("/api/admin/rounds/start")
    resp2 = client.post("/api/admin/rounds/start")
    assert resp1.get_json()["round"] == resp2.get_json()["round"]


# -----------------------------------------------------------------------
# Advance round
# -----------------------------------------------------------------------

def test_advance_round(client, db):
    """Advancing should resolve the current round and create/activate the next."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.post("/api/admin/rounds/advance")
    assert resp.status_code == 200
    data = resp.get_json()
    # After advancing from round 1, we should be on round 2
    assert data["round"] == 2


def test_advance_round_resolves_current(client, db):
    """After advancing, the previous round's status should be 'resolved'."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    client.post("/api/admin/rounds/advance")
    round1 = Round.query.filter_by(round_number=1).first()
    assert round1.status == "resolved"
    assert round1.ended_at is not None


def test_advance_round_no_active_round(client, db):
    """Advancing when all rounds are resolved should return 400."""
    _create_gm(client, db)
    # Mark all rounds as resolved so current_round() returns None
    for r in Round.query.all():
        r.status = "resolved"
    db.session.commit()
    resp = client.post("/api/admin/rounds/advance")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_active_round"


# -----------------------------------------------------------------------
# Reset rounds
# -----------------------------------------------------------------------

def test_reset_rounds(client, db):
    """Resetting rounds should wipe game state and recreate pending rounds."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.post("/api/admin/rounds/reset")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "reset"


def test_reset_rounds_clears_actions(client, db):
    """After reset, all actions and active rounds should be cleared."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    client.post("/api/admin/rounds/advance")
    client.post("/api/admin/rounds/reset")
    # All rounds should be pending after reset
    active = Round.query.filter_by(status="active").all()
    resolved = Round.query.filter_by(status="resolved").all()
    assert len(active) == 0
    assert len(resolved) == 0
    pending = Round.query.filter_by(status="pending").all()
    assert len(pending) == 6


def test_reset_rounds_zeroes_team_stats(client, db):
    """After reset, all team current_ stats should be back to zero."""
    _create_gm(client, db)
    team = Team.query.first()
    team.current_prosperity = 15
    team.current_escalation = 10
    db.session.commit()
    client.post("/api/admin/rounds/reset")
    team_fresh = Team.query.get(team.id)
    assert team_fresh.current_prosperity == 0
    assert team_fresh.current_security == 0
    assert team_fresh.current_influence == 0
    assert team_fresh.current_escalation == 0


# -----------------------------------------------------------------------
# Full reset
# -----------------------------------------------------------------------

def test_full_reset(client, db):
    """Full reset should remove player accounts but keep GM accounts."""
    gm = _create_gm(client, db, email="fullreset_gm@example.com")
    # Create a player account
    player_reg = client.post("/api/auth/register", json={
        "display_name": "NormalPlayer",
        "email": "fullreset_player@example.com",
    })
    assert player_reg.status_code == 201
    # Log back in as GM
    client.post("/api/auth/login", json={"email": "fullreset_gm@example.com", "password": gm.password_hash})
    # We need to re-login as GM since the above registered user session replaced it
    gm_user = User.query.filter_by(email="fullreset_gm@example.com").first()
    from app.utils.passwords import generate_random_password, hash_password
    # Just directly call the endpoint since we're already logged in as GM
    resp = client.post("/api/admin/full-reset")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "full_reset"
    # Player should be gone, GM should remain
    assert User.query.filter_by(email="fullreset_player@example.com").first() is None
    assert User.query.filter_by(email="fullreset_gm@example.com").first() is not None


# -----------------------------------------------------------------------
# Toggle nukes
# -----------------------------------------------------------------------

def test_toggle_nukes_on(client, db):
    """Toggling nukes to True should set nuke_unlocked=True."""
    _create_gm(client, db)
    resp = client.post("/api/admin/nukes/toggle", json={"unlocked": True})
    assert resp.status_code == 200
    assert resp.get_json()["nuke_unlocked"] is True


def test_toggle_nukes_off(client, db):
    """Toggling nukes to False should set nuke_unlocked=False."""
    _create_gm(client, db)
    client.post("/api/admin/nukes/toggle", json={"unlocked": True})
    resp = client.post("/api/admin/nukes/toggle", json={"unlocked": False})
    assert resp.status_code == 200
    assert resp.get_json()["nuke_unlocked"] is False


def test_toggle_nukes_roundtrip(client, db):
    """Toggling on then off should reflect correct state each time."""
    _create_gm(client, db)
    resp1 = client.post("/api/admin/nukes/toggle", json={"unlocked": True})
    assert resp1.get_json()["nuke_unlocked"] is True
    resp2 = client.post("/api/admin/nukes/toggle", json={"unlocked": False})
    assert resp2.get_json()["nuke_unlocked"] is False


# -----------------------------------------------------------------------
# Crisis inject/clear
# -----------------------------------------------------------------------

def test_inject_crisis_valid(client, db):
    """Injecting a known crisis code should return 200 with crisis details."""
    _create_gm(client, db)
    resp = client.post("/api/admin/crisis/inject", json={"code": "VOLT_TYPHOON"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == "VOLT_TYPHOON"
    assert "title" in data
    assert "summary" in data


def test_inject_crisis_unknown(client, db):
    """Injecting an unknown crisis code should return 400."""
    _create_gm(client, db)
    resp = client.post("/api/admin/crisis/inject", json={"code": "NONEXISTENT_CRISIS"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "unknown_crisis"


def test_inject_crisis_missing_code(client, db):
    """Injecting without a code should return 400."""
    _create_gm(client, db)
    resp = client.post("/api/admin/crisis/inject", json={})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "missing_code"


def test_inject_crisis_modifies_team_stats(client, db):
    """Injecting VOLT_TYPHOON should reduce security and increase escalation for all teams."""
    _create_gm(client, db)
    team = Team.query.first()
    sec_before = team.current_security
    esc_before = team.current_escalation
    client.post("/api/admin/crisis/inject", json={"code": "VOLT_TYPHOON"})
    db.session.refresh(team)
    assert team.current_security == sec_before - 4
    assert team.current_escalation == esc_before + 8


def test_clear_crisis(client, db):
    """Clearing a crisis should remove the active crisis state."""
    _create_gm(client, db)
    client.post("/api/admin/crisis/inject", json={"code": "VOLT_TYPHOON"})
    resp = client.post("/api/admin/crisis/clear")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["active_crisis"] is None


# -----------------------------------------------------------------------
# Narrative rerun
# -----------------------------------------------------------------------

def test_narrative_rerun_no_active_round(client, db):
    """Rerunning narrative when all rounds are resolved should return 400."""
    _create_gm(client, db)
    # Mark all rounds as resolved so current_round() returns None
    for r in Round.query.all():
        r.status = "resolved"
    db.session.commit()
    resp = client.post("/api/admin/narrative/rerun")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_active_round"


def test_narrative_rerun_with_active_round(client, db):
    """Rerunning narrative with an active round should return a narrative string."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.post("/api/admin/narrative/rerun")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "narrative" in data
    assert isinstance(data["narrative"], str)


# -----------------------------------------------------------------------
# Admin status endpoint
# -----------------------------------------------------------------------

def test_admin_status_returns_expected_fields(client, db):
    """The admin status endpoint should return global, teams, rounds, and player_count."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.get("/api/admin/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "global" in data
    assert "teams" in data
    assert "rounds" in data
    assert "player_count" in data
    assert "current_round" in data
    assert "timer" in data
    assert "crises" in data
    assert "available_crises" in data


def test_admin_status_team_summary(client, db):
    """Admin status should include all teams with correct fields."""
    _create_gm(client, db)
    resp = client.get("/api/admin/status")
    data = resp.get_json()
    teams = data["teams"]
    assert len(teams) == len(TEAMS)
    for t in teams:
        assert "id" in t
        assert "nation_name" in t
        assert "nation_code" in t
        assert "members" in t
        assert "seat_cap" in t


def test_admin_status_round_summary(client, db):
    """Admin status should list rounds with number and status."""
    _create_gm(client, db)
    resp = client.get("/api/admin/status")
    data = resp.get_json()
    rounds = data["rounds"]
    assert len(rounds) == 6
    for r in rounds:
        assert "round_number" in r
        assert "status" in r


def test_admin_status_has_proposal_preview_when_active(client, db):
    """When a round is active, admin status should include proposal_preview."""
    _create_gm(client, db)
    client.post("/api/admin/rounds/start")
    resp = client.get("/api/admin/status")
    data = resp.get_json()
    assert "proposal_preview" in data


# -----------------------------------------------------------------------
# Rounds overview
# -----------------------------------------------------------------------

def test_rounds_overview(client, db):
    """GET /api/admin/rounds should list all rounds."""
    _create_gm(client, db)
    resp = client.get("/api/admin/rounds")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 6
    for r in data:
        assert "id" in r
        assert "round_number" in r
        assert "status" in r
