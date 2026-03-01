#!/usr/bin/env python3
"""
End-to-end smoke test for Cyber War Room.

Simulates 30 players (3 per team, 10 teams) against a running Docker
instance.  Uses the /join endpoint to register+login in one call and
auto-assign to specific teams via join codes.

Requirements
------------
    pip install requests python-socketio[client] websocket-client

Usage
-----
    1. docker compose up --build
    2. python scripts/e2e_smoke.py [--base-url http://localhost:5050]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from typing import Any

import requests

try:
    import socketio as sio_lib

    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:5050"
GM_EMAIL = "admin@warroom.local"
GM_PASSWORD = "ChangeMe123!"

# 10 join codes × 3 players = 30 players (excludes UN)
JOIN_CODES = [
    "NEXUS-OPS", "IRON-VANGUARD", "GHOST-SHELL", "CORAL-TIDE",
    "FROST-WATCH", "SHADOW-VEIL", "DAWN-SHIELD", "NEON-GRID",
    "SKY-ARC", "LOTUS-VAULT",
]
PLAYERS_PER_TEAM = 3
BATCH_SIZE = 10  # /join allows 10/minute from one IP

results: list[tuple[str, str, str]] = []
audit_notes: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ok(name: str, condition: bool, detail: str = "") -> bool:
    tag = "PASS" if condition else "FAIL"
    results.append((name, tag, detail))
    sym = "\u2713" if condition else "\u2717"
    print(f"  [{sym}] {name}" + (f"  -- {detail}" if detail else ""))
    return condition


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


class Player:
    """Thin wrapper around a requests.Session impersonating one user."""

    def __init__(self, name: str, join_code: str | None = None):
        self.name = name
        self.join_code = join_code
        self.http = requests.Session()
        self.password: str | None = None
        self.email: str | None = None
        self.user_id: int | None = None
        self.team_id: int | None = None
        self.team_name: str | None = None
        self.role: str | None = None
        self.is_captain: bool = False
        self.session_token: str | None = None

    def join(self) -> bool:
        """Register + login in one call via /join."""
        r = self.http.post(
            f"{BASE_URL}/api/auth/join",
            json={"display_name": self.name, "join_code": self.join_code},
        )
        if r.status_code == 200:
            d = r.json()
            self.password = d["password"]
            self.user_id = d["user"]["id"]
            self.email = d["user"]["email"]
            self.team_id = d["user"]["team_id"]
            return True
        return False

    def login(self) -> bool:
        r = self.http.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": self.email, "password": self.password},
        )
        if r.status_code == 200:
            d = r.json()
            self.user_id = d["user"]["id"]
            self.team_id = d["user"].get("team_id")
            self.role = d["user"].get("role")
            self.is_captain = d["user"].get("is_captain", False)
            self.session_token = d.get("session_token")
            if "team" in d:
                self.team_name = d["team"].get("nation_name")
            return True
        return False

    def get(self, path: str, **kw: Any) -> requests.Response:
        return self.http.get(f"{BASE_URL}{path}", **kw)

    def post(self, path: str, **kw: Any) -> requests.Response:
        return self.http.post(f"{BASE_URL}{path}", **kw)


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def phase_health():
    section("Phase 0 · Health Check")
    try:
        r = requests.get(f"{BASE_URL}/api/health/", timeout=5)
        ok("Health endpoint reachable", r.status_code == 200, f"status={r.status_code}")
    except Exception as exc:
        ok("Health endpoint reachable", False, str(exc))
        print("\n  *** Cannot reach the server.  Is Docker running? ***\n")
        sys.exit(1)


def phase_gm_login(gm: Player):
    section("Phase 1 · GM Login")
    gm.email = GM_EMAIL
    gm.password = GM_PASSWORD
    gm.name = "Game Master"
    logged_in = gm.login()
    ok("GM login", logged_in, f"role={gm.role}")
    if not logged_in:
        print("  *** GM login failed.  Check GM_USERNAME / GM_PASSWORD in .env.docker ***")
        sys.exit(1)


def phase_join_players(players: list[Player]) -> dict[int | None, list[Player]]:
    """Register + login all players via /join, batched to respect rate limits."""
    section("Phase 2 · Join 30 Players (3 per team)")
    success = 0
    total = len(players)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = players[batch_start : batch_start + BATCH_SIZE]
        if batch_start > 0:
            wait = 62
            print(f"    ... rate-limit cooldown ({wait}s) ...")
            time.sleep(wait)
        for p in batch:
            if p.join():
                success += 1
            else:
                # Try to get error detail
                r = p.http.post(
                    f"{BASE_URL}/api/auth/join",
                    json={"display_name": p.name, "join_code": p.join_code},
                )
                ok(f"Join {p.name} ({p.join_code})", False, r.text[:100])

    ok(f"Joined {success}/{total} players", success == total)

    # Group by team
    teams: dict[int | None, list[Player]] = defaultdict(list)
    for p in players:
        teams[p.team_id].append(p)

    # Show distribution
    for tid, members in sorted(teams.items(), key=lambda x: x[0] or 0):
        if tid is None:
            continue
        names = ", ".join(m.name for m in members)
        print(f"    Team {tid}: {len(members)} players ({names})")

    # Fetch team names via game state
    for tid, members in teams.items():
        if tid is None:
            continue
        r = members[0].get("/api/game/state")
        if r.status_code == 200:
            d = r.json()
            tn = d.get("team", {}).get("nation_name", "?")
            for m in members:
                m.team_name = tn
            print(f"    Team {tid} = {tn}")

    return teams


def phase_gm_reset_and_start(gm: Player):
    section("Phase 3 · GM Resets + Starts Round")
    r = gm.post("/api/admin/rounds/reset")
    ok("Reset game", r.status_code == 200, r.text[:80])
    r = gm.post("/api/admin/rounds/start")
    ok("Start round 1", r.status_code == 200, r.text[:80])


def phase_game_state(teams: dict[int | None, list[Player]]):
    section("Phase 4 · Players Fetch Game State")
    sampled = []
    for tid, members in teams.items():
        if tid is None:
            continue
        sampled.append(members[0])
        if len(sampled) >= 5:
            break

    for p in sampled:
        r = p.get("/api/game/state")
        d = r.json() if r.status_code == 200 else {}
        has_team = "team" in d
        has_round = "round" in d
        ok(
            f"State for {p.name} (team {p.team_id})",
            r.status_code == 200 and has_team and has_round,
            f"roster={len(d.get('roster', []))} advisors={len(d.get('advisors', []))}",
        )

    # Verify actions list
    r = sampled[0].get("/api/game/actions")
    n_actions = len(r.json()) if r.status_code == 200 else 0
    ok("Actions catalog loads", r.status_code == 200 and n_actions > 10, f"{n_actions} actions")


def phase_proposals(teams: dict[int | None, list[Player]]):
    section("Phase 5 · Submit Proposals + Vote")
    proposal_ids: dict[int, int] = {}  # team_id -> proposal_id
    nation_tids = [t for t in teams if t is not None]

    for tid in nation_tids:
        members = teams[tid]
        proposer = members[0]
        other_tids = [t for t in nation_tids if t != tid]
        target = random.choice(other_tids) if other_tids else None

        r = proposer.post(
            "/api/game/proposals",
            json={"action_code": "CYBER_ESPIONAGE", "slot": 1, "target_team_id": target},
        )
        created = r.status_code == 201
        if created:
            proposal_ids[tid] = r.json()["id"]
        ok(f"Proposal by {proposer.team_name or tid}", created, r.text[:100])

    # Self-target guard
    if nation_tids:
        first_tid = nation_tids[0]
        p = teams[first_tid][0]
        r = p.post(
            "/api/game/proposals",
            json={"action_code": "CYBER_ESPIONAGE", "slot": 1, "target_team_id": first_tid},
        )
        ok("Self-target rejected", r.status_code == 400, r.text[:80])

    # Voting
    section("Phase 5b · Voting")
    votes_cast = 0
    for tid, pid in proposal_ids.items():
        for voter in teams.get(tid, []):
            r = voter.post("/api/game/votes", json={"proposal_id": pid, "value": 1})
            if r.status_code == 200:
                votes_cast += 1
            else:
                ok(f"Vote by {voter.name}", False, r.text[:80])
    ok(f"Votes cast", votes_cast > 0, f"{votes_cast} total")

    return proposal_ids


def phase_diplomacy(teams: dict[int | None, list[Player]]):
    section("Phase 6 · Diplomacy")
    nation_tids = [t for t in teams if t is not None]
    if len(nation_tids) < 2:
        ok("Diplomacy (need >=2 teams)", False, "not enough teams")
        return

    team_a_id, team_b_id = nation_tids[0], nation_tids[1]
    player_a = teams[team_a_id][0]
    player_b = teams[team_b_id][0]

    # Self-diplomacy guard
    r = player_a.post("/api/diplomacy/start", json={"target_team_id": team_a_id})
    ok("Self-diplomacy rejected", r.status_code == 400, r.text[:80])

    # Open channel
    r = player_a.post("/api/diplomacy/start", json={"target_team_id": team_b_id})
    opened = r.status_code in (200, 201)
    ok("Open diplomacy channel", opened, r.text[:100])
    if not opened:
        return
    channel_id = r.json()["channel_id"]

    # Player A sends message
    r = player_a.post(
        "/api/diplomacy/send",
        json={"channel_id": channel_id, "content": "Greetings from Team A"},
    )
    ok("Player A sends diplo message", r.status_code == 200)

    # Player B sends reply
    r = player_b.post(
        "/api/diplomacy/send",
        json={"channel_id": channel_id, "content": "Reply from Team B"},
    )
    ok("Player B sends diplo reply", r.status_code == 200)

    # Player B reads channel — should see both messages
    r = player_b.get("/api/diplomacy/")
    if r.status_code == 200:
        channels = r.json()
        ch = next((c for c in channels if c["channel_id"] == channel_id), None)
        if ch:
            msgs = [m["content"] for m in ch.get("messages", [])]
            ok(
                "Cross-user diplo visibility",
                "Greetings from Team A" in msgs and "Reply from Team B" in msgs,
                f"{len(msgs)} messages",
            )
        else:
            ok("Cross-user diplo visibility", False, "channel not found in list")
    else:
        ok("Cross-user diplo visibility", False, f"status={r.status_code}")

    # Open a second channel between two other teams
    if len(nation_tids) >= 4:
        team_c_id, team_d_id = nation_tids[2], nation_tids[3]
        pc = teams[team_c_id][0]
        r = pc.post("/api/diplomacy/start", json={"target_team_id": team_d_id})
        ok("Second diplomacy channel opens", r.status_code in (200, 201))


def phase_team_chat(teams: dict[int | None, list[Player]]):
    section("Phase 7 · Team Chat (Socket.IO)")
    if not HAS_SOCKETIO:
        ok(
            "Socket.IO chat test",
            False,
            "SKIPPED -- install: pip install python-socketio[client] websocket-client",
        )
        audit_notes.append("Socket.IO client not installed; team chat cross-visibility not tested.")
        return

    # Pick a team with >=2 members
    chat_tid = None
    chat_members: list[Player] = []
    for tid, members in teams.items():
        if tid and len(members) >= 2:
            chat_tid = tid
            chat_members = members[:2]
            break
    if not chat_members:
        ok("Team chat (need >=2 on a team)", False, "no team with 2+ members")
        return

    sender, receiver = chat_members
    received_messages: list[dict] = []

    sender_sio = sio_lib.Client()
    receiver_sio = sio_lib.Client()

    @receiver_sio.on("chat:message", namespace="/team")
    def on_chat_msg(data):
        received_messages.append(data)

    headers_s = {"Cookie": "; ".join(f"{k}={v}" for k, v in sender.http.cookies.items())}
    headers_r = {"Cookie": "; ".join(f"{k}={v}" for k, v in receiver.http.cookies.items())}

    try:
        receiver_sio.connect(
            BASE_URL, namespaces=["/team"], headers=headers_r,
            transports=["websocket"], wait_timeout=5,
        )
        ok("Receiver socket connected", receiver_sio.connected)
    except Exception as exc:
        ok("Receiver socket connected", False, str(exc)[:120])
        audit_notes.append(f"Socket.IO connect failed for receiver: {exc}")
        return

    try:
        sender_sio.connect(
            BASE_URL, namespaces=["/team"], headers=headers_s,
            transports=["websocket"], wait_timeout=5,
        )
        ok("Sender socket connected", sender_sio.connected)
    except Exception as exc:
        ok("Sender socket connected", False, str(exc)[:120])
        receiver_sio.disconnect()
        return

    # Send message
    test_content = f"e2e-chat-{random.randint(1000, 9999)}"
    sender_sio.emit("chat:message", {"content": test_content}, namespace="/team")
    time.sleep(2)

    ok(
        "Receiver sees sender chat",
        any(m.get("content") == test_content for m in received_messages),
        f"got {len(received_messages)} msgs",
    )

    sender_sio.disconnect()
    receiver_sio.disconnect()


def phase_intel(gm: Player, teams: dict[int | None, list[Player]]):
    section("Phase 8 · Intel Drops + Solve")
    target_tid = next((t for t in teams if t is not None), None)
    if not target_tid:
        ok("Intel test (need teams)", False)
        return

    # Get active round
    r = gm.get("/api/admin/rounds")
    rounds = r.json() if r.status_code == 200 else []
    active_round = next((rd for rd in rounds if rd["status"] == "active"), None)
    if not active_round:
        ok("Active round exists for intel", False, "no active round")
        return

    solution = "ESCALATION"
    r = gm.post(
        "/api/admin/intel-drops",
        json={
            "round_id": active_round["id"],
            "team_id": target_tid,
            "puzzle_type": "cipher",
            "clue": "Decrypt: RFPNYNGVBA (ROT13)",
            "solution": solution,
            "reward_type": "phone a friend lifeline",
        },
    )
    intel_created = r.status_code == 201
    ok("GM creates intel drop", intel_created, r.text[:120])
    if not intel_created:
        return
    intel_id = r.json()["id"]

    # Player tries wrong answer
    solver = teams[target_tid][0]
    r = solver.post("/api/game/intel/solve", json={"intel_id": intel_id, "answer": "WRONG"})
    ok("Wrong intel answer rejected", r.status_code == 400)

    # Player tries correct answer
    r = solver.post("/api/game/intel/solve", json={"intel_id": intel_id, "answer": solution})
    if r.status_code == 200:
        ok("Correct intel answer accepted", True, r.text[:120])
    else:
        ok(
            "Correct intel answer accepted",
            False,
            f"status={r.status_code} body={r.text[:120]}",
        )
        audit_notes.append(
            "BUG: Intel solve failed.  If status=400, check that admin intel-drops "
            "endpoint uses werkzeug hash_password (not hashlib.sha256)."
        )


def phase_crisis(gm: Player):
    section("Phase 9 · Crisis Injection")
    r = gm.post("/api/admin/crisis/inject", json={"code": "VOLT_TYPHOON"})
    ok("Inject VOLT_TYPHOON crisis", r.status_code == 200, r.text[:120])


def phase_advance_round(gm: Player):
    section("Phase 10 · GM Advances Round")
    r = gm.post("/api/admin/rounds/advance")
    ok("Advance round", r.status_code == 200, r.text[:120])


def phase_leaderboard(teams: dict[int | None, list[Player]]):
    section("Phase 11 · Leaderboard / News / History")
    p = next(m for tid, ms in teams.items() if tid for m in ms)

    r = p.get("/api/game/leaderboard")
    if r.status_code == 200:
        d = r.json()
        entries = d.get("entries", [])
        ok("Leaderboard returns entries", len(entries) >= 10, f"{len(entries)} entries")
        scores = [e["score"] for e in entries]
        ok("Leaderboard sorted desc", scores == sorted(scores, reverse=True))
    else:
        ok("Leaderboard loads", False, f"status={r.status_code}")

    r = p.get("/api/game/news")
    n_events = len(r.json()) if r.status_code == 200 else 0
    ok("News feed loads", r.status_code == 200, f"{n_events} events")

    r = p.get("/api/game/history")
    ok("Action history loads", r.status_code == 200)


def phase_reveal(gm: Player):
    """Reveal requires doom_triggered or GM role — use GM session."""
    section("Phase 12 · Reveal Data (GM)")
    r = gm.get("/api/reveal/")
    if r.status_code == 200:
        d = r.json()
        ok("Reveal data loads", True, f"keys={list(d.keys())[:6]}")
        ok("Reveal has human_vs_ai", "human_vs_ai" in d)
        ok("Reveal has ai_models", "ai_models" in d)
    else:
        ok("Reveal data loads", False, f"status={r.status_code} body={r.text[:100]}")


def phase_misc_guards(gm: Player, teams: dict[int | None, list[Player]]):
    section("Phase 13 · Auth + Permission Guards")
    player = next(m for tid, ms in teams.items() if tid for m in ms)

    # Unauthenticated access
    anon = requests.Session()
    r = anon.get(f"{BASE_URL}/api/game/state")
    ok("Game state requires auth", r.status_code in (401, 302))

    r = anon.post(f"{BASE_URL}/api/admin/rounds/start")
    ok("Admin requires auth", r.status_code in (401, 302, 403))

    # Non-admin cannot admin
    r = player.post("/api/admin/rounds/start")
    ok("Player cannot access admin", r.status_code == 403, f"status={r.status_code}")

    # Invalid vote value
    r = player.post("/api/game/votes", json={"proposal_id": 1, "value": 99})
    ok("Invalid vote value rejected", r.status_code == 400)

    # Nuclear actions locked by default
    nation_tids = [t for t in teams if t is not None]
    if len(nation_tids) >= 2:
        r = player.post(
            "/api/game/proposals",
            json={"action_code": "NUCLEAR_STRIKE", "slot": 1, "target_team_id": nation_tids[-1]},
        )
        ok("Nuclear actions locked", r.status_code == 400 and "nuclear_locked" in r.text)


def phase_round_2(gm: Player, teams: dict[int | None, list[Player]]):
    """Quick round 2 to verify multi-round flow."""
    section("Phase 14 · Round 2 Quick Cycle")
    r = gm.post("/api/admin/rounds/start")
    started = r.status_code == 200
    ok("Start round 2", started, r.text[:80])
    if not started:
        return

    # A few teams submit different actions
    action_codes = ["SHARE_INTEL", "SECURITY_AUDIT", "HONEYPOTS", "DISINFORMATION", "CYBER_STRIKE"]
    nation_tids = [t for t in teams if t is not None]
    for i, tid in enumerate(nation_tids[:5]):
        members = teams[tid]
        other = random.choice([t for t in nation_tids if t != tid])
        code = action_codes[i % len(action_codes)]
        r = members[0].post(
            "/api/game/proposals",
            json={"action_code": code, "slot": 1, "target_team_id": other},
        )
        # Some actions don't need target — that's fine if it returns 201 or 400
        if r.status_code == 201:
            # Have teammates vote
            pid = r.json()["id"]
            for voter in members[1:]:
                voter.post("/api/game/votes", json={"proposal_id": pid, "value": 1})

    r = gm.post("/api/admin/rounds/advance")
    ok("Advance round 2", r.status_code == 200, r.text[:80])

    # Verify leaderboard updated
    p = teams[nation_tids[0]][0]
    r = p.get("/api/game/leaderboard")
    if r.status_code == 200:
        impact = r.json().get("cyber_impact", [])
        ok("Cyber impact has entries after 2 rounds", len(impact) > 0, f"{len(impact)} entries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global BASE_URL, GM_EMAIL, GM_PASSWORD

    parser = argparse.ArgumentParser(description="Cyber War Room E2E smoke test")
    parser.add_argument("--base-url", default="http://localhost:5050")
    parser.add_argument("--gm-email", default=GM_EMAIL)
    parser.add_argument("--gm-password", default=GM_PASSWORD)
    args = parser.parse_args()

    BASE_URL = args.base_url.rstrip("/")
    GM_EMAIL = args.gm_email
    GM_PASSWORD = args.gm_password

    print(f"\nCyber War Room  E2E Smoke Test")
    print(f"Target: {BASE_URL}")
    print(f"GM: {GM_EMAIL}")
    print(f"Players: {len(JOIN_CODES) * PLAYERS_PER_TEAM} ({PLAYERS_PER_TEAM}/team)")
    print(f"Note: rate-limit pauses between batches (~2 min total)\n")

    # Build player list: 3 per join code
    players: list[Player] = []
    for code in JOIN_CODES:
        for i in range(1, PLAYERS_PER_TEAM + 1):
            tag = code.split("-")[0].lower()
            players.append(Player(f"{tag}_{i}", join_code=code))

    # ── Phase 0 ──
    phase_health()

    # ── Phase 1 — GM ──
    gm = Player("Game Master")
    phase_gm_login(gm)

    # ── Phase 2 — Join players ──
    teams = phase_join_players(players)

    # ── Phase 3 — Reset + start round ──
    phase_gm_reset_and_start(gm)

    # ── Phase 4 — Game state ──
    phase_game_state(teams)

    # ── Phase 5 — Proposals + Votes ──
    phase_proposals(teams)

    # ── Phase 6 — Diplomacy ──
    phase_diplomacy(teams)

    # ── Phase 7 — Team chat ──
    phase_team_chat(teams)

    # ── Phase 8 — Intel ──
    phase_intel(gm, teams)

    # ── Phase 9 — Crisis ──
    phase_crisis(gm)

    # ── Phase 10 — Advance round ──
    phase_advance_round(gm)

    # ── Phase 11 — Leaderboard / News / History ──
    phase_leaderboard(teams)

    # ── Phase 12 — Reveal (GM only) ──
    phase_reveal(gm)

    # ── Phase 13 — Auth guards ──
    phase_misc_guards(gm, teams)

    # ── Phase 14 — Round 2 cycle ──
    phase_round_2(gm, teams)

    # ── Summary ──
    section("SUMMARY")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    total = len(results)
    print(f"\n  {passed}/{total} passed,  {failed} failed\n")

    if audit_notes:
        print("  AUDIT NOTES:")
        for i, note in enumerate(audit_notes, 1):
            print(f"    {i}. {note}\n")

    if failed:
        print("  FAILED CHECKS:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"    - {name}" + (f"  ({detail})" if detail else ""))
        print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
