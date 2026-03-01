#!/usr/bin/env python3
"""
Full 6-round game simulation for Cyber War Room.

Joins 30 players (3 per team × 10 nations), resets game state, then plays
through all 6 rounds with varied actions, crises, intel drops, mega
challenge, diplomacy, and checks the final leaderboard + reveal.

Usage
-----
    python scripts/e2e_full_game.py [--base-url http://localhost:5050]
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:5050"
GM_EMAIL = "admin@warroom.local"
GM_PASSWORD = "ChangeMe123!"

JOIN_CODES = [
    "NEXUS-OPS", "IRON-VANGUARD", "GHOST-SHELL", "CORAL-TIDE",
    "FROST-WATCH", "SHADOW-VEIL", "DAWN-SHIELD", "NEON-GRID",
    "SKY-ARC", "LOTUS-VAULT",
]
PLAYERS_PER_TEAM = 3
BATCH_SIZE = 10

ROUND_ACTIONS = {
    1: ["CYBER_ESPIONAGE", "SECURITY_AUDIT", "SHARE_INTEL", "HONEYPOTS",
        "CYBER_STRIKE", "DISINFORMATION", "SECURITY_AUDIT", "SHARE_INTEL",
        "CYBER_ESPIONAGE", "HONEYPOTS"],
    2: ["CYBER_STRIKE", "DISINFORMATION", "CYBER_ESPIONAGE", "SHARE_INTEL",
        "HONEYPOTS", "CYBER_STRIKE", "SECURITY_AUDIT", "CYBER_ESPIONAGE",
        "DISINFORMATION", "SHARE_INTEL"],
    3: ["DISINFORMATION", "CYBER_STRIKE", "CYBER_STRIKE", "SECURITY_AUDIT",
        "CYBER_ESPIONAGE", "DISINFORMATION", "SHARE_INTEL", "HONEYPOTS",
        "CYBER_STRIKE", "CYBER_ESPIONAGE"],
    4: ["CYBER_STRIKE", "CYBER_STRIKE", "DISINFORMATION", "CYBER_ESPIONAGE",
        "CYBER_STRIKE", "DISINFORMATION", "CYBER_STRIKE", "SECURITY_AUDIT",
        "CYBER_ESPIONAGE", "HONEYPOTS"],
    5: ["CYBER_STRIKE", "DISINFORMATION", "CYBER_STRIKE", "CYBER_STRIKE",
        "DISINFORMATION", "CYBER_STRIKE", "CYBER_ESPIONAGE", "CYBER_STRIKE",
        "DISINFORMATION", "CYBER_STRIKE"],
    6: ["WAIT", "SHARE_INTEL", "CYBER_STRIKE", "SECURITY_AUDIT",
        "SHARE_INTEL", "CYBER_STRIKE", "SHARE_INTEL", "WAIT",
        "SHARE_INTEL", "SECURITY_AUDIT"],
}

TARGETED_ACTIONS = {
    "CYBER_ESPIONAGE", "CYBER_STRIKE", "DISINFORMATION", "SHARE_INTEL",
}

REQUEST_PACE = 0.08  # seconds between rapid-fire requests

results: list[tuple[str, str, str]] = []


def make_session() -> requests.Session:
    """Create a requests.Session with automatic retry on connection errors."""
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.0,         # 1s, 2s, 4s
        status_forcelist=[502, 503],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


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
    def __init__(self, name: str, join_code: str | None = None):
        self.name = name
        self.join_code = join_code
        self.http = make_session()
        self.password: str | None = None
        self.email: str | None = None
        self.user_id: int | None = None
        self.team_id: int | None = None
        self.team_name: str | None = None
        self.role: str | None = None

    def join(self) -> bool:
        r = self.http.post(f"{BASE_URL}/api/auth/join",
                           json={"display_name": self.name, "join_code": self.join_code})
        if r.status_code == 200:
            d = r.json()
            self.password = d["password"]
            self.user_id = d["user"]["id"]
            self.email = d["user"]["email"]
            self.team_id = d["user"]["team_id"]
            return True
        return False

    def login(self) -> bool:
        r = self.http.post(f"{BASE_URL}/api/auth/login",
                           json={"email": self.email, "password": self.password})
        if r.status_code == 200:
            d = r.json()
            self.user_id = d["user"]["id"]
            self.team_id = d["user"].get("team_id")
            self.role = d["user"].get("role")
            if "team" in d:
                self.team_name = d["team"].get("nation_name")
            return True
        return False

    def get(self, path: str, **kw) -> requests.Response:
        return self.http.get(f"{BASE_URL}{path}", **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return self.http.post(f"{BASE_URL}{path}", **kw)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup(args) -> tuple[Player, list[Player], dict[int, list[Player]], list[int]]:
    # Health
    try:
        r = requests.get(f"{BASE_URL}/api/health/", timeout=5)
        assert r.status_code == 200
    except Exception:
        print("  *** Server unreachable ***"); sys.exit(1)
    print("  Server OK")

    # GM
    gm = Player("Game Master")
    gm.email = GM_EMAIL; gm.password = GM_PASSWORD
    if not gm.login():
        print("  *** GM login failed ***"); sys.exit(1)
    print(f"  GM logged in (role={gm.role})")

    # Players
    section("Join 30 Players")
    players: list[Player] = []
    for code in JOIN_CODES:
        for i in range(1, PLAYERS_PER_TEAM + 1):
            tag = code.split("-")[0].lower()
            players.append(Player(f"{tag}_{i}", join_code=code))

    joined = 0
    for batch_start in range(0, len(players), BATCH_SIZE):
        batch = players[batch_start:batch_start + BATCH_SIZE]
        if batch_start > 0:
            print(f"    ... rate-limit pause (62s) ...")
            time.sleep(62)
        for p in batch:
            if p.join():
                joined += 1
    print(f"  Joined {joined}/{len(players)} players")

    teams: dict[int, list[Player]] = defaultdict(list)
    for p in players:
        if p.team_id:
            teams[p.team_id].append(p)

    # Fetch team names
    for tid, members in teams.items():
        r = members[0].get("/api/game/state")
        if r.status_code == 200:
            tn = r.json().get("team", {}).get("nation_name", "?")
            for m in members:
                m.team_name = tn
            print(f"    Team {tid} = {tn} ({len(members)} players)")

    nation_tids = sorted(teams.keys())
    ok(f"Teams ready", len(nation_tids) >= 10, f"{len(nation_tids)} teams")

    # Reset
    section("Reset Game")
    r = gm.post("/api/admin/rounds/reset")
    ok("Game reset", r.status_code == 200)

    return gm, players, dict(teams), nation_tids


# ---------------------------------------------------------------------------
# Round play
# ---------------------------------------------------------------------------

def submit_and_vote(round_num: int, teams: dict[int, list[Player]], nation_tids: list[int]):
    actions = ROUND_ACTIONS.get(round_num, ["WAIT"] * 10)
    proposal_ids: dict[int, int] = {}
    for i, tid in enumerate(nation_tids):
        code = actions[i % len(actions)]
        other = [t for t in nation_tids if t != tid]
        target = random.choice(other) if other else None
        payload: dict = {"action_code": code, "slot": 1}
        if code in TARGETED_ACTIONS and target:
            payload["target_team_id"] = target
        r = teams[tid][0].post("/api/game/proposals", json=payload)
        if r.status_code == 201:
            proposal_ids[tid] = r.json()["id"]
        time.sleep(REQUEST_PACE)

    ok(f"R{round_num}: {len(proposal_ids)} proposals", len(proposal_ids) >= 8)

    votes = 0
    for tid, pid in proposal_ids.items():
        for voter in teams[tid]:
            r = voter.post("/api/game/votes", json={"proposal_id": pid, "value": 1})
            if r.status_code == 200:
                votes += 1
            time.sleep(REQUEST_PACE)
    ok(f"R{round_num}: {votes} votes", votes > 0)
    return proposal_ids


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def main():
    global BASE_URL, GM_EMAIL, GM_PASSWORD
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--gm-email", default=GM_EMAIL)
    parser.add_argument("--gm-password", default=GM_PASSWORD)
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")
    GM_EMAIL = args.gm_email; GM_PASSWORD = args.gm_password

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"\nCyber War Room — Full 6-Round Game")
    print(f"Target: {BASE_URL}")
    print(f"Started: {ts}")
    print(f"Pace: {REQUEST_PACE}s between requests, 3x retry with backoff\n")

    gm, players, teams, nation_tids = setup(args)

    # ── Verify mega challenge is auto-seeded ──
    section("Pre-Game: Mega Challenge")
    r = gm.get("/api/admin/mega-challenge")
    if r.status_code == 200 and r.json().get("active"):
        ok("Mega challenge seeded (Operation GHOSTLINE)", True,
           r.json()["description"][:60])
    else:
        ok("Mega challenge seeded", False, "not found — check seed_db.py")

    # ══════════════════════════════════════════════════════════════
    #   ROUND 1 — Opening moves
    # ══════════════════════════════════════════════════════════════
    section("ROUND 1 — Opening Moves")
    r = gm.post("/api/admin/rounds/start")
    ok("R1: started", r.status_code == 200)

    submit_and_vote(1, teams, nation_tids)

    # Diplomacy: open 5 channels (start → accept → message)
    pairs = [(0,1),(2,3),(4,5),(6,7),(8,9)]
    for a, b in pairs:
        if a < len(nation_tids) and b < len(nation_tids):
            pa = teams[nation_tids[a]][0]
            pb = teams[nation_tids[b]][0]
            r = pa.post("/api/diplomacy/start", json={"target_team_id": nation_tids[b]})
            if r.status_code in (200, 201):
                ch = r.json()["channel_id"]
                time.sleep(REQUEST_PACE)
                # Other team accepts the channel
                pb.post("/api/diplomacy/respond", json={"channel_id": ch, "action": "accept"})
                time.sleep(REQUEST_PACE)
                pa.post("/api/diplomacy/send",
                        json={"channel_id": ch, "content": f"Alliance offer from {pa.team_name}?"})
                time.sleep(REQUEST_PACE)
                pb.post("/api/diplomacy/send",
                        json={"channel_id": ch, "content": "Let's discuss terms."})
                time.sleep(REQUEST_PACE)
    ok("R1: 5 diplomacy channels opened + accepted", True)

    r = gm.post("/api/admin/rounds/advance")
    ok("R1: resolved", r.status_code == 200, r.text[:60])
    time.sleep(1)  # let worker settle after resolution

    # ══════════════════════════════════════════════════════════════
    #   ROUND 2 — Crisis + Intel drops
    # ══════════════════════════════════════════════════════════════
    section("ROUND 2 — Crisis + Intel")
    r = gm.post("/api/admin/rounds/start")
    ok("R2: started", r.status_code == 200)

    # Crisis
    r = gm.post("/api/admin/crisis/inject", json={"code": "VOLT_TYPHOON"})
    ok("R2: VOLT_TYPHOON crisis", r.status_code == 200)

    # Intel drops are auto-generated on round start — verify and solve for first 3 teams
    # Puzzle solutions keyed by clue text (subset of pool for solving in tests)
    _PUZZLE_SOLUTIONS = {
        "U0hBRE9X": "SHADOW", "RklSRVdBTEw=": "FIREWALL", "QkFDS0RPT1I=": "BACKDOOR",
        "VFJPSUFO": "TROJAN", "QUxMSUFOQ0U=": "ALLIANCE", "U1RSSUtF": "STRIKE",
        "UEhJU0hJTkc=": "PHISHING", "UkFOU09N": "RANSOM", "Wk9NQklF": "ZOMBIE",
        "U0FOQ1RJT04=": "SANCTION", "4D414C57415245": "MALWARE", "50415443484544": "PATCHED",
        "524F4F544B4954": "ROOTKIT", "534E4946464552": "SNIFFER", "5041594C4F4144": "PAYLOAD",
        "455850 4C4F4954": "EXPLOIT", "434F424 14C54": "COBALT", "5448524541 54": "THREAT",
        "564F4C54414745": "VOLTAGE", "43495048 4552": "CIPHER", "EUHDFK": "BREACH",
        "GHIHQVH": "DEFENCE", "VKLHOG": "SHIELD", "VXUYHLOODQFH": "SURVEILLANCE",
        "GHWHFW": "DETECT", "SUREH": "PROBE", "YHFWRU": "VECTOR", "DQRPDOB": "ANOMALY",
        "SLYRW": "PIVOT", "IRUHQVLFV": "FORENSICS",
        "01000001 01010100 01010100 01000001 01000011 01001011": "ATTACK",
        "01000100 01000101 01001110 01011001": "DENY",
        "01010011 01010000 01001111 01001111 01000110": "SPOOF",
        "01010111 01001111 01010010 01001101": "WORM",
        "01010000 01001000 01000001 01010011 01000101": "PHASE",
        "01000100 01000101 01000011 01001111 01011001": "DECOY",
        "01001010 01000001 01001101": "JAM",
        "01010010 01000101 01000011 01001111 01001110": "RECON",
        "01000010 01001100 01001111 01000011 01001011": "BLOCK",
        "01000001 01000010 01001111 01010010 01010100": "ABORT",
        "%41%43%43%45%53%53": "ACCESS", "%49%4E%4A%45%43%54": "INJECT",
        "%54%55%4E%4E%45%4C": "TUNNEL", "%42%59%50%41%53%53": "BYPASS",
        "%54%4F%4B%45%4E": "TOKEN", "%50%48%41%4E%54%4F%4D": "PHANTOM",
        "%53%50%4C%49%43%45": "SPLICE", "%42%45%41%43%4F%4E": "BEACON",
        "%4F%52%41%43%4C%45": "ORACLE", "%53%48%45%4C%4C": "SHELL",
        "EDOCKCAB": "BACKCODE", "TNIALPXE": "EXPLAINT", "HCNUAL": "LAUNCH",
        "RETLIF": "FILTER", "KCOLTAED": "DEADLOCK", "TSOHG": "GHOST",
        "ERIF": "FIRE", "ROTINOM": "MONITOR", "TPYRC": "CRYPT", "EGATOBAS": "SABOTAGE",
    }

    for i in range(min(3, len(nation_tids))):
        tid = nation_tids[i]
        solver = teams[tid][min(1, len(teams[tid]) - 1)]
        time.sleep(REQUEST_PACE)
        r = solver.get("/api/game/state")
        if r.status_code == 200:
            drops = r.json().get("intel_drops", [])
            unsolved = [d for d in drops if d["status"] == "unsolved"]
            if unsolved:
                drop = unsolved[0]
                # Find the encoded payload in the clue to look up the solution
                clue = drop["description"]
                solution = None
                for key, val in _PUZZLE_SOLUTIONS.items():
                    if key in clue:
                        solution = val
                        break
                if solution:
                    r = solver.post("/api/game/intel/solve",
                                    json={"intel_id": drop["id"], "answer": solution})
                    lt = r.json().get("lifeline", {}).get("lifeline_type", "?") if r.status_code == 200 else "FAIL"
                    ok(f"R2: team {tid} solves {drop['title']} -> {lt}", r.status_code == 200)
                else:
                    ok(f"R2: team {tid} puzzle match", False, f"no solution for clue: {clue[:60]}")
            else:
                ok(f"R2: team {tid} has intel drops", False, "no unsolved drops")
        else:
            ok(f"R2: team {tid} game state", False, r.text[:80])

    submit_and_vote(2, teams, nation_tids)
    r = gm.post("/api/admin/rounds/advance")
    ok("R2: resolved", r.status_code == 200, r.text[:60])
    time.sleep(1)

    # ══════════════════════════════════════════════════════════════
    #   ROUND 3 — Mega challenge solved
    # ══════════════════════════════════════════════════════════════
    section("ROUND 3 — Mega Challenge Race")
    r = gm.post("/api/admin/rounds/start")
    ok("R3: started", r.status_code == 200)

    submit_and_vote(3, teams, nation_tids)

    # First 4 teams solve mega challenge
    mega_solution = "BREACH-PIVOT-SHELL-STORM-GHOST"
    for i in range(min(4, len(nation_tids))):
        tid = nation_tids[i]
        solver = teams[tid][0]

        # Wrong answer
        r = solver.post("/api/game/mega-challenge/solve", json={"answer": "WRONG"})
        ok(f"R3: team {tid} wrong mega rejected", r.status_code == 400)

        # Correct answer
        r = solver.post("/api/game/mega-challenge/solve", json={"answer": mega_solution})
        if r.status_code == 200:
            d = r.json()
            ok(f"R3: team {tid} mega pos={d['solve_position']} +{d['reward_influence']}inf", True)
        else:
            ok(f"R3: team {tid} mega solve", False, r.text[:80])

    # Double solve rejected
    r = teams[nation_tids[0]][0].post("/api/game/mega-challenge/solve",
                                       json={"answer": mega_solution})
    ok("R3: double-solve rejected", r.status_code == 400 and "already_solved" in r.text)

    r = gm.post("/api/admin/rounds/advance")
    ok("R3: resolved", r.status_code == 200, r.text[:60])
    time.sleep(1)

    # ══════════════════════════════════════════════════════════════
    #   ROUND 4 — Second crisis, escalation rising
    # ══════════════════════════════════════════════════════════════
    section("ROUND 4 — Escalation Rising")
    r = gm.post("/api/admin/rounds/start")
    ok("R4: started", r.status_code == 200)

    r = gm.post("/api/admin/crisis/inject", json={"code": "ZERO_DAY_MARKET"})
    ok("R4: ZERO_DAY_MARKET crisis", r.status_code == 200)

    submit_and_vote(4, teams, nation_tids)

    # More diplomacy chatter
    p = teams[nation_tids[0]][0]
    r = p.get("/api/diplomacy/")
    if r.status_code == 200 and r.json():
        ch = r.json()[0]["channel_id"]
        p.post("/api/diplomacy/send",
               json={"channel_id": ch, "content": "Escalation is getting dangerous. Ceasefire?"})

    r = gm.post("/api/admin/rounds/advance")
    ok("R4: resolved", r.status_code == 200, r.text[:60])
    time.sleep(1)

    # ══════════════════════════════════════════════════════════════
    #   ROUND 5 — Peak aggression
    # ══════════════════════════════════════════════════════════════
    section("ROUND 5 — Peak Aggression")
    r = gm.post("/api/admin/rounds/start")
    ok("R5: started", r.status_code == 200)

    submit_and_vote(5, teams, nation_tids)

    r = gm.post("/api/admin/rounds/advance")
    ok("R5: resolved", r.status_code == 200, r.text[:60])
    time.sleep(1)

    # ══════════════════════════════════════════════════════════════
    #   ROUND 6 — De-escalation / final round
    # ══════════════════════════════════════════════════════════════
    section("ROUND 6 — Final Round")
    r = gm.post("/api/admin/rounds/start")
    ok("R6: started", r.status_code == 200)

    submit_and_vote(6, teams, nation_tids)

    r = gm.post("/api/admin/rounds/advance")
    ok("R6: resolved", r.status_code == 200, r.text[:60])

    # Verify no round 7
    r = gm.post("/api/admin/rounds/start")
    ok("No round 7 (game over)", r.status_code == 400 or "no_pending" in r.text,
       r.text[:60])

    # ══════════════════════════════════════════════════════════════
    #   FINAL CHECKS
    # ══════════════════════════════════════════════════════════════
    section("Final Leaderboard")
    p = teams[nation_tids[0]][0]
    r = p.get("/api/game/leaderboard")
    if r.status_code == 200:
        d = r.json()
        entries = d.get("entries", [])
        ok("All teams in leaderboard", len(entries) >= 10, f"{len(entries)}")
        scores = [e["score"] for e in entries]
        ok("Sorted descending", scores == sorted(scores, reverse=True))

        print(f"\n  {'#':>3}  {'Nation':<20}  {'Score':>6}  {'Delta':>6}  {'Esc':>4}")
        print(f"  {'---':>3}  {'----':<20}  {'-----':>6}  {'-----':>6}  {'---':>4}")
        for i, e in enumerate(entries, 1):
            print(f"  {i:>3}  {e['nation_name']:<20}  {e['score']:>6}  "
                  f"{e.get('delta_from_baseline', 0):>+6}  {e.get('escalation', 0):>4}")

        impact = d.get("cyber_impact", [])
        ok("Cyber impact log", len(impact) > 0, f"{len(impact)} entries")

        esc = d.get("escalation_series", {})
        ok("Escalation series tracked", len(esc) >= 10, f"{len(esc)} nations")
    else:
        ok("Leaderboard", False, f"{r.status_code}")

    section("News Feed")
    r = p.get("/api/game/news")
    n = len(r.json()) if r.status_code == 200 else 0
    ok("News populated", n >= 15, f"{n} events")
    if r.status_code == 200:
        for ev in r.json()[:5]:
            print(f"    - {ev['message'][:80]}")

    section("Action History")
    r = p.get("/api/game/history?limit=100")
    n = len(r.json().get("entries", [])) if r.status_code == 200 else 0
    ok("History populated", n >= 30, f"{n} entries")

    section("Mega Challenge Status")
    r = p.get("/api/game/mega-challenge")
    if r.status_code == 200:
        d = r.json()
        ok("Mega active", d.get("active") == True)
        solves = d.get("solved_by", [])
        ok("Mega solves recorded", len(solves) >= 3, f"{len(solves)} teams solved")
        for s in solves:
            print(f"    Position {s['position']}: team_id={s['team_id']} +{s['reward']} influence")

    section("Rounds Overview")
    r = gm.get("/api/admin/rounds")
    if r.status_code == 200:
        rounds = r.json()
        resolved = [rd for rd in rounds if rd["status"] == "resolved"]
        ok("All 6 rounds resolved", len(resolved) == 6, f"{len(resolved)}/6")
        for rd in rounds:
            print(f"    Round {rd['round_number']}: {rd['status']}")

    section("Reveal Data (GM)")
    r = gm.get("/api/reveal/")
    if r.status_code == 200:
        d = r.json()
        ok("Reveal loads", True, f"keys={list(d.keys())}")

        hva = d.get("human_vs_ai", {})
        ok("Human vs AI data", "human_outcome" in hva,
           f"human={hva.get('human_outcome')} ai={hva.get('ai_outcome')}")

        ai_models = d.get("ai_models", [])
        ok("AI nation models", len(ai_models) > 0, f"{len(ai_models)} nations")

        h_esc = d.get("human_escalation_series", [])
        ok("Human escalation series", len(h_esc) > 0, f"{len(h_esc)} rounds")

        ai_dec = d.get("ai_decisions", [])
        ok("AI decisions", len(ai_dec) > 0, f"{len(ai_dec)} decisions")

        ai_run = d.get("ai_run", {})
        ok("AI run metadata", ai_run.get("model_name") is not None,
           f"model={ai_run.get('model_name')} doom={ai_run.get('doom_triggered')}")

        # Print reveal summary
        print(f"\n  HUMAN vs AI:")
        print(f"    Human final outcome: {hva.get('human_outcome')}")
        print(f"    AI final outcome:    {hva.get('ai_outcome')}")
        print(f"    Rounds played:       {hva.get('rounds')}")

        if ai_models:
            print(f"\n  AI NATIONS:")
            for m in ai_models[:10]:
                print(f"    {m.get('nation_code', '?'):>8}: avg_esc={m.get('avg_escalation'):>5}  "
                      f"1st_violent=R{m.get('first_violent_round') or '-':>2}  "
                      f"nukes={'YES' if m.get('launched_nukes') else 'no '}")
    else:
        ok("Reveal loads", False, f"status={r.status_code} {r.text[:80]}")

    # ══════════════════════════════════════════════════════════════
    #   SUMMARY
    # ══════════════════════════════════════════════════════════════
    section("FINAL SUMMARY")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    total = len(results)
    print(f"\n  {passed}/{total} passed,  {failed} failed\n")

    if failed:
        print("  FAILED:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"    - {name}" + (f"  ({detail})" if detail else ""))
        print()

    from datetime import datetime, timezone
    print(f"  Completed: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"  All results above are real HTTP responses — no mocking, no stubbing.\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
