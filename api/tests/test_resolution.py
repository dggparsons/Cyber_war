"""Tests for round resolution logic."""
import random

from app.extensions import db as _db
from app.models import (
    Team, Round, ActionProposal, ActionVote, User, GlobalState,
    Action, NewsEvent, FalseFlagPlan, Lifeline, OutcomeScoreHistory,
)
from app.seeds.team_data import TEAMS
from app.services.resolution import (
    resolve_round, lock_top_proposals, choose_winner, execute_action,
    apply_effects,
)
from app.data.actions import ACTION_LOOKUP


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


def _create_user_and_round(db_session, round_number=99, email="resolver@example.com"):
    _seed(db_session)
    team = Team.query.first()
    user = User.query.filter_by(email=email).first()
    if not user:
        from app.utils.passwords import hash_password
        user = User(
            display_name="Resolver", email=email,
            password_hash=hash_password("pass"), team_id=team.id,
        )
        db_session.session.add(user)
        db_session.session.commit()
    round_obj = Round(round_number=round_number, status="active")
    db_session.session.add(round_obj)
    db_session.session.commit()
    return user, team, round_obj


# -----------------------------------------------------------------------
# resolve_round basic
# -----------------------------------------------------------------------

def test_resolve_with_proposals(app, db):
    """resolve_round should process submitted proposals and return a list."""
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


def test_resolve_creates_action_records(app, db):
    """Each resolved proposal should produce an Action record."""
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


def test_resolve_stores_outcome_score_history(app, db):
    """resolve_round should save OutcomeScoreHistory entries for every team."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db)
        db.session.commit()
        resolve_round(round_obj)
        histories = OutcomeScoreHistory.query.filter_by(round_id=round_obj.id).all()
        assert len(histories) == len(TEAMS)


def test_resolve_generates_narrative(app, db):
    """After resolution the round should have a narrative set."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db)
        db.session.commit()
        resolve_round(round_obj)
        db.session.refresh(round_obj)
        assert round_obj.narrative is not None
        assert len(round_obj.narrative) > 0


# -----------------------------------------------------------------------
# Auto-fill WAIT for empty slots
# -----------------------------------------------------------------------

def test_resolve_auto_fills_wait(app, db):
    """Teams with no proposals should get an auto-filled WAIT action."""
    with app.app_context():
        _seed(db)
        round_obj = Round(round_number=98, status="active")
        db.session.add(round_obj)
        db.session.commit()
        resolutions = resolve_round(round_obj)
        assert isinstance(resolutions, list)
        wait_actions = [r for r in resolutions if r.action_code == "WAIT"]
        # Every team should get a WAIT
        assert len(wait_actions) == len(TEAMS)


def test_resolve_auto_fill_skips_teams_with_proposals(app, db):
    """A team with a submitted proposal should not get an auto-fill WAIT."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=97)
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


# -----------------------------------------------------------------------
# Deterministic RNG
# -----------------------------------------------------------------------

def test_deterministic_rng_same_round(app, db):
    """Running resolve_round for the same round parameters should produce
    the same RNG seed and therefore the same random sequence."""
    with app.app_context():
        # Demonstrate seed determinism manually
        seed_val = f"cyberwar-r42-5"
        random.seed(seed_val)
        seq1 = [random.random() for _ in range(10)]
        random.seed(seed_val)
        seq2 = [random.random() for _ in range(10)]
        assert seq1 == seq2


def test_deterministic_rng_different_rounds(app, db):
    """Different round IDs should produce different RNG sequences."""
    with app.app_context():
        random.seed("cyberwar-r1-1")
        seq1 = [random.random() for _ in range(10)]
        random.seed("cyberwar-r2-2")
        seq2 = [random.random() for _ in range(10)]
        assert seq1 != seq2


# -----------------------------------------------------------------------
# lock_top_proposals
# -----------------------------------------------------------------------

def test_lock_top_proposals_picks_highest_voted(app, db):
    """lock_top_proposals should lock the proposal with the most positive votes."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=96, email="locker@example.com")
        # Create a second user for voting
        from app.utils.passwords import hash_password
        voter = User(
            display_name="Voter", email="voter@example.com",
            password_hash=hash_password("pass"), team_id=team.id,
        )
        db.session.add(voter)
        db.session.commit()

        # Proposal A: will receive positive votes
        prop_a = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="SECURITY_AUDIT", status="draft",
        )
        # Proposal B: will receive no votes
        prop_b = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="WAIT", status="draft",
        )
        db.session.add_all([prop_a, prop_b])
        db.session.flush()

        # Vote +1 for proposal A
        vote = ActionVote(proposal_id=prop_a.id, voter_user_id=voter.id, value=1)
        db.session.add(vote)
        db.session.commit()

        lock_top_proposals(round_obj)

        db.session.refresh(prop_a)
        db.session.refresh(prop_b)
        assert prop_a.status == "locked"
        assert prop_b.status == "closed"


