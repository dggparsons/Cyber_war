"""Tests for lifelines: phone-a-friend, intel solve, and lifeline service functions."""
from app.extensions import db as _db
from app.models import Team, Round, User, IntelDrop, Lifeline, ActionProposal
from app.seeds.team_data import TEAMS
from app.services.lifelines import award_lifeline, consume_lifeline, list_lifelines
from app.utils.passwords import hash_password
import pytest


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


# -----------------------------------------------------------------------
# award_lifeline creates lifeline
# -----------------------------------------------------------------------

def test_award_lifeline_creates_new(app, db):
    """award_lifeline should create a new Lifeline record if one does not exist."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        lifeline = award_lifeline(team.id, "phone_a_friend", awarded_for="test")
        db.session.commit()
        assert lifeline is not None
        assert lifeline.lifeline_type == "phone_a_friend"
        assert lifeline.remaining_uses == 1
        assert lifeline.awarded_for == "test"


def test_award_lifeline_increments_existing(app, db):
    """award_lifeline should increment remaining_uses if a lifeline of that type
    already exists for the team."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "phone_a_friend")
        db.session.commit()
        # Award again
        lifeline = award_lifeline(team.id, "phone_a_friend")
        db.session.commit()
        assert lifeline.remaining_uses == 2


def test_award_lifeline_custom_uses(app, db):
    """award_lifeline with uses=3 should create a lifeline with 3 remaining uses."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        lifeline = award_lifeline(team.id, "false_flag", uses=3)
        db.session.commit()
        assert lifeline.remaining_uses == 3


def test_award_lifeline_updates_awarded_for(app, db):
    """Re-awarding a lifeline should update the awarded_for field."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "phone_a_friend", awarded_for="first_award")
        db.session.commit()
        lifeline = award_lifeline(team.id, "phone_a_friend", awarded_for="second_award")
        db.session.commit()
        assert lifeline.awarded_for == "second_award"


# -----------------------------------------------------------------------
# consume_lifeline decrements uses
# -----------------------------------------------------------------------

def test_consume_lifeline_decrements(app, db):
    """consume_lifeline should decrement remaining_uses by 1."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "phone_a_friend", uses=2)
        db.session.commit()
        lifeline = consume_lifeline(team.id, "phone_a_friend")
        db.session.commit()
        assert lifeline.remaining_uses == 1


def test_consume_lifeline_to_zero(app, db):
    """Consuming a lifeline with remaining_uses=1 should leave 0 remaining."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "false_flag", uses=1)
        db.session.commit()
        lifeline = consume_lifeline(team.id, "false_flag")
        db.session.commit()
        assert lifeline.remaining_uses == 0


# -----------------------------------------------------------------------
# consume_lifeline raises ValueError when none available
# -----------------------------------------------------------------------

def test_consume_lifeline_raises_when_none_exist(app, db):
    """consume_lifeline should raise ValueError if no lifeline exists."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        with pytest.raises(ValueError, match="lifeline_unavailable"):
            consume_lifeline(team.id, "phone_a_friend")


def test_consume_lifeline_raises_when_zero_remaining(app, db):
    """consume_lifeline should raise ValueError if remaining_uses is 0."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        lifeline = Lifeline(
            team_id=team.id, lifeline_type="phone_a_friend", remaining_uses=0,
        )
        db.session.add(lifeline)
        db.session.commit()
        with pytest.raises(ValueError, match="lifeline_unavailable"):
            consume_lifeline(team.id, "phone_a_friend")


# -----------------------------------------------------------------------
# list_lifelines
# -----------------------------------------------------------------------

def test_list_lifelines_excludes_zero_remaining(app, db):
    """list_lifelines should not include lifelines with 0 remaining uses."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        lifeline = Lifeline(
            team_id=team.id, lifeline_type="phone_a_friend", remaining_uses=0,
        )
        db.session.add(lifeline)
        db.session.commit()
        result = list_lifelines(team.id)
        assert len(result) == 0


def test_list_lifelines_includes_positive_remaining(app, db):
    """list_lifelines should include lifelines with remaining_uses > 0."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "phone_a_friend", uses=2)
        award_lifeline(team.id, "false_flag", uses=1)
        db.session.commit()
        result = list_lifelines(team.id)
        assert len(result) == 2
        types = {ll["lifeline_type"] for ll in result}
        assert "phone_a_friend" in types
        assert "false_flag" in types


