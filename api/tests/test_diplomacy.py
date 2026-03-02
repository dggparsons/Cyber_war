"""Tests for diplomacy endpoints."""
from app.extensions import db as _db
from app.models import Team, Round, User, DiplomacyChannel, Message
from app.seeds.team_data import TEAMS


def _seed(db_session):
    if not Team.query.first():
        for td in TEAMS:
            db_session.session.add(Team(**td))
        db_session.session.add(Round(round_number=1, status="pending"))
        db_session.session.commit()


def _login(client, db_session, email="diplo@example.com", team_index=0):
    """Register and log in a user, assigning them to the team at team_index."""
    _seed(db_session)
    reg = client.post("/api/auth/register", json={
        "display_name": "DiploTester",
        "email": email,
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={"email": email, "password": password})
    user = User.query.filter_by(email=email).first()
    if not user.team_id:
        team = Team.query.all()[team_index]
        user.team_id = team.id
        db_session.session.commit()
    return user


def _login_two_users(client, db_session):
    """Create two users on different teams and return both.
    The first user remains logged in."""
    _seed(db_session)
    teams = Team.query.all()

    # Register user A on team 0
    reg_a = client.post("/api/auth/register", json={
        "display_name": "DiploUserA",
        "email": "diplo_a@example.com",
    })
    pw_a = reg_a.get_json()["password"]
    user_a = User.query.filter_by(email="diplo_a@example.com").first()
    user_a.team_id = teams[0].id

    # Register user B on team 1
    reg_b = client.post("/api/auth/register", json={
        "display_name": "DiploUserB",
        "email": "diplo_b@example.com",
    })
    pw_b = reg_b.get_json()["password"]
    user_b = User.query.filter_by(email="diplo_b@example.com").first()
    user_b.team_id = teams[1].id

    db_session.session.commit()

    # Log in user A
    client.post("/api/auth/login", json={"email": "diplo_a@example.com", "password": pw_a})
    return user_a, user_b, pw_a, pw_b


# -----------------------------------------------------------------------
# List channels
# -----------------------------------------------------------------------

def test_list_channels_empty(client, db):
    """A fresh user should see an empty diplomacy channel list."""
    _login(client, db, email="diplolist@example.com")
    resp = client.get("/api/diplomacy/")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
    assert len(resp.get_json()) == 0


# -----------------------------------------------------------------------
# Start channel creates pending channel
# -----------------------------------------------------------------------

def test_start_channel(client, db):
    """Starting a diplomacy channel should create it in pending status."""
    user = _login(client, db, email="diplostart@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    resp = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert "channel_id" in data
    assert data["status"] == "pending"


def test_start_channel_creates_db_record(client, db):
    """The DiplomacyChannel record should exist in the DB after start."""
    user = _login(client, db, email="diplo_dbcheck@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    resp = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    channel_id = resp.get_json()["channel_id"]
    channel = DiplomacyChannel.query.get(channel_id)
    assert channel is not None
    assert channel.status == "pending"
    pair = sorted([user.team_id, other.id])
    assert channel.team_a_id == pair[0]
    assert channel.team_b_id == pair[1]
    assert channel.initiated_by == user.team_id


def test_start_channel_idempotent(client, db):
    """Starting a channel to the same team twice should return the existing channel."""
    user = _login(client, db, email="diplo_idemp@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    resp1 = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    resp2 = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    assert resp1.get_json()["channel_id"] == resp2.get_json()["channel_id"]


# -----------------------------------------------------------------------
# Accept channel changes status
# -----------------------------------------------------------------------

def test_accept_channel(client, db):
    """The non-initiating team accepting should change status to 'accepted'."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    teams = Team.query.all()
    # User A starts a channel to user B's team
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    # Logout user A, then login as user B
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    resp = client.post("/api/diplomacy/respond", json={
        "channel_id": channel_id,
        "action": "accept",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "accepted"

    channel = db.session.get(DiplomacyChannel, channel_id)
    assert channel.status == "accepted"


# -----------------------------------------------------------------------
# Decline channel changes status
# -----------------------------------------------------------------------

def test_decline_channel(client, db):
    """The non-initiating team declining should change status to 'declined'."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    # Logout user A, then login as user B
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    resp = client.post("/api/diplomacy/respond", json={
        "channel_id": channel_id,
        "action": "decline",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "declined"


def test_initiator_cannot_respond(client, db):
    """The initiating team should not be able to accept/decline their own request."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    # User A (initiator) tries to accept
    resp = client.post("/api/diplomacy/respond", json={
        "channel_id": channel_id,
        "action": "accept",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "initiator_cannot_respond"


def test_respond_invalid_action(client, db):
    """Responding with an invalid action should return 400."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    resp = client.post("/api/diplomacy/respond", json={
        "channel_id": channel_id,
        "action": "invalid_action",
    })
    assert resp.status_code == 400


def test_respond_already_accepted(client, db):
    """Responding to an already-accepted channel should return 400."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "accept"})
    # Try to respond again
    resp = client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "decline"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "channel_not_pending"


# -----------------------------------------------------------------------
# Send message in accepted channel
# -----------------------------------------------------------------------

def test_send_message_in_accepted_channel(client, db):
    """Sending a message in an accepted channel should succeed."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    # Accept as user B
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "accept"})

    # Send message as user B
    resp = client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "Hello from team B!",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"] == "Hello from team B!"
    assert data["channel_id"] == channel_id


def test_send_message_creates_record(client, db):
    """A sent message should create a Message record in the database."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "accept"})
    client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "Test message content",
    })

    msg = Message.query.filter_by(channel=f"diplomacy:{channel_id}").first()
    assert msg is not None
    assert msg.content == "Test message content"


def test_messages_visible_in_channel_list(client, db):
    """Messages should appear in the channel list for accepted channels."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "accept"})
    client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "Visible message",
    })

    resp = client.get("/api/diplomacy/")
    channels = resp.get_json()
    ch = next(c for c in channels if c["channel_id"] == channel_id)
    assert len(ch["messages"]) >= 1
    assert any(m["content"] == "Visible message" for m in ch["messages"])