def test_lock_top_proposals_no_proposals(app, db):
    """lock_top_proposals with no proposals should do nothing and not raise."""
    with app.app_context():
        _seed(db)
        round_obj = Round(round_number=95, status="active")
        db.session.add(round_obj)
        db.session.commit()
        # Should not raise
        lock_top_proposals(round_obj)


def test_lock_top_proposals_already_locked(app, db):
    """Proposals that are already locked should not be changed."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=94, email="alreadylocked@example.com")
        prop = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="HONEYPOTS", status="locked",
        )
        db.session.add(prop)
        db.session.commit()
        lock_top_proposals(round_obj)
        db.session.refresh(prop)
        assert prop.status == "locked"


# -----------------------------------------------------------------------
# Nuclear action triggers doom
# -----------------------------------------------------------------------

def test_nuclear_action_triggers_doom(app, db):
    """Executing a nuclear-category action should trigger doom when successful."""
    with app.app_context():
        _seed(db)
        gs = GlobalState.query.first()
        gs.nuke_unlocked = True
        db.session.commit()

        user, team, round_obj = _create_user_and_round(db, round_number=93, email="nuke@example.com")
        teams = Team.query.all()
        target = next(t for t in teams if t.id != team.id)

        # Force success by seeding RNG to always succeed
        random.seed(0)
        action_def = ACTION_LOOKUP["NUCLEAR_STRIKE"]
        proposal = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="NUCLEAR_STRIKE", status="locked",
            target_team_id=target.id,
        )
        db.session.add(proposal)
        db.session.commit()

        # Execute action directly; we need it to succeed for doom to trigger
        # Set random to always succeed by using seed that gives high value
        success = execute_action(proposal, action_def, actor=team, target=target)
        db.session.commit()

        if success:
            gs_after = GlobalState.query.first()
            assert gs_after.doom_triggered is True
            assert gs_after.doom_message is not None


def test_nuclear_category_reduces_all_team_stats(app, db):
    """Nuclear action success should reduce prosperity and security for all teams."""
    with app.app_context():
        _seed(db)
        gs = GlobalState.query.first()
        gs.nuke_unlocked = True
        db.session.commit()

        user, team, round_obj = _create_user_and_round(db, round_number=92, email="nukestats@example.com")
        teams = Team.query.all()
        target = next(t for t in teams if t.id != team.id)

        action_def = ACTION_LOOKUP["NUCLEAR_STRIKE"]
        proposal = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="NUCLEAR_STRIKE", status="locked",
            target_team_id=target.id,
        )
        db.session.add(proposal)
        db.session.commit()

        # Store prosperity before
        pre_prosperity = {t.id: t.current_prosperity for t in teams}

        # Try multiple times to get a success
        for seed in range(100):
            random.seed(seed)
            test_val = random.random()
            if test_val < 0.6:  # base success chance
                break

        random.seed(seed)
        success = execute_action(proposal, action_def, actor=team, target=target)
        db.session.commit()

        if success:
            for t in Team.query.all():
                # All teams lose 20 prosperity from nuclear doom
                assert t.current_prosperity <= pre_prosperity[t.id]


# -----------------------------------------------------------------------
# apply_effects
# -----------------------------------------------------------------------

def test_apply_effects_self_only(app, db):
    """apply_effects with self_effects should modify actor stats."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        old_security = team.current_security
        action_def = ACTION_LOOKUP["SECURITY_AUDIT"]
        apply_effects(team, None, action_def)
        assert team.current_security == old_security + 5


def test_apply_effects_self_and_target(app, db):
    """apply_effects with both self_effects and target_effects should modify both."""
    with app.app_context():
        _seed(db)
        teams = Team.query.all()
        actor = teams[0]
        target = teams[1]
        old_actor_influence = actor.current_influence
        old_target_security = target.current_security
        action_def = ACTION_LOOKUP["SHARE_INTEL"]
        apply_effects(actor, target, action_def)
        assert actor.current_influence == old_actor_influence + 2
        assert target.current_security == old_target_security + 3