def test_list_lifelines_returns_correct_fields(app, db):
    """Each lifeline in the list should have id, lifeline_type, remaining_uses, awarded_for."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        award_lifeline(team.id, "phone_a_friend", awarded_for="test_award")
        db.session.commit()
        result = list_lifelines(team.id)
        assert len(result) == 1
        ll = result[0]
        assert "id" in ll
        assert "lifeline_type" in ll
        assert "remaining_uses" in ll
        assert "awarded_for" in ll
        assert ll["awarded_for"] == "test_award"


# -----------------------------------------------------------------------
# Phone-a-friend route
# -----------------------------------------------------------------------

def test_phone_a_friend_no_lifeline(client, db):
    """Using phone-a-friend without a lifeline should return 400."""
    user = _login(client, db, email="nophone@example.com")
    resp = client.post("/api/game/lifelines/phone-a-friend")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "no_phone_a_friend_lifeline"


def test_phone_a_friend_with_lifeline(client, db):
    """Using phone-a-friend with a lifeline should return a hint."""
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


def test_phone_a_friend_decrements_lifeline(client, db):
    """Using phone-a-friend should decrement the lifeline remaining_uses."""
    user = _login(client, db, email="phone_dec@example.com")
    lifeline = Lifeline(
        team_id=user.team_id,
        lifeline_type="phone_a_friend",
        remaining_uses=2,
    )
    db.session.add(lifeline)
    db.session.commit()
    client.post("/api/game/lifelines/phone-a-friend")
    db.session.refresh(lifeline)
    assert lifeline.remaining_uses == 1


def test_phone_a_friend_returns_hint_with_enemy_proposals(client, db):
    """When enemy proposals exist, phone-a-friend should return intel about one."""
    user = _login(client, db, email="phone_enemy@example.com")
    lifeline = Lifeline(
        team_id=user.team_id,
        lifeline_type="phone_a_friend",
        remaining_uses=1,
    )
    db.session.add(lifeline)

    # Create an enemy proposal for the active round
    round_obj = Round.query.filter_by(status="active").first()
    other_team = next(t for t in Team.query.all() if t.id != user.team_id)
    enemy_user = User(
        display_name="Enemy", email="enemy_for_phone@example.com",
        password_hash=hash_password("p"), team_id=other_team.id,
    )
    db.session.add(enemy_user)
    db.session.flush()
    enemy_proposal = ActionProposal(
        round_id=round_obj.id, team_id=other_team.id,
        proposer_user_id=enemy_user.id, slot=1,
        action_code="CYBER_STRIKE", status="draft",
        target_team_id=user.team_id,
    )
    db.session.add(enemy_proposal)
    db.session.commit()

    resp = client.post("/api/game/lifelines/phone-a-friend")
    assert resp.status_code == 200
    hint = resp.get_json()["hint"]
    assert hint["team_name"] != "N/A"
    assert hint["slot"] > 0


def test_phone_a_friend_no_enemy_proposals(client, db):
    """When no enemy proposals exist, phone-a-friend should return a fallback hint."""
    user = _login(client, db, email="phone_noenemy@example.com")
    lifeline = Lifeline(
        team_id=user.team_id,
        lifeline_type="phone_a_friend",
        remaining_uses=1,
    )
    db.session.add(lifeline)
    db.session.commit()

    resp = client.post("/api/game/lifelines/phone-a-friend")
    assert resp.status_code == 200
    hint = resp.get_json()["hint"]
    assert hint["team_name"] == "N/A"
    assert hint["action_name"] == "No intel available"


# -----------------------------------------------------------------------
# Intel solve
# -----------------------------------------------------------------------

def test_intel_solve_correct(client, db):
    """Solving an intel drop with the correct answer should succeed and grant a lifeline."""
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
    """Solving an intel drop with an incorrect answer should return 400."""
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


def test_intel_solve_already_solved(client, db):
    """Solving an already-solved intel drop should return 400."""
    user = _login(client, db, email="intel_already@example.com")
    solution = "ANSWER"
    sol_hash = hash_password(solution)
    round_obj = Round.query.filter_by(status="active").first()
    intel = IntelDrop(
        round_id=round_obj.id if round_obj else 1,
        team_id=user.team_id,
        puzzle_type="cipher",
        clue="Solved clue",
        reward="false flag lifeline",
        solution_hash=sol_hash,
        solved_by_team_id=user.team_id,
    )
    db.session.add(intel)
    db.session.commit()
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": intel.id,
        "answer": solution,
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "already_solved"


def test_intel_solve_not_found(client, db):
    """Solving a non-existent intel drop should return 404."""
    user = _login(client, db, email="intel_notfound@example.com")
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": 99999,
        "answer": "ANYTHING",
    })
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "intel_not_found"


def test_intel_solve_invalid_payload(client, db):
    """Solving with missing fields should return 400."""
    user = _login(client, db, email="intel_invalid@example.com")
    resp = client.post("/api/game/intel/solve", json={})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_payload"


def test_intel_solve_grants_correct_lifeline_type(client, db):
    """Solving an intel drop with 'false flag lifeline' reward should grant false_flag type."""
    user = _login(client, db, email="intel_fftype@example.com")
    solution = "TESTKEY"
    sol_hash = hash_password(solution)
    round_obj = Round.query.filter_by(status="active").first()
    intel = IntelDrop(
        round_id=round_obj.id if round_obj else 1,
        team_id=user.team_id,
        puzzle_type="stego",
        clue="Steganography puzzle",
        reward="false flag lifeline",
        solution_hash=sol_hash,
    )
    db.session.add(intel)
    db.session.commit()
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": intel.id,
        "answer": solution,
    })
    data = resp.get_json()
    assert data["lifeline"]["lifeline_type"] == "false_flag"


def test_intel_solve_grants_phone_a_friend_type(client, db):
    """Solving with 'phone a friend lifeline' reward should grant phone_a_friend type."""
    user = _login(client, db, email="intel_paftype@example.com")
    solution = "PHONEANSWER"
    sol_hash = hash_password(solution)
    round_obj = Round.query.filter_by(status="active").first()
    intel = IntelDrop(
        round_id=round_obj.id if round_obj else 1,
        team_id=user.team_id,
        puzzle_type="cipher",
        clue="Cipher puzzle",
        reward="phone a friend lifeline",
        solution_hash=sol_hash,
    )
    db.session.add(intel)
    db.session.commit()
    resp = client.post("/api/game/intel/solve", json={
        "intel_id": intel.id,
        "answer": solution,
    })
    data = resp.get_json()
    assert data["lifeline"]["lifeline_type"] == "phone_a_friend"
