# Cyber War Room — Project Audit (v2)

## Overall Verdict: Playable MVP, Needs Polish

The core game loop works. Players can register, get assigned to a nation, propose actions, vote on them, and watch scores change after resolution. The GM can drive rounds forward. Chat and diplomacy channels are live. This is a real game now — the gap is between "functional" and "conference-ready."

---

## Implementation Status: ~65% Complete

| Feature | v1 Audit | Now | Notes |
|---|---|---|---|
| Auth (register/login) | Working | **Working** | + join codes added |
| Team auto-assignment | Working | **Working** | + join-code-to-nation mapping |
| Chat (Socket.IO) | Basic | **Working** | team rooms functional |
| DB models & schema | Working | **Working** | 13 tables, dynamic column migration |
| Action catalog | 4 actions | **15 actions** | 12 global + 3 UN-specific |
| Proposal submission | Basic POST | **Working** | slot/action/target validation, auto-locks top proposals |
| Voting on proposals | Schema only | **Working** | POST /api/game/votes, upsert, tallies |
| Round timer | Hardcoded 6:00 | **Live countdown** | Socket.IO tick every 1s, pause/resume, auto-locks slots |
| Round lifecycle | Stub | **Full state machine** | start/advance/reset/pause/resume via admin API |
| Action resolution | Not built | **Working** | probabilistic success, stat updates, news generation |
| Leaderboard | Static baselines | **Dynamic** | baseline + deltas - escalation penalty |
| World Engine narrative | Stub string | **Still stub** | static text, no LLM integration |
| GM controls | Namespace only | **Admin panel** | round control + nuke toggle + crisis inject UI |
| AI shadow game | Not started | **Still not started** | placeholder reveal data |
| Advisors | NEXUS only | **All 11 teams** | 2-4 per nation with mood + hint |
| Briefings | 2 nations | **All 11 teams** | allies, threats, consequences |
| Frontend action picker | 3 hardcoded slots | **Dropdown + target selector** | action catalog fetched, target nation picker |
| Diplomacy channels | Not built | **Working** | create channel, send messages, Socket.IO broadcast |
| News ticker | Not built | **Working** | marquee animation, polls every 5s |
| Spectator view | Not built | **Working** | leaderboard table + timer + reveal preview |
| Join codes | Not built | **Working** | 11 pre-defined codes (NEXUS-OPS, etc.) |

---

## What Works End-to-End (The Core Loop)

1. Player opens app → registers or enters join code → lands on team dashboard
2. Sees their nation name, advisors, briefing, 3 action slots
3. Picks an action from dropdown, selects target nation, submits proposal
4. Teammates see proposal, vote +1 or -1
5. GM starts timer → live countdown ticks in header
6. GM advances round → resolution engine runs:
   - Winner per slot = highest votes (tie = earliest timestamp)
   - Success probability = 0.6 + (attacker security - target security) / 100, clamped [0.2, 0.9]
   - Effects applied to team stats (prosperity, security, influence, escalation)
   - NewsEvent created per action ("NEXUS attempted Cyber Espionage on IRONVEIL — SUCCESS")
7. Leaderboard updates: score = baseline + current deltas - escalation
8. Repeat for next round

**This loop is solid.** The game is playable.

---

## Remaining Gaps (Ranked by Impact)

### Tier 1 — Will Break the Conference Experience

**1. World Engine is still a stub**
`generate_stub_narrative()` still outputs the same filler sentence every round, so the news panel never reflects real actions or crises.
- **Fix:** Feed resolved actions/stat deltas into a templated or LLM-driven narrator and push unique copy every round.

**2. AI shadow game reveal missing**
`/api/reveal` serves placeholder data and the spectator view shows it immediately. The planned “AI destroyed the world” twist doesn’t exist yet.
- **Fix:** Run/record AI games, store their escalation/outcome curves, hide reveal data until game end, and build the doom→reveal flow.

**3. Diplomacy lacks mechanics**
There are no alliance/betrayal actions, so diplomacy chat is purely cosmetic.
- **Fix:** Add alliance/betrayal actions that impact stats/escalation and show their consequences in resolution + news.

**4. Timer resync gap**
`useRoundTimer` still trusts `round:tick` events; a missed packet leads to drift.
- **Fix:** Include server timestamps in tick payloads or add a `round:sync` event clients can request.

### Tier 2 — Will Hurt the Fun

**5. News ticker still static**
Same as item 1 — without narratives, the marquee is repetitive and loses audiences.

**6. News feed is polling**
Client polls `/api/game/news` every 5 seconds; there’s a lag after big events.
- **Fix:** Emit `news:event` Socket.IO messages when `NewsEvent` rows are created.

**7. No audio/flash cues**
Crises/nukes now have overlays, but there’s still no audio or projector-scale visual punch.

**8. Spectator view lacks charts**
Still just a leaderboard table; no escalation chart, crisis log, or reveal gating.

**9. UN team lacks special powers**
Actions exist but UN can’t see incoming proposals or veto moves as designed.

**10. Reveal data is still placeholder**
Until AI runs exist, the reveal sidebar is fake numbers (ties to Tier 1 item 2).

### Tier 3 — Nice to Have

**11. No QR codes for join codes** — table tents with QR codes would speed onboarding.

**12. False flag mechanic unused** — `Lifeline` model exists but nothing awards or consumes it.

**13. Intel puzzle solver missing** — players can’t submit intel answers even though `IntelDrop` exists.

**14. Chat lacks auto-scroll** — user experience issue on long sessions.

**15. Escalation thresholds silent** — no warnings when global escalation crosses 20/40/60/80.

**16. Test coverage ~5%** — still only one socket test; resolution/leaderboard paths untested.

**17. `datetime.utcnow` usage** — still mixed in some services; should standardize on timezone-aware datetimes.

---

## Bugs & Technical Issues

**18. Reveal data exposed mid-game**
`fetchRevealData()` still fires on mount, so AI comparison numbers show up in the sidebar before the game ends.
- **Fix:** Only fetch reveal data after doom/game over, or gate `/api/reveal` by role/state.

**19. Action slot “suggestions” still misleading**
`game_state()` still surfaces the first three catalog actions as “suggestions,” implying they’re the only options.
- **Fix:** Drop the suggestion field or replace it with neutral placeholders.

**20. Timer desync risk**
As above — still trusting ticks without resync.

**21. Resolution deletes proposals/votes**
History gets wiped each round, so there’s no recap or audit trail.

---

## Priority Build Order (Conference Countdown)

If time is limited, do these in order:

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 1 | Generated narrative from resolved actions | 3 hrs | Makes the news ticker interesting |
| 2 | News Socket.IO push + timer resync | 2 hrs | Keeps clients synchronized instantly |
| 3 | AI shadow game reveal & spectator polish | 4 hrs | Delivers the conference twist |
| 4 | Alliance/betrayal mechanics | 3 hrs | Gives diplomacy real stakes |
| 5 | Post-round history & recap UI | 3 hrs | Lets teams review decisions |
| 6 | Audio/flash cues for crises & doom | 2 hrs | Makes key moments impossible to miss |
| 7 | Hide reveal data until game ends | 30 min | Don't spoil the payoff |

---

## Summary

You've gone from 30% to roughly 70%. The core loop, crises, nuke locks, and doom overlay are in place — that's the heavy lifting. What remains is the **story + stagecraft**: dynamic narratives, AI reveal, alliance mechanics, spectator charts, and audio/visual punch. Nail the new priority list and the experience moves from “playable” to conference-grade.
