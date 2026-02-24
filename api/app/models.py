"""SQLAlchemy models for Phase 1 PoC."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Team(db.Model, TimestampMixin):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    nation_name = db.Column(db.String(64), nullable=False, unique=True)
    nation_code = db.Column(db.String(16), nullable=False, unique=True)
    team_type = db.Column(db.String(16), default="nation")
    seat_cap = db.Column(db.Integer, default=8)
    baseline_prosperity = db.Column(db.Integer, default=100)
    baseline_security = db.Column(db.Integer, default=50)
    baseline_influence = db.Column(db.Integer, default=50)
    current_prosperity = db.Column(db.Integer, default=0)
    current_security = db.Column(db.Integer, default=0)
    current_influence = db.Column(db.Integer, default=0)
    current_escalation = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)

    users = db.relationship("User", back_populates="team")


class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), default="player")
    is_captain = db.Column(db.Boolean, default=False)
    session_token = db.Column(db.String(64))

    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    team = db.relationship("Team", back_populates="users")


class Round(db.Model, TimestampMixin):
    __tablename__ = "rounds"

    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default="pending")
    narrative = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)


class ActionProposal(db.Model, TimestampMixin):
    __tablename__ = "action_proposals"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    proposer_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    action_code = db.Column(db.String(64), nullable=False)
    target_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    rationale = db.Column(db.Text)
    status = db.Column(db.String(16), default="draft")
    vetoed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    vetoed_reason = db.Column(db.Text)

    votes = db.relationship("ActionVote", back_populates="proposal", cascade="all, delete-orphan")


class ActionVote(db.Model, TimestampMixin):
    __tablename__ = "action_votes"

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("action_proposals.id"), nullable=False)
    voter_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    value = db.Column(db.Integer, nullable=False)

    proposal = db.relationship("ActionProposal", back_populates="votes")

    __table_args__ = (
        db.UniqueConstraint("proposal_id", "voter_user_id", name="uq_vote_proposal_voter"),
    )


class Action(db.Model, TimestampMixin):
    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    action_code = db.Column(db.String(64), nullable=False)
    target_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    action_slot = db.Column(db.Integer, nullable=False)
    locked_from_proposal_id = db.Column(db.Integer, db.ForeignKey("action_proposals.id"))
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    success = db.Column(db.Boolean)


class Message(db.Model, TimestampMixin):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    content = db.Column(db.Text, nullable=False)
    channel = db.Column(db.String(64), default="team")
    user = db.relationship("User")


class Waitlist(db.Model, TimestampMixin):
    __tablename__ = "waitlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(16), default="waiting")


class Lifeline(db.Model, TimestampMixin):
    __tablename__ = "lifelines"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    lifeline_type = db.Column(db.String(32), nullable=False)
    remaining_uses = db.Column(db.Integer, default=1)
    awarded_for = db.Column(db.String(64))


class IntelDrop(db.Model, TimestampMixin):
    __tablename__ = "intel_drops"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    puzzle_type = db.Column(db.String(32), nullable=False)
    clue = db.Column(db.Text, nullable=False)
    reward = db.Column(db.String(64))
    solution_hash = db.Column(db.String(128), nullable=False)
    solved_by_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    solved_at = db.Column(db.DateTime)


class MegaChallenge(db.Model, TimestampMixin):
    __tablename__ = "mega_challenge"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    reward_tiers = db.Column(db.JSON, nullable=False)
    solution_hash = db.Column(db.String(128), nullable=False)
    winner_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    solved_at = db.Column(db.DateTime)


class MegaChallengeSolve(db.Model, TimestampMixin):
    __tablename__ = "mega_challenge_solves"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("mega_challenge.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    solve_position = db.Column(db.Integer, nullable=False)
    reward_influence = db.Column(db.Integer, nullable=False)


class DiplomacyChannel(db.Model, TimestampMixin):
    __tablename__ = "diplomacy_channels"

    id = db.Column(db.Integer, primary_key=True)
    team_a_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    status = db.Column(db.String(16), default="open")


class NewsEvent(db.Model, TimestampMixin):
    __tablename__ = "news_events"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)


class CrisisEvent(db.Model, TimestampMixin):
    __tablename__ = "crisis_events"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    effect_text = db.Column(db.Text, nullable=False)
    payload = db.Column(db.JSON)
    applied_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class GlobalState(db.Model, TimestampMixin):
    __tablename__ = "global_state"

    id = db.Column(db.Integer, primary_key=True)
    nuke_unlocked = db.Column(db.Boolean, default=False)
    doom_triggered = db.Column(db.Boolean, default=False)
    doom_message = db.Column(db.Text)
    active_crisis_payload = db.Column(db.JSON)
    active_crisis_code = db.Column(db.String(64))
    last_crisis_at = db.Column(db.DateTime)
    escalation_thresholds = db.Column(db.JSON, default=list)


class Alliance(db.Model, TimestampMixin):
    __tablename__ = "alliances"

    id = db.Column(db.Integer, primary_key=True)
    team_a_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    status = db.Column(db.String(16), default="active")

    __table_args__ = (
        db.UniqueConstraint("team_a_id", "team_b_id", name="uq_alliance_pair"),
    )


class FalseFlagPlan(db.Model, TimestampMixin):
    __tablename__ = "false_flag_plans"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    proposal_id = db.Column(db.Integer, db.ForeignKey("action_proposals.id"), nullable=False)
    target_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    lifeline_id = db.Column(db.Integer, db.ForeignKey("lifelines.id"), nullable=False)


class OutcomeScoreHistory(db.Model, TimestampMixin):
    __tablename__ = "outcome_score_history"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    outcome_score = db.Column(db.Integer, nullable=False)


class AiRun(db.Model, TimestampMixin):
    __tablename__ = "ai_runs"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(64), nullable=False)
    scenario = db.Column(db.String(64), default="conference_default")


class AiRoundScore(db.Model, TimestampMixin):
    __tablename__ = "ai_round_scores"

    id = db.Column(db.Integer, primary_key=True)
    ai_run_id = db.Column(db.Integer, db.ForeignKey("ai_runs.id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    escalation_score = db.Column(db.Integer, nullable=False)
    outcome_score = db.Column(db.Integer, nullable=False)
