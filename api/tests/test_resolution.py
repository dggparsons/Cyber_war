"""Tests for round resolution logic."""
from app.extensions import db as _db
from app.models import Team, Round, ActionProposal, User, GlobalState
from app.seeds.team_data import TEAMS
from app.services.resolution import resolve_round


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.commit()
    gs = GlobalState.query.first()
    if not gs:
        gs = GlobalState(nuke_unlocked=False, doom_triggered=False, escalation_thresholds=[20, 40, 60, 80])
        db_session.session.add(gs)
        db_session.session.commit()


def _create_user_and_round(db_session):
    _seed(db_session)
    team = Team.query.first()
    user = User.query.filter_by(email="resolver@example.com").first()
    if not user:
        from app.utils.passwords import hash_password
        user = User(display_name="Resolver", email="resolver@example.com", password_hash=hash_password("pass"), team_id=team.id)
        db_session.session.add(user)
        db_session.session.commit()
    round_obj = Round(round_number=99, status="active")
    db_session.session.add(round_obj)
    db_session.session.commit()
    return user, team, round_obj


def test_resolve_with_proposals(app, db):
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db)
        proposal = ActionProposal(
            round_id=round_obj.id,
            team_id=team.id,
            proposer_user_id=user.id,
            slot=1,
            action_code="WAIT",
            status="draft",
        )
        db.session.add(proposal)
        db.session.commit()
        resolutions = resolve_round(round_obj)
        assert isinstance(resolutions, list)


def test_resolve_auto_fills_wait(app, db):
    with app.app_context():
        _seed(db)
        round_obj = Round(round_number=98, status="active")
        db.session.add(round_obj)
        db.session.commit()
        # No proposals for any team — all should get WAIT
        resolutions = resolve_round(round_obj)
        assert isinstance(resolutions, list)
        wait_actions = [r for r in resolutions if r.action_code == "WAIT"]
        assert len(wait_actions) > 0


def test_resolve_single_slot(app, db):
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db)
        proposal = ActionProposal(
            round_id=round_obj.id,
            team_id=team.id,
            proposer_user_id=user.id,
            slot=1,
            action_code="SECURITY_AUDIT",
            status="locked",
        )
        db.session.add(proposal)
        db.session.commit()
        resolutions = resolve_round(round_obj)
        team_actions = [r for r in resolutions if r.team_id == team.id]
        assert len(team_actions) == 1
        assert team_actions[0].action_code == "SECURITY_AUDIT"
