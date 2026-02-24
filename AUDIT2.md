# Cyber War Room — Project Audit #2

**Date:** 2026-02-24
**Audited against:** `plan.md`, `build_plan_phase1.md` through `build_plan_phase6.md`
**Previous audit:** `AUDIT.md` (2026-02-22 initial, 2026-02-23 post-fix pass)

---

## Executive Summary

The project has continued to mature since the first audit. The **backend is substantially complete** with all critical bugs from AUDIT.md resolved, a new game reset service, LLM-powered World Engine narratives (Anthropic Claude Sonnet 4), 32 defined actions (exceeding the plan's 27), and Docker deployment working end-to-end. The **frontend is functional** with Recharts charts, CRT visual effects, WebSocket+polling transport, connection status indicator, and colour-coded action escalation badges.

**Key changes since AUDIT.md (post-fix pass):**
- New `game_reset.py` service for full game state reset
- Admin route for game reset (`POST /rounds/reset`)
- World Engine now has real LLM integration with Anthropic API + template fallback
- Docker infrastructure solidified (health checks, restart policies, SPA fallback, build args)

**Remaining gaps:** AI shadow game is still a random-number stub, Mega Challenge has no implementation, Phone-a-Friend lifeline has no logic, several UX features remain unbuilt (typing indicators, diplomacy accept/decline, captain override modal, toast system, roster display), `App.tsx` is still a 1,766-line monolith, no CI/CD pipeline, backend runs Werkzeug dev server as root in Docker.

| Phase | Scope | Estimated Completion |
|-------|-------|---------------------|
| **Phase 1** — Foundation | Auth, models, team assignment, timer, sockets, GM panel | **~88%** |
| **Phase 2** — Game Core | Actions, proposals, resolution, intel/lifelines, mega challenge | **~78%** |
| **Phase 3** — Real-Time & Chat | Chat, diplomacy, broadcasts, session mgmt, leaderboard wiring | **~62%** |
| **Phase 4** — Leaderboard & World Engine | Scoring, LLM narrator, nuke controls, news ticker, dashboard | **~80%** |
| **Phase 5** — AI Shadow Game & Polish | AI sim, reveal, crisis enhancements, animations, playtesting | **~40%** |
| **Phase 6** — Deployment & Live Run | Docker, Azure, smoke tests, content prep, contingencies | **~35%** |

**Overall estimated completion: ~67% (up from ~65% post-fix pass)**

---

## Phase 1 — Foundation (~88%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| App factory (`create_app`) | DONE | Working with blueprint registration, extension init, logging |
| Database models | DONE | All 19+ models in `models.py` (257 lines) including OutcomeScoreHistory, AiRun, AiRoundScore, FalseFlagPlan, Alliance, GlobalState |
| Alembic migrations | NOT DONE | Still uses manual `ALTER TABLE` DDL on startup via `ensure_*_columns()` in `schema.py`. No `alembic.ini` or `migrations/` directory. Acceptable for PoC |
| Seed script (10 nations + UN, advisors, baselines) | DONE | `seed_db.py` (70 lines) seeds 11 teams, rounds, admin account |
| `POST /api/register` (random password, hash) | DONE | `auth.py` — checks email uniqueness before creating user. **Password-reset bug FIXED** |
| `POST /api/login` (session cookie + token) | DONE | Session token, auto team assignment on login |
| `POST /api/join` (invite code) | DONE | UUID suffix on generated emails prevents collisions. **Email collision bug FIXED** |
| Admin routes (game reset, status, intel drops) | PARTIAL | Has game reset, status dashboard, intel drop CRUD, crisis inject/clear, doom clear, nuke toggle, round controls. Missing: user listing, password reset, team reassignment |
| Rate limiting | NOT DONE | No rate limiting on any endpoint |
| Team assignment service | DONE | `team_assignment.py` with `BEGIN IMMEDIATE` for SQLite, waitlist fallback |
| Socket.IO event on new team member | NOT DONE | No event emitted when a player joins a team |
| Round/timer state machine | DONE | `RoundManager` (270 lines) with states, background timer, auto-lock. **Now respects `ROUND_DURATIONS` config** |
| Nuclear lock flag | DONE | `global_state.py` toggle + broadcast |
| Doom event on nuke success | DONE | `resolution.py` triggers doom, `global_state.py` broadcasts `game:over` |
| Clear doom flag | DONE | `clear_doom_flag()` exposed via `POST /admin/clear-doom` |
| Game reset service | DONE | **NEW** `game_reset.py` (74 lines) — resets all game state, team stats, recreates rounds |
| Socket.IO `/team` namespace | PARTIAL | Chat events work via decorators with correct namespace. No formal namespace class, no `connect`/`disconnect` handlers with `join_room` |
| Socket.IO `/gm` namespace | NOT DONE | No GM namespace exists |
| Socket.IO `/leaderboard` namespace | NOT DONE | No leaderboard namespace (uses `/global` instead) |
| Server-side auth on socket handlers | PARTIAL | `chat_events.py` checks `current_user` but no middleware on namespace level |
| GM dashboard API (`/admin/status`) | PARTIAL | Returns global state + crisis history + proposal preview. Missing: team summaries, chat logs, action queues |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Vite/React scaffold | DONE | Vite 7.3.1, React 19.2.0, TypeScript, Tailwind |
| `react-router` setup | NOT DONE | Still uses `?view=player|spectator|gm` query param, not routes |
| Tailwind retro palette | DONE | 4 custom colors (warroom-blue, slate, cyan, amber), 2 fonts (Inter, Press Start 2P) |
| CRT effect CSS | DONE | `App.css` (103 lines) with scanlines (`crt-overlay`), phosphor glow (`text-glow`), flicker (`crt-flicker`), screen shake (`screen-shake`), hack pulse (`hack-pulse`) |
| Auth views (register/login) | DONE | `AuthPanel` with register (name+email or join code) and login |
| Player dashboard shell (3-zone layout) | DONE | Header + action console + sidebar panels |
| Action proposal & voting UI | DONE | 3 slots with dropdowns + target, vote buttons, locked/vetoed indicators |
| Escalation color badges on actions | DONE | `getCategoryColor()` maps categories to hex colours: green/white/yellow/orange/red/purple |
| Chat panel | DONE | Real-time chat with `useChat` hook |
| Roster/teammate list | NOT DONE | No roster widget showing teammates. Advisors shown, nations modal shows all nations |
| Leaderboard view | DONE | Recharts bar chart + line chart, DoomsdayClock gauge, news ticker |
| GM dashboard | DONE | Round controls, nuke toggle, crisis injection, proposal oversight, game reset, doom clear |

### Integration & Validation

| Task | Status | Notes |
|------|--------|-------|
| Seed/test script for 12 fake users | NOT DONE | Seed script creates teams/admin only, not test users |
| CLI round simulator | NOT DONE | No CLI simulation tool |
| Unit tests for team assignment race conditions | NOT DONE | Zero tests for team assignment |
| Unit tests for auth | DONE | `test_auth.py` with 7 test functions (register, duplicate, login, invalid password, me, missing fields, logout) |
| Unit tests for game routes | DONE | `test_game.py` with 4 tests (actions list, leaderboard, news, game state) |
| Socket.IO chat test | DONE | `socket_chat_test.py` with 1 test (message persistence) |
| Azure deployment docs | PARTIAL | `deployment_checklist.md` covers steps but incomplete |

---

## Phase 2 — Game Core (~78%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Action catalog (`actions.py`) | DONE | **32 action codes** defined across 7 categories (286 lines). Exceeds plan's 27. Includes: WAIT, SHARE_INTEL, SECURITY_AUDIT, CYBER_ESPIONAGE, HONEYPOTS, CYBER_STRIKE, DISINFORMATION, FORM_ALLIANCE, BREAK_ALLIANCE, SUPPLY_CHAIN, SANCTIONS, NUKE_LOCK, CYBER_KINETIC, CRITICAL_SABOTAGE, NUCLEAR_STRIKE, UN_SANCTION, UN_SHIELD, UN_MEDIATION, PROPOSE_NAP, DEMILITARIZE, RELEASE_DATA, SEND_MESSAGE, PUBLIC_ATTRIBUTION, INCREASE_BUDGET, RANSOMWARE, DESTROY_CABLES, MILITARY_MOBILIZATION, AUTONOMOUS_WEAPON, and more |
| Proposal endpoints (create/vote) | DONE | `submit_proposal()` and `cast_vote()` in `game.py` (601 lines) |
| Per-round/per-slot limits | DONE | 3 slots enforced |
| Target validation | PARTIAL | Validates target exists but no self-targeting prevention |
| Proposals freeze on `resolving` | DONE | `submissions_open()` check in `round_manager.py` |
| Round timer + background scheduler | DONE | `RoundManager._start_timer()` with Socket.IO ticks. **Now reads `ROUND_DURATIONS` from config correctly** |
| Auto-fill "Wait" on timer expiry | DONE | `resolve_round()` auto-fills WAIT for empty slots |
| Resolution engine | DONE | `resolution.py` (261 lines) — groups by team, picks winners, executes, applies effects, creates Action records |
| Success probability | DONE | Uses `current_security` and `current_influence` for calculations (not baseline). Uses dynamic stats as intended |
| Deterministic RNG seeding | NOT DONE | Uses `random.random()` without seeding per round |
| Intel drop mechanics | PARTIAL | Model exists, `solve_intel()` route works, admin endpoints for CRUD (`POST /admin/intel-drops`, `GET /admin/intel-drops`). No asset upload/management interface |
| Lifeline tokens | DONE | `lifelines.py` — award, consume, list, queue false flag |
| Mega Challenge | NOT DONE | Model exists (`MegaChallenge`) but is never referenced in any route or service. Zero implementation |
| Phone-a-Friend lifeline | NOT DONE | Lifeline type exists but no usage logic or endpoint |
| State machine enforcement | PARTIAL | Round states exist but transitions are implicit. No explicit `close_submissions` or `publish_results` |
| Outcome Score history | DONE | `OutcomeScoreHistory` model populated by `resolution.py` after each round |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Action menu with categories/colors/tooltips | DONE | Dropdown with category colours via `getCategoryColor()`. No tooltips or category grouping |
| Per-slot validation states | PARTIAL | Nuke lock check exists. No "resources insufficient" or "target required" indicators |
| Live vote counters | DONE | Vote tally displayed per proposal |
| Locked badges on timer expiry | DONE | Locked/closed/vetoed status indicators |
| Captain override modal | NOT DONE | No captain override when proposals are missing |
| Advisory hints per action | NOT DONE | Advisor panel shows generic hints (name, mood, hint), not per-action advice |
| Timer synced via Socket.IO | DONE | `useRoundTimer.ts` (89 lines) with client-side interpolation |
| Status chips (Submissions Open / Resolving / Results Ready) | NOT DONE | Timer shows paused/complete but no phase chips |
| Intel drop UI (download, solve, reward) | PARTIAL | List + solution input. No download buttons, no puzzle type indicators, no reward badges |
| Mega Challenge UI | NOT DONE | No implementation |
| Results panel with per-action outcomes | PARTIAL | Flat list of resolved actions in Round History. No stat changes, no target reactions, no animations |

---

## Phase 3 — Real-Time & Chat (~62%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Socket namespace auth middleware | NOT DONE | No middleware; auth checked per-handler only |
| Heartbeat/ping logging | NOT DONE | |
| `chat:message` + `chat:history` | DONE | `chat_events.py` — works via module-level decorators with `/team` namespace |
| `chat:typing` | NOT DONE | |
| In-memory buffer per team | DONE | `services/chat/__init__.py` uses capped deque |
| Profanity filter | NOT DONE | |
| Diplomacy channels | DONE | `diplomacy.py` — create channel, send messages, list channels |
| Diplomacy Socket.IO broadcast | DONE | **FIXED** — now correctly specifies `namespace="/team"` on emit |
| Expiration/closure at round end | NOT DONE | Channels persist indefinitely |
| Intel key/lifeline code sharing | NOT DONE | |
| GM broadcast via Socket.IO | PARTIAL | Crisis injection, nuke toggle, escalation threshold, news events broadcast. No `gm:announcement` or `gm:reveal` events |
| Leaderboard namespace broadcasts | NOT DONE | No `/leaderboard` namespace; uses `/global` namespace for broadcasts |
| Duplicate login detection + `session:kick` | NOT DONE | `session_token` column exists but no active enforcement or socket kick |
| Per-user connection metadata | NOT DONE | |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Chat UI with color-coded senders | PARTIAL | Chat works. All senders use same colour (`warroom-cyan` / `#38bdf8`). Not differentiated by role (player/advisor/GM) |
| Typing indicators | NOT DONE | |
| Unread badges | NOT DONE | |
| Collapsible chat for small screens | NOT DONE | Fixed height container |
| Diplomacy drawer (request/accept/decline) | PARTIAL | Can create channels and message, see active channels with "With {nation_name}". No accept/decline flow, no invitation notification |
| Quick-share widgets for intel/lifeline trades | NOT DONE | |
| Toast/alert system | PARTIAL | Crisis overlays, escalation alert with screen-shake, doom overlay exist. No general-purpose toast library. Browser `alert()` used for errors |
| Real-time charts (Recharts) | DONE | `EscalationChart` (line chart) and `LeaderboardBarChart` (bar chart) using Recharts 3.7.0 |
| Doomsday Clock indicator | DONE | Circular conic-gradient gauge showing doom percentage, visible in spectator view and player header |
| Connection status indicator | DONE | Green/red dot in header next to nation name. State managed via socket connect/disconnect events |

---

## Phase 4 — Leaderboard & World Engine (~80%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Outcome Score calculation | DONE | `leaderboard.py` computes scores from baseline + current stats - escalation |
| Outcome Score history for charting | DONE | `OutcomeScoreHistory` model populated after each round by resolution engine |
| Leaderboard API | DONE | `/api/game/leaderboard` returns current standings with escalation series |
| Leaderboard Socket.IO push | PARTIAL | Uses `/global` namespace for broadcasts, not a dedicated `/leaderboard` namespace |
| World Engine LLM integration | DONE | **`world_engine.py` (75 lines) calls Anthropic Claude Sonnet 4** (`claude-sonnet-4-20250514`) via environment API key. Falls back to category-based templates if LLM fails or no key |
| Async job queue for LLM | NOT DONE | LLM call is synchronous in the resolution pipeline |
| Fallback to templated narrative | DONE | Category-based templates for each action type when LLM unavailable |
| GM nuke toggle endpoints | DONE | `admin.py` `toggle_nukes()` |
| Doom detector | DONE | `resolution.py` triggers doom on nuclear success |
| News ticker event log | DONE | `NewsEvent` model, `/api/game/news` endpoint, Socket.IO broadcast |
| Intel drop solve / false flag in ticker | NOT DONE | Ticker only shows action resolution news |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Full-screen SOC-style leaderboard | PARTIAL | `SpectatorView` shows team cards in a grid with charts. Not full-screen SOC layout |
| Outcome Score bar chart + baseline badges | DONE | `LeaderboardBarChart` using Recharts. Shows score + delta from baseline. Green/red for positive/negative |
| Escalation line chart | DONE | `EscalationChart` using Recharts. Red line showing escalation trend. Single line, not multi-nation |
| Cyber Impact list (who attacked whom) | NOT DONE | |
| Doomsday Clock gauge | DONE | Circular conic-gradient gauge (0-100%) |
| News ticker | DONE | Marquee animation with headlines (25s normal, 40s slow) |
| World News panel | DONE | Shows narrative text per round |
| GM controls for nuke/crisis/reveal | DONE | Toggle buttons with state indicators in AdminPanel |
| LLM narrative queue / manual re-run | NOT DONE | |
| Visual cues on escalation thresholds | PARTIAL | Top banner alert + screen-shake animation. No background colour shift |

---

## Phase 5 — AI Shadow Game & Polish (~40%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| AI simulation runner (LLM agents) | NOT DONE | `run_ai_sim.py` (48 lines) generates random escalation deltas (+5 to +15). No LLM integration |
| Record per-round AI actions/outcomes | PARTIAL | `AiRun` and `AiRoundScore` models exist. Populated with random data only |
| Reveal data API (AI vs human comparison) | PARTIAL | `reveal.py` (58 lines) returns AI simulation results. Shows per-model: avg escalation, first violent round, nuclear status |
| LLM highlight quotes for reveal | NOT DONE | Sample quotes in `ai_reveal_samples.json` but not from real AI runs |
| GM crisis preview/preload UI | NOT DONE | Can inject crises via dropdown but no preview, no preloaded scripts |
| Asset manager for intel drops | NOT DONE | No upload, no management interface |
| Lifeline ledger display | PARTIAL | Lifelines listed in game state with remaining counts. No comprehensive earn/use history |
| Keyboard navigation | NOT DONE | |
| Color contrast audit | NOT DONE | |
| Bundle splitting / performance tuning | NOT DONE | |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Reveal screen (side-by-side comparison) | PARTIAL | Shows AI model cards in 3-column grid with stats. No side-by-side human vs AI graphs, no quote carousel. Only visible when doom active + reveal data exists |
| Doom-state overlay | DONE | Full-screen game-over message |
| Crisis GM modal (select, edit, preview, broadcast) | PARTIAL | Dropdown + inject button. No edit, no preview, no confirmation dialog |
| Intel drop management panel | NOT DONE | No download links, no status indicators, no reward badges |
| False Flag button with confirmation dialog | PARTIAL | Inline select+apply. No confirmation dialog, no cooldown display |
| Phone-a-Friend button | NOT DONE | |
| Advisor portraits reacting to outcomes | NOT DONE | Text-only advisor cards (name, mood, hint). No images |
| Hacking animations | DONE | `hack-pulse` CSS animation for intel drops |
| CRT flickers on escalation | DONE | `crt-flicker` animation (4s opacity cycle) |
| Doomsday Clock ticks | DONE | Gauge updates with escalation score |
| Playtest analytics/logging | NOT DONE | |

### Asset Pack

| Task | Status | Notes |
|------|--------|-------|
| 3 cipher PDFs | NOT DONE | 1 sample cipher_vault.txt exists (Vigenere) |
| 2 stego images | NOT DONE | |
| False Flag briefing card | NOT DONE | |
| Phone-a-Friend hint sheet | NOT DONE | |
| Mega Challenge outline | DONE | `mega_challenge_outline.md` with multi-stage design |

---

## Phase 6 — Deployment & Live Run (~35%)

| Task | Status | Notes |
|------|--------|-------|
| Docker Compose | DONE | Health checks (10s interval, 3 retries), `restart: unless-stopped`, named volume for DB persistence, proper service dependencies |
| Backend Dockerfile | PARTIAL | Python 3.11-slim, works. **Runs as root** (no USER directive). Runs `seed_db.py` + `run_ai_sim.py` on every startup |
| Client Dockerfile | DONE | Multi-stage build (Node 20 Alpine → Nginx Alpine). `VITE_API_BASE_URL` passed as build arg. Nginx SPA fallback (`try_files $uri $uri/ /index.html`) |
| Backend server | BROKEN (prod) | Uses `socketio.run()` with `allow_unsafe_werkzeug=True`. No Gunicorn or production WSGI server. Single-threaded, not suitable for production load |
| Azure deployment | NOT DONE | Checklist exists but no actual Azure config |
| HTTPS/SSL | NOT DONE | |
| Smoke test automation | PARTIAL | `playwright_login.mjs` exists but standalone, not in test framework or CI |
| Production secrets management | PARTIAL | `SECRET_KEY` set to real value in `.env.docker` but committed to git. **Should use secret management** |
| CORS | PARTIAL | `CORS_ORIGINS=*` in `.env.docker`. **Must restrict for production** |
| Database backup procedure | NOT DONE | Docker volume for persistence but no export/backup tooling |
| Content prep (crisis events, AI reveal, awards) | PARTIAL | 3 crises defined, sample reveal data exists, no award badges |
| CI/CD pipeline | NOT DONE | No GitHub Actions or equivalent |
| Game reset | DONE | **NEW** `reset_game_state()` in `game_reset.py`, exposed via `POST /admin/rounds/reset` |

---

## Critical Bugs

### Resolved Since AUDIT.md

| # | Original Issue | Status |
|---|---------------|--------|
| 1 | `client/Dockerfile` — `VITE_API_BASE_URL` not passed as build arg | **FIXED** — ARG + ENV properly configured |
| 2 | `sockets/chat.py` — imports non-existent `TeamNamespace` | **MITIGATED** — dead code, not imported |
| 3 | `auth.py` — register resets existing user passwords | **FIXED** — checks email uniqueness |
| 4 | `auth.py` — `join_with_code()` email collision | **FIXED** — UUID suffix generates unique emails |
| 5 | `diplomacy.py` — socket emit missing namespace | **FIXED** — `namespace="/team"` specified |
| 6 | `resolution.py` — uses `baseline_security` instead of `current_security` | **FIXED** — uses dynamic stats |
| 7 | `round_manager.py` — timer hardcodes 360s | **FIXED** — reads `ROUND_DURATIONS` from config |
| 8 | `client/.env.example` — port 5000 vs 5050 mismatch | **FIXED** — port is 5050 |
| 9 | `actions.py` — `NUKE_LOCK` decorative only | **FIXED** — now toggles `GlobalState.nuke_unlocked` |

### Current Issues

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | **HIGH** | `api/wsgi.py` | Uses Werkzeug dev server with `allow_unsafe_werkzeug=True` in production Docker. No Gunicorn. Single-threaded, not designed for concurrent load |
| 2 | **HIGH** | `api/Dockerfile` | Runs as root. No `USER` directive for non-root execution |
| 3 | **HIGH** | `api/.env.docker` | `CORS_ORIGINS=*` — wildcard CORS unsafe for production deployment |
| 4 | **MEDIUM** | `api/.env.docker` | `SECRET_KEY` committed to git. Should use external secret management |
| 5 | **MEDIUM** | `api/requirements.txt` | `anthropic` dependency has no version pin — could break with major updates |
| 6 | **MEDIUM** | `api/sockets/chat.py` | Dead/broken code (imports non-existent `TeamNamespace`). Not imported anywhere but should be removed |
| 7 | **MEDIUM** | `api/app/routes/game.py:214-215` | Dead code branch: `pending` count is queried but never used |
| 8 | **LOW** | `docs/default_admin_credentials.md` | GM password `ChangeMe123!` visible in docs. Must change before live event |
| 9 | **LOW** | `client/public/vite.svg` | Default Vite favicon, not Cyber War Room themed |
| 10 | **LOW** | `api/scripts/run_ai_sim.py` | Runs on every Docker container startup (no idempotency guard) |

---

## Architectural Concerns

1. **In-memory timer state** — `RoundManager` is a module-level singleton holding timer state in memory. State is lost on restart and not shared across workers. Multi-process deployment will break.
2. **No Alembic migrations** — Schema changes via raw `ALTER TABLE` DDL on startup. Acceptable for PoC/SQLite but fragile for production.
3. **Duplicate round management** — Both `rounds.py:get_active_round()` and `round_manager.py:current_round()` create/manage rounds with different side effects. Risk of inconsistent state.
4. **Monolithic frontend** — All **1,766 lines** in `App.tsx`. 17 inline components, all state in root. No code splitting, no error boundaries, no state management library.
5. **No production WSGI server** — Backend uses Flask dev server in Docker. Needs Gunicorn + eventlet for production Socket.IO support.
6. **No CSRF protection** — Session-based auth with cookies but no CSRF tokens on mutations.
7. **Synchronous LLM calls** — World Engine LLM call blocks the resolution pipeline. No async job queue.
8. **No rate limiting** — No rate limiting on any endpoint (registration, login, proposals, chat).

---

## Outstanding Work — Priority Order

### P0 — Must Fix (Blocking Production Deployment)

- [ ] Replace Werkzeug dev server with Gunicorn + eventlet in Docker
- [ ] Add non-root USER to backend Dockerfile
- [ ] Restrict `CORS_ORIGINS` to specific domain(s) in production
- [ ] Move `SECRET_KEY` out of git (use env secrets or Azure Key Vault)
- [ ] Pin `anthropic` package version in requirements.txt
- [ ] Change default GM password for production

### P1 — Core Gameplay Gaps

- [ ] Implement Mega Challenge route and UI
- [ ] Implement Phone-a-Friend lifeline logic and UI
- [ ] Add captain override modal when proposals are missing at round end
- [ ] Add self-targeting prevention in target validation
- [ ] Add deterministic RNG seeding per round for reproducibility
- [ ] Add explicit state machine transitions (`close_submissions`, `publish_results`)

### P2 — Real-Time & UX

- [ ] Add `/gm` and `/leaderboard` socket namespaces per plan
- [ ] Implement typing indicators in chat
- [ ] Colour-code chat senders by role (player vs advisor vs GM)
- [ ] Add toast/notification system for GM announcements
- [ ] Add diplomacy accept/decline invitation flow
- [ ] Add session kick on duplicate login
- [ ] Add roster/teammate list widget
- [ ] Add unread badges in chat
- [ ] Add collapsible chat for small screens
- [ ] Add quick-share widgets for intel/lifeline trades

### P3 — Leaderboard & World Engine

- [ ] Build multi-nation escalation line chart (currently single line)
- [ ] Add Cyber Impact list (who attacked whom)
- [ ] Add async job queue for LLM World Engine calls
- [ ] Add intel drop solve / false flag events to news ticker
- [ ] Add LLM narrative queue with manual re-run option
- [ ] Add escalation threshold background colour shift

### P4 — AI Shadow Game & Reveal

- [ ] Implement real AI simulation runner with LLM agents
- [ ] Build proper reveal screen with side-by-side comparison graphs
- [ ] Add AI quote carousel for reveal
- [ ] Connect reveal data API to real AI simulation results
- [ ] Remove random-number stub from `run_ai_sim.py`

### P5 — Visual Polish & Theme

- [ ] Add advisor portraits that react to outcomes
- [ ] Replace default Vite favicon with custom Cyber War Room icon
- [ ] Refactor `App.tsx` into separate component files
- [ ] Add per-action advisory hints from advisor metadata
- [ ] Add status chips (Submissions Open / Resolving / Results Ready)
- [ ] Add "resources insufficient" / "target required" validation indicators

### P6 — Testing & Infrastructure

- [ ] Write tests for admin routes (round management, crisis injection, game reset)
- [ ] Write tests for team assignment race conditions
- [ ] Write tests for leaderboard scoring
- [ ] Set up Playwright test config; convert `playwright_login.mjs` to proper test
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Remove dead code (`sockets/chat.py`, `game.py:214-215` dead branch)
- [ ] Add rate limiting on registration and login endpoints
- [ ] Update stale `api/README.md`
- [ ] Replace `client/README.md` template with project docs

### P7 — Asset Pack

- [ ] Create 3 cipher PDFs (Vigenere, substitution, XOR) with answer keys
- [ ] Create 2 stego images (hidden base64 text, LSB message)
- [ ] Create False Flag briefing card
- [ ] Create Phone-a-Friend hint sheet
- [ ] Implement GM asset manager for intel drops

---

## Remaining Work Summary

**Still TODO (42 items):**

**P0 — Deployment Blockers (6):** Gunicorn, non-root Docker, CORS restriction, secret management, pin anthropic version, change GM password

**P1 — Gameplay (6):** Mega Challenge, Phone-a-Friend, captain override, self-target prevention, deterministic RNG, state machine transitions

**P2 — Real-Time/UX (10):** Socket namespaces, typing indicators, chat colours, toast system, diplomacy accept/decline, session kick, roster, unread badges, collapsible chat, quick-share widgets

**P3 — Leaderboard/Engine (6):** Multi-nation chart, Cyber Impact list, async LLM queue, ticker events, narrative queue, escalation colour shift

**P4 — AI Shadow Game (5):** Real AI runner, side-by-side reveal, AI quote carousel, real reveal data, remove random stub

**P5 — Polish (6):** Advisor portraits, custom favicon, refactor App.tsx, advisory hints, status chips, validation indicators

**P6 — Testing/Infra (9):** Admin tests, team assignment tests, leaderboard tests, Playwright config, CI/CD, dead code removal, rate limiting, update READMEs

**P7 — Assets (5):** Cipher PDFs, stego images, False Flag card, Phone-a-Friend sheet, asset manager

---

## Files Summary

### Backend (33 Python files, ~3,762 lines total)

| File | Lines | Status |
|------|-------|--------|
| `app/__init__.py` | ~89 | Working, `async_mode="threading"` |
| `app/models.py` | ~257 | Complete (19+ models including OutcomeScoreHistory) |
| `app/config.py` | ~70 | Complete, ROUND_DURATIONS properly parsed |
| `app/extensions.py` | ~27 | Working |
| `app/routes/__init__.py` | ~26 | Clean — registers health, auth, game, reveal, admin, diplomacy |
| `app/routes/auth.py` | ~180 | Working, bugs fixed |
| `app/routes/game.py` | ~601 | Most complete file, minor dead code (line 214-215) |
| `app/routes/admin.py` | ~218 | Working, includes game reset, intel CRUD, doom clear |
| `app/routes/diplomacy.py` | ~113 | Working, namespace bug fixed |
| `app/routes/reveal.py` | ~58 | Returns AI sim results (doom-locked or GM-only) |
| `app/routes/health.py` | ~11 | Minimal but working |
| `app/services/round_manager.py` | ~270 | Working, respects ROUND_DURATIONS |
| `app/services/resolution.py` | ~261 | Working, uses current_security |
| `app/services/world_engine.py` | ~75 | **LLM integration (Anthropic Claude Sonnet 4) + template fallback** |
| `app/services/game_reset.py` | ~74 | **NEW** — full game state reset |
| `app/services/proposals.py` | ~47 | Clean |
| `app/services/alliances.py` | ~49 | Clean |
| `app/services/crisis.py` | ~80 | Working |
| `app/services/global_state.py` | ~139 | Working, doom/clear_doom, escalation thresholds |
| `app/services/leaderboard.py` | ~25 | Clean |
| `app/services/lifelines.py` | ~49 | Clean |
| `app/services/rounds.py` | ~45 | Working, overlaps with round_manager |
| `app/services/schema.py` | ~52 | Ad-hoc migrations |
| `app/services/team_assignment.py` | ~45 | Working, SQLite-specific |
| `app/services/chat/__init__.py` | ~19 | Capped deque buffer |
| `app/data/actions.py` | ~286 | Complete — 32 actions |
| `app/data/crises.py` | ~42 | 3 crises defined |
| `app/data/ai_reveal.py` | ~30 | Static sample data |
| `app/seeds/team_data.py` | ~113 | Complete — 11 teams |
| `app/sockets/__init__.py` | ~10 | Essentially empty |
| `app/sockets/chat.py` | ~30 | Dead/broken code (imports non-existent class) |
| `app/sockets/chat_events.py` | ~36 | Working |
| `app/utils/passwords.py` | ~24 | Clean |
| `scripts/seed_db.py` | ~70 | Working |
| `scripts/run_ai_sim.py` | ~48 | Random-number stub |
| `wsgi.py` | ~13 | Working (dev server only) |

### Frontend (8 source files, ~2,221 lines total)

| File | Lines | Status |
|------|-------|--------|
| `src/App.tsx` | ~1,766 | Monolithic but functional. 17 inline components |
| `src/main.tsx` | ~10 | Standard entry point |
| `src/hooks/useChat.ts` | ~39 | Working |
| `src/hooks/useRoundTimer.ts` | ~89 | Working with interpolation |
| `src/lib/api.ts` | ~291 | 29 API functions, comprehensive |
| `src/lib/socket.ts` | ~26 | Working, polling + WebSocket transport |
| `src/App.css` | ~103 | CRT effects, animations (marquee, flicker, shake, pulse) |
| `src/index.css` | ~22 | Fonts + Tailwind directives |

### Tests (3 files, 11 test functions)

| File | Tests | Coverage |
|------|-------|----------|
| `api/tests/test_auth.py` | 7 | Register, duplicate, login, invalid password, me, missing fields, logout |
| `api/tests/test_game.py` | 4 | Actions list, leaderboard, news, game state |
| `api/tests/socket_chat_test.py` | 1 | Chat message persistence |

### Dependencies

**Backend (`requirements.txt`):**
flask, flask-socketio, flask-login, flask-sqlalchemy, flask-cors, sqlalchemy, python-dotenv, simple-websocket, werkzeug, anthropic, pytest, pytest-flask

**Frontend (`package.json`):**
react 19.2.0, react-dom, socket.io-client 4.8.3, recharts 3.7.0, tailwindcss 3.4.12, vite 7.3.1, typescript 5.9.3

---

## Comparison: AUDIT.md vs AUDIT2.md

| Metric | AUDIT.md (post-fix) | AUDIT2.md | Delta |
|--------|---------------------|-----------|-------|
| Overall completion | ~65% | ~67% | +2% |
| Phase 1 | ~85% | ~88% | +3% |
| Phase 2 | ~75% | ~78% | +3% |
| Phase 3 | ~60% | ~62% | +2% |
| Phase 4 | ~70% | ~80% | +10% |
| Phase 5 | ~35% | ~40% | +5% |
| Phase 6 | ~20% | ~35% | +15% |
| Backend files | 30 | 33 | +3 |
| Backend lines | ~2,800 est | ~3,762 | +~960 |
| Frontend lines | ~1,491 (App.tsx) | ~2,221 total | +~730 |
| Test functions | ~1 | 11 | +10 |
| Actions defined | 17 | 32 | +15 |
| Critical bugs | 12 | 10 | -2 (9 fixed, 10 new) |
| Outstanding items | 22 | 42 | +20 (more granular tracking) |

**Biggest improvements since first audit:** World Engine LLM integration (+10% Phase 4), Docker infrastructure (+15% Phase 6), action catalog completion, test coverage, game reset functionality.

**Biggest remaining gaps:** AI shadow game (still random numbers), Mega Challenge (zero implementation), production deployment hardening (no Gunicorn, root Docker, wildcard CORS), frontend monolith, missing UX features (typing, toasts, diplomacy flow).