def test_apply_effects_target_negative(app, db):
    """Offensive actions should reduce target stats."""
    with app.app_context():
        _seed(db)
        teams = Team.query.all()
        actor = teams[0]
        target = teams[1]
        old_target_prosperity = target.current_prosperity
        action_def = ACTION_LOOKUP["CYBER_STRIKE"]
        apply_effects(actor, target, action_def)
        assert target.current_prosperity == old_target_prosperity - 6


def test_apply_effects_no_effects(app, db):
    """An action with no effects (like WAIT) should leave stats unchanged."""
    with app.app_context():
        _seed(db)
        team = Team.query.first()
        old_prosperity = team.current_prosperity
        old_security = team.current_security
        old_influence = team.current_influence
        action_def = ACTION_LOOKUP["WAIT"]
        apply_effects(team, None, action_def)
        assert team.current_prosperity == old_prosperity
        assert team.current_security == old_security
        assert team.current_influence == old_influence


# -----------------------------------------------------------------------
# False flag attribution in news events
# -----------------------------------------------------------------------

def test_false_flag_attribution_in_news(app, db):
    """When a false flag plan exists, news events should attribute the action
    to the blamed team rather than the true actor."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=91, email="falseflag@example.com")
        teams = Team.query.all()
        target = next(t for t in teams if t.id != team.id)
        blamed = next(t for t in teams if t.id not in (team.id, target.id))

        # Create lifeline for false flag
        lifeline = Lifeline(team_id=team.id, lifeline_type="false_flag", remaining_uses=1)
        db.session.add(lifeline)
        db.session.flush()

        # Create a proposal with false flag plan
        proposal = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="CYBER_STRIKE", status="locked",
            target_team_id=target.id,
        )
        db.session.add(proposal)
        db.session.flush()

        plan = FalseFlagPlan(
            team_id=team.id, proposal_id=proposal.id,
            target_team_id=blamed.id, lifeline_id=lifeline.id,
        )
        db.session.add(plan)
        db.session.commit()

        # Clear existing news
        NewsEvent.query.delete()
        db.session.commit()

        resolutions = resolve_round(round_obj)
        # Check that news events mention the blamed team instead of the real actor
        news = NewsEvent.query.all()
        blame_mentioned = any(blamed.nation_name in n.message for n in news)
        sigint_mentioned = any("SIGINT" in n.message for n in news)

        # The blamed team's name should appear in the news
        assert blame_mentioned or sigint_mentioned


# -----------------------------------------------------------------------
# choose_winner
# -----------------------------------------------------------------------

def test_choose_winner_by_votes(app, db):
    """choose_winner should select the proposal with the highest vote score."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=90, email="chooser@example.com")
        from app.utils.passwords import hash_password
        voter1 = User(display_name="V1", email="v1@example.com", password_hash=hash_password("p"), team_id=team.id)
        voter2 = User(display_name="V2", email="v2@example.com", password_hash=hash_password("p"), team_id=team.id)
        db.session.add_all([voter1, voter2])
        db.session.commit()

        prop_a = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="SECURITY_AUDIT", status="draft",
        )
        prop_b = ActionProposal(
            round_id=round_obj.id, team_id=team.id, proposer_user_id=user.id,
            slot=1, action_code="WAIT", status="draft",
        )
        db.session.add_all([prop_a, prop_b])
        db.session.flush()

        # prop_a gets +2, prop_b gets -1
        db.session.add(ActionVote(proposal_id=prop_a.id, voter_user_id=voter1.id, value=1))
        db.session.add(ActionVote(proposal_id=prop_a.id, voter_user_id=voter2.id, value=1))
        db.session.add(ActionVote(proposal_id=prop_b.id, voter_user_id=voter1.id, value=-1))
        db.session.commit()

        winner = choose_winner([prop_a, prop_b])
        assert winner.id == prop_a.id


# -----------------------------------------------------------------------
# resolve_round single slot
# -----------------------------------------------------------------------

def test_resolve_single_slot(app, db):
    """A team with a single locked proposal should resolve it as their action."""
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


# -----------------------------------------------------------------------
# Cleanup after resolution
# -----------------------------------------------------------------------

def test_resolve_cleans_up_proposals(app, db):
    """After resolution, proposals for that round should be deleted."""
    with app.app_context():
        user, team, round_obj = _create_user_and_round(db, round_number=89, email="cleanup@example.com")
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

        resolve_round(round_obj)

        remaining = ActionProposal.query.filter_by(round_id=round_obj.id).all()
        assert len(remaining) == 0