# -----------------------------------------------------------------------
# Cannot send message in pending channel
# -----------------------------------------------------------------------

def test_cannot_send_message_in_pending_channel(client, db):
    """Sending a message in a pending (not yet accepted) channel should fail."""
    user = _login(client, db, email="diplosend_pending@example.com")
    teams = Team.query.all()
    other = next(t for t in teams if t.id != user.team_id)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": other.id})
    channel_id = resp_start.get_json()["channel_id"]

    resp = client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "Should not work",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "channel_not_accepted"


def test_cannot_send_empty_message(client, db):
    """Sending an empty message should be rejected."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "accept"})

    resp = client.post("/api/diplomacy/send", json={
        "channel_id": channel_id,
        "content": "",
    })
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "content_required"


# -----------------------------------------------------------------------
# Cannot self-target
# -----------------------------------------------------------------------

def test_self_diplomacy_rejected(client, db):
    """Starting a diplomacy channel with your own team should fail."""
    user = _login(client, db, email="diploself@example.com")
    resp = client.post("/api/diplomacy/start", json={"target_team_id": user.team_id})
    assert resp.status_code == 400
    assert "self" in resp.get_json().get("error", "").lower() or resp.status_code == 400


# -----------------------------------------------------------------------
# Channel not found
# -----------------------------------------------------------------------

def test_send_message_invalid_channel(client, db):
    """Sending a message to a non-existent channel should return 404."""
    _login(client, db, email="diplo_invalid_ch@example.com")
    resp = client.post("/api/diplomacy/send", json={
        "channel_id": 99999,
        "content": "Hello",
    })
    assert resp.status_code == 404


def test_respond_invalid_channel(client, db):
    """Responding to a non-existent channel should return 404."""
    _login(client, db, email="diplo_respond_invalid@example.com")
    resp = client.post("/api/diplomacy/respond", json={
        "channel_id": 99999,
        "action": "accept",
    })
    assert resp.status_code == 404


# -----------------------------------------------------------------------
# Declined channel re-open
# -----------------------------------------------------------------------

def test_reopen_declined_channel(client, db):
    """Starting a channel that was previously declined should re-open it as pending."""
    user_a, user_b, pw_a, pw_b = _login_two_users(client, db)
    resp_start = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    channel_id = resp_start.get_json()["channel_id"]

    # Decline as user B
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_b@example.com", "password": pw_b})
    client.post("/api/diplomacy/respond", json={"channel_id": channel_id, "action": "decline"})

    # Re-open as user A
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "diplo_a@example.com", "password": pw_a})
    resp = client.post("/api/diplomacy/start", json={"target_team_id": user_b.team_id})
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert data["status"] == "pending"
    assert data["channel_id"] == channel_id
