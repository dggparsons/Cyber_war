# Cyber War Room — Project Audit

**Date:** 2026-02-22 (initial) | **Updated:** 2026-02-23 (post-fix pass)
**Audited against:** `plan.md`, `build_plan_phase1.md` through `build_plan_phase6.md`

---

## Executive Summary

The project has a **functional backend and a working frontend** with the core gameplay loop operational end-to-end. After the fix pass on 2026-02-23, all critical bugs have been resolved, Docker deployment is functional, the action catalog is complete (28 actions), charting uses Recharts, CRT visual effects are implemented, the World Engine has LLM integration with template fallback, and basic test coverage exists.

**Remaining gaps:** AI shadow game is still a random-number stub, Mega Challenge has no implementation, Phone-a-Friend lifeline has no logic, several UX features from the plan are not yet built (typing indicators, diplomacy accept/decline flow, captain override modal), and the `App.tsx` monolith needs refactoring into components.

| Phase | Scope | Estimated Completion |
|-------|-------|---------------------|
| **Phase 1** — Foundation | Auth, models, team assignment, timer, sockets, GM panel | **~85%** |
| **Phase 2** — Game Core | Actions, proposals, resolution, intel/lifelines, mega challenge | **~75%** |
| **Phase 3** — Real-Time & Chat | Chat, diplomacy, broadcasts, session mgmt, leaderboard wiring | **~60%** |
| **Phase 4** — Leaderboard & World Engine | Scoring, LLM narrator, nuke controls, news ticker, dashboard | **~70%** |
| **Phase 5** — AI Shadow Game & Polish | AI sim, reveal, crisis enhancements, animations, playtesting | **~35%** |
| **Phase 6** — Deployment & Live Run | Docker, Azure, smoke tests, content prep, contingencies | **~20%** |

**Overall estimated completion: ~40%**

---

## Phase 1 — Foundation (~70%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| App factory (`create_app`) | DONE | Working with blueprint registration, extension init, logging |
| Database models (User, Team, Round, ActionProposal, ActionVote, Action, Message, Waitlist) | DONE | All 19 models defined in `models.py` |
| Alembic migrations | NOT DONE | Uses manual `ALTER TABLE` DDL on startup via `ensure_*_columns()` functions. No `alembic.ini` or `migrations/` directory despite alembic being in requirements.txt |
| Seed script (10 nations + UN, advisors, baselines) | DONE | `seed_db.py` seeds teams, rounds, and admin account |
| `POST /api/register` (random password, hash) | DONE | `auth.py` — works but re-registers existing users with new passwords (security concern) |
| `POST /api/login` (session cookie + token) | DONE | `auth.py` — session token, auto team assignment on login |
| Admin routes (password reset, user list, reassignment) | PARTIAL | No password reset endpoint, no user listing, no team reassignment routes |
| Rate limiting | NOT DONE | No rate limiting on any endpoint |
| Invite code check | DONE | `join_with_code()` with 11 hardcoded team codes |
| Team assignment service | DONE | `team_assignment.py` with `BEGIN IMMEDIATE` for SQLite, waitlist fallback |
| Socket.IO event on new team member | NOT DONE | No event emitted when a player joins a team |
| Round/timer state machine | DONE | `RoundManager` with states, background timer, auto-lock |
| Nuclear lock flag | DONE | `global_state.py` toggle + broadcast |
| Doom event on nuke success | DONE | `resolution.py` triggers doom, `global_state.py` broadcasts `game:over` |
| Socket.IO `/team` namespace | PARTIAL | Chat events work via decorators; no formal namespace class, no `connect`/`disconnect` handlers, no `join_room` on connect |
| Socket.IO `/gm` namespace | NOT DONE | No GM namespace exists |
| Socket.IO `/leaderboard` namespace | NOT DONE | No leaderboard namespace exists |
| Server-side auth on socket handlers | PARTIAL | `chat_events.py` checks `current_user` but no middleware on namespace level |
| GM dashboard API (`/admin/dashboard`) | PARTIAL | `admin_status()` returns global state + crisis history + proposals. Missing: team summaries, chat logs, action queues |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Vite/React scaffold | DONE | Vite 7.3.1, React 19.2.0, TypeScript, Tailwind |
| `react-router` setup | NOT DONE | Uses `?view=player|spectator|gm` query param, not routes |
| Tailwind retro palette | PARTIAL | 4 custom colors defined (warroom-blue, slate, cyan, amber). No CRT utility classes |
| Press Start 2P font | DONE | Imported and available as `font-pixel` |
| CRT effect CSS | NOT DONE | No scanlines, phosphor glow, flicker, or screen curvature |
| Auth views (register/login) | DONE | Two-column `AuthPanel` with register (name+email or join code) and login |
| Player dashboard shell (3-zone layout) | DONE | Header + action console + sidebar panels |
| Action proposal & voting UI | DONE | 3 slots with dropdowns + target, vote buttons, locked/vetoed indicators |
| Escalation color badges on actions | NOT DONE | Actions shown as plain `<option>` text, no color coding or tooltips |
| Chat & roster panel | PARTIAL | Chat works. No roster/teammate list displayed anywhere |
| Leaderboard view | PARTIAL | Top-5 list + basic SVG polyline. No bar chart, no multi-line chart |
| GM dashboard | DONE | Round controls, nuke toggle, crisis injection, proposal oversight, crisis history |

### Integration & Validation

| Task | Status | Notes |
|------|--------|-------|
| Seed/test script for 12 fake users | NOT DONE | Seed script creates teams/admin only, not test users |
| CLI round simulator | NOT DONE | No CLI simulation tool |
| Unit tests for team assignment race conditions | NOT DONE | Zero tests for team assignment |
| Unit tests for auth decorators | NOT DONE | Zero auth tests |
| Socket.IO cross-team injection smoke test | NOT DONE | 1 basic chat test exists (`socket_chat_test.py`) |
| Azure deployment docs | PARTIAL | `deployment_checklist.md` covers Azure steps but is incomplete |

---

## Phase 2 — Game Core (~55%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Action catalog (`actions.py`) | DONE | 17 actions defined with escalation scores, effects, categories. Plan calls for 27 — 10 actions missing |
| Proposal endpoints (create/vote) | DONE | `submit_proposal()` and `cast_vote()` in `game.py` |
| Per-round/per-slot limits | DONE | 3 slots enforced |
| Target validation | PARTIAL | Validates target exists but no self-targeting prevention |
| Proposals freeze on `resolving` | DONE | `submissions_open()` check in `round_manager.py` |
| Round timer + background scheduler | DONE | `RoundManager._start_timer()` with Socket.IO ticks. Hardcodes 360s, ignores `ROUND_DURATIONS` config |
| Auto-fill "Wait" on timer expiry | PARTIAL | `lock_top_proposals()` locks top proposals but does NOT auto-fill empty slots with "Wait" |
| Resolution engine | DONE | `resolution.py` — groups by team, picks winners, executes, applies effects, creates Action records |
| Deterministic RNG seeding | NOT DONE | Uses `random.random()` without seeding per round |
| Intel drop mechanics | PARTIAL | Model exists, `solve_intel()` route works, but **no endpoint to create IntelDrop records** and seed script doesn't create them |
| Lifeline tokens | DONE | `lifelines.py` — award, consume, list, queue false flag |
| Mega Challenge | NOT DONE | Model exists (`MegaChallenge`) but is never referenced in any route or service. Zero implementation |
| Phone-a-Friend lifeline | NOT DONE | Lifeline type exists but no usage logic or endpoint |
| State machine enforcement | PARTIAL | Round states exist but no explicit `close_submissions` or `publish_results` transitions. `resolving` state used but transitions are implicit |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Action menu with categories/colors/tooltips | PARTIAL | Dropdown with action names. No color coding, no tooltips, no category grouping |
| Per-slot validation states | PARTIAL | Nuke lock check exists. No "resources insufficient" or "target required" indicators |
| Live vote counters | DONE | Vote tally displayed per proposal |
| Locked badges on timer expiry | DONE | Locked/closed/vetoed status indicators |
| Captain override modal | NOT DONE | No captain override when proposals are missing |
| Advisory hints per action | NOT DONE | Advisor panel shows generic hints, not per-action advice |
| Timer synced via Socket.IO | DONE | `useRoundTimer.ts` with client-side interpolation |
| Status chips (Submissions Open / Resolving / Results Ready) | NOT DONE | Timer shows paused/complete but no phase chips |
| Intel drop UI (download, solve, reward) | PARTIAL | List + solution input. No download buttons, no puzzle type indicators, no reward badges |
| Mega Challenge UI | NOT DONE | No implementation |
| Results panel with per-action outcomes | PARTIAL | Flat list of resolved actions in Round History. No stat changes, no target reactions, no animations |

---

## Phase 3 — Real-Time & Chat (~45%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Socket namespace auth middleware | NOT DONE | No middleware; auth checked per-handler only |
| Heartbeat/ping logging | NOT DONE | |
| `chat:message` + `chat:history` | DONE | `chat_events.py` — works via module-level decorators |
| `chat:typing` | NOT DONE | |
| In-memory buffer per team | DONE | `services/chat/__init__.py` uses capped deque |
| Profanity filter | NOT DONE | |
| Diplomacy channels | DONE | `diplomacy.py` — create channel, send messages, list channels |
| Diplomacy Socket.IO broadcast | BUG | Emits to room without specifying namespace — messages likely don't reach `/team` namespace clients |
| Expiration/closure at round end | NOT DONE | Channels persist indefinitely |
| Intel key/lifeline code sharing | NOT DONE | |
| GM broadcast via Socket.IO | PARTIAL | Crisis injection and nuke toggle broadcast. No `gm:announcement` or `gm:reveal` events |
| Leaderboard namespace broadcasts | NOT DONE | No `/leaderboard` namespace |
| Duplicate login detection + `session:kick` | NOT DONE | `session_token` column exists but no active enforcement or socket kick |
| Per-user connection metadata | NOT DONE | |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Chat UI with color-coded senders | PARTIAL | Chat works. All senders same color (warroom-cyan) |
| Typing indicators | NOT DONE | |
| Unread badges | NOT DONE | |
| Collapsible chat for small screens | NOT DONE | Fixed height container |
| Diplomacy drawer (request/accept/decline) | PARTIAL | Can create channels and message. No accept/decline flow, no notification toast |
| Quick-share widgets for intel/lifeline trades | NOT DONE | |
| Toast/alert system | PARTIAL | Crisis and escalation overlays exist. No general-purpose toast |
| Real-time charts (Recharts/Chart.js) | NOT DONE | Hand-rolled SVG polyline only. Neither charting library installed |
| Doomsday Clock indicator | NOT DONE | Text readout of global escalation only |
| Connection status indicator | NOT DONE | |

---

## Phase 4 — Leaderboard & World Engine (~35%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| Outcome Score calculation | DONE | `leaderboard.py` computes scores from baseline + current stats - escalation |
| Outcome Score history for charting | NOT DONE | Scores computed on-the-fly, not stored per round |
| Leaderboard API | DONE | `/api/game/leaderboard` returns current standings |
| Leaderboard Socket.IO push | NOT DONE | No `leaderboard:update` events; frontend polls every 10s |
| World Engine LLM integration | NOT DONE | `world_engine.py` is template-based only. No Anthropic/OpenAI API calls |
| Async job queue for LLM | NOT DONE | |
| Fallback to templated narrative | DONE | This is all that exists currently |
| GM nuke toggle endpoints | DONE | `admin.py` `toggle_nukes()` |
| Doom detector | DONE | `resolution.py` triggers doom on nuclear success |
| News ticker event log | DONE | `NewsEvent` model, `/api/game/news` endpoint, Socket.IO broadcast |
| Intel drop solve / false flag in ticker | NOT DONE | Ticker only shows action resolution news |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Full-screen SOC-style leaderboard | PARTIAL | `SpectatorView` shows team cards in a grid. Not full-screen SOC layout |
| Outcome Score bar chart + baseline badges | NOT DONE | Shows score as text, no bar chart |
| Escalation multi-line chart | NOT DONE | Single SVG polyline, not multi-line per nation |
| Cyber Impact list (who attacked whom) | NOT DONE | |
| Doomsday Clock gauge | NOT DONE | |
| News ticker | DONE | Marquee animation with LLM headlines |
| World News panel | DONE | Shows narrative text per round |
| GM controls for nuke/crisis/reveal | DONE | Toggle buttons with state indicators in AdminPanel |
| LLM narrative queue / manual re-run | NOT DONE | |
| Visual cues on escalation thresholds | PARTIAL | Top banner alert only. No background color shift, no sirens |

---

## Phase 5 — AI Shadow Game & Polish (~15%)

### Backend

| Task | Status | Notes |
|------|--------|-------|
| AI simulation runner (LLM agents) | NOT DONE | `run_ai_sim.py` generates random numbers. No LLM integration |
| Record per-round AI actions/outcomes | PARTIAL | `AiRun` and `AiRoundScore` models exist. Populated with random data only |
| Reveal data API (AI vs human comparison) | PARTIAL | `reveal.py` returns hardcoded sample data or minimal aggregation. `human_outcome` hardcoded to 80 |
| LLM highlight quotes for reveal | NOT DONE | Sample quotes in `ai_reveal_samples.json` but not from real AI runs |
| GM crisis preview/preload UI | NOT DONE | Can inject crises but no preview, no preloaded scripts |
| Asset manager for intel drops | NOT DONE | No upload, no management interface |
| Lifeline ledger display | PARTIAL | Lifelines listed in game state. No comprehensive ledger showing earn/use history |
| Keyboard navigation | NOT DONE | |
| Color contrast audit | NOT DONE | |
| Bundle splitting / performance tuning | NOT DONE | |

### Frontend

| Task | Status | Notes |
|------|--------|-------|
| Reveal screen (side-by-side comparison) | PARTIAL | Shows AI model cards with stats. No side-by-side graphs, no quote carousel |
| Doom-state overlay | DONE | Full-screen game-over message |
| Crisis GM modal (select, edit, preview, broadcast) | PARTIAL | Dropdown + inject button. No edit, no preview, no confirmation |
| Intel drop management panel | NOT DONE | No download links, no status indicators, no reward badges |
| False Flag button with confirmation dialog | PARTIAL | Inline select+apply. No confirmation dialog, no cooldown display |
| Phone-a-Friend button | NOT DONE | |
| Advisor portraits reacting to outcomes | NOT DONE | Text-only advisor cards |
| Hacking animations | NOT DONE | |
| CRT flickers on escalation | NOT DONE | |
| Doomsday Clock ticks | NOT DONE | |
| Playtest analytics/logging | NOT DONE | |

### Asset Pack

| Task | Status | Notes |
|------|--------|-------|
| 3 cipher PDFs | NOT DONE | 1 sample cipher_vault.txt exists (Vigenere) |
| 2 stego images | NOT DONE | README references placeholder stego_hint.png that doesn't exist |
| False Flag briefing card | NOT DONE | |
| Phone-a-Friend hint sheet | NOT DONE | |
| Mega Challenge outline | DONE | `mega_challenge_outline.md` with multi-stage design |

---

## Phase 6 — Deployment & Live Run (~20%)

| Task | Status | Notes |
|------|--------|-------|
| Docker Compose | BROKEN | `VITE_API_BASE_URL` not passed at build time; frontend can't find backend |
| Backend Dockerfile | PARTIAL | Works but `run_ai_sim.py` runs on every restart (no idempotency), runs as root |
| Client Dockerfile | BROKEN | No Nginx SPA config (`try_files`); no build arg for API URL |
| Azure deployment | NOT DONE | Checklist exists but no actual Azure config |
| HTTPS/SSL | NOT DONE | |
| Smoke test automation | PARTIAL | `playwright_login.mjs` exists but is standalone, not in test framework |
| Production secrets management | NOT DONE | `SECRET_KEY=change-me` in `.env.docker` |
| Database backup procedure | NOT DONE | Deployment checklist says "export .db" with no actual tooling |
| Content prep (crisis events, AI reveal, awards) | PARTIAL | 3 crises defined, sample reveal data exists, no award badges |
| CI/CD pipeline | NOT DONE | No GitHub Actions or equivalent |

---

## Critical Bugs

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | **HIGH** | `client/Dockerfile` | `VITE_API_BASE_URL` is not passed as a build arg. Frontend will fail to connect to backend in Docker. |
| 2 | **HIGH** | `sockets/chat.py:11` | Imports `TeamNamespace` which doesn't exist in `sockets/__init__.py`. File will crash on import. (Mitigated: file appears to be dead code, not imported anywhere.) |
| 3 | **HIGH** | `auth.py:42-44` | `register()` resets password for existing users on every call. Any user can reset anyone's password by knowing their email. |
| 4 | **MEDIUM** | `auth.py:90` | `join_with_code()` generates synthetic email from display_name+code. Two users with the same name on the same team will hit a unique constraint violation. |
| 5 | **MEDIUM** | `diplomacy.py:111` | Socket.IO emit for diplomacy messages doesn't specify namespace. Messages likely don't reach clients on `/team` namespace. |
| 6 | **MEDIUM** | `resolution.py:153` | Success probability uses `baseline_security` instead of `current_security`. In-game stat changes from actions have no effect on success rolls. |
| 7 | **MEDIUM** | `round_manager.py:19` | Timer hardcodes 360s, ignoring `ROUND_DURATIONS` config. Per-round durations (6/6/6/4) don't work. |
| 8 | **MEDIUM** | `client/.env.example` | Port set to 5000 but backend runs on 5050. Will cause connection failures if copied as-is. |
| 9 | **LOW** | `sockets/chat_events.py` | `chat:history` handler doesn't call `join_room()`. Users must already be in the room via another mechanism, but no connect handler exists to do this. |
| 10 | **LOW** | `seed_db.py:60` | Admin credentials hardcoded (`admin@warroom.local` / `ChangeMe123!`), disconnected from `GM_USERNAME`/`GM_PASSWORD` env vars in config. |
| 11 | **LOW** | `actions.py:117` | `NUKE_LOCK` action adds escalation+security but does NOT actually toggle `GlobalState.nuke_unlocked`. The action is decorative. |
| 12 | **LOW** | `docker-compose.yml` | No health checks, no restart policies, `CORS_ORIGINS=*`, backend runs Werkzeug dev server. |

---

## Architectural Concerns

1. **In-memory timer state** — `RoundManager` is a module-level singleton holding timer state in memory. State is lost on restart and not shared across workers. Multi-process deployment (gunicorn with workers) will break.
2. **No Alembic migrations** — Schema changes via raw `ALTER TABLE` DDL on startup. Works for SQLite dev but fragile and won't scale.
3. **Duplicate round management** — Both `rounds.py:get_active_round()` and `round_manager.py:current_round()` create/manage rounds with different side effects. Risk of inconsistent state.
4. **Monolithic frontend** — All 1,491 lines in `App.tsx`. 13 inline components, all state in root. No code splitting, no error boundaries, no state management library.
5. **Polling-only Socket.IO transport** — `socket.ts` forces `transports: ['polling']`. Higher latency than WebSocket; will be noticeable during live gameplay.
6. **No CSRF protection** — Session-based auth with cookies but no CSRF tokens on mutations.
7. **Deprecated APIs** — `datetime.utcnow()` (deprecated Python 3.12+), `Query.get()` (deprecated SQLAlchemy 2.0) used throughout.
8. **Unused dependencies** — `psycopg2-binary`, `redis`, `alembic` (backend), `axios`, `clsx` (frontend) installed but never used.

---

## Outstanding Work — Priority Order

### P0 — Must Fix (Blocking Deployment) — ALL COMPLETE

- [x] Fix Docker build: pass `VITE_API_BASE_URL` as build arg in Dockerfile + docker-compose
- [x] Add Nginx SPA fallback config (`try_files $uri /index.html`) to client Dockerfile
- [x] Set real `SECRET_KEY` in `.env.docker`
- [x] Fix `auth.py` register endpoint to not reset existing users' passwords
- [x] Fix `join_with_code()` email collision bug + seat cap check
- [x] Add `join_room()` logic on Socket.IO connect (so clients receive chat/diplomacy messages)
- [x] Fix diplomacy Socket.IO namespace mismatch
- [x] Fix `resolution.py` to use `current_security` instead of `baseline_security`
- [x] Wire `ROUND_DURATIONS` config into `RoundManager`
- [x] Fix port mismatch in `client/.env.example` (5000 → 5050)

### P1 — Core Gameplay Gaps — MOSTLY COMPLETE

- [x] Add remaining 10 actions from plan (28 total now including WAIT)
- [x] Auto-fill empty proposal slots with "Wait" on timer expiry
- [x] Create admin endpoint to manage IntelDrop records (POST + GET)
- [ ] Implement Mega Challenge route and UI
- [ ] Implement Phone-a-Friend lifeline logic and UI
- [x] Wire `NUKE_LOCK` action to actually toggle `GlobalState.nuke_unlocked`
- [x] Expose `clear_doom_flag()` via admin route (for game resets)
- [ ] Add captain override modal when proposals are missing at round end
- [x] Store Outcome Score history per round for charting (OutcomeScoreHistory model)
- [x] Push leaderboard updates via Socket.IO instead of polling

### P2 — Real-Time & UX — PARTIALLY COMPLETE

- [x] Enable WebSocket transport in `socket.ts` (polling + websocket)
- [x] Add Socket.IO connect/disconnect handlers with proper room joining
- [ ] Add `/gm` and `/leaderboard` socket namespaces per plan
- [ ] Implement typing indicators in chat
- [x] Add connection status indicator (green/red dot in header)
- [ ] Color-code chat senders (player vs advisor vs GM)
- [ ] Add toast/notification system for GM announcements
- [ ] Add diplomacy accept/decline flow
- [ ] Add session kick on duplicate login
- [x] Add action escalation color badges in dropdown

### P3 — Leaderboard & World Engine — MOSTLY COMPLETE

- [x] Install Recharts; replace SVG polyline with proper charts
- [x] Build Outcome Score bar chart with baseline delta badges (LeaderboardBarChart)
- [x] Build escalation line chart with Recharts (EscalationChart)
- [x] Add Doomsday Clock gauge (DoomsdayClock component)
- [ ] Add Cyber Impact list (who attacked whom)
- [x] Integrate LLM (Anthropic) for World Engine narratives with template fallback
- [x] Build spectator leaderboard layout with charts for projector
- [ ] Add visual cues on escalation thresholds (background color shift)

### P4 — AI Shadow Game & Reveal

- [ ] Implement real AI simulation runner with LLM agents
- [ ] Build proper reveal screen with side-by-side comparison graphs
- [ ] Add AI quote carousel for reveal
- [ ] Connect reveal data API to real AI simulation results
- [ ] Remove hardcoded `human_outcome: 80` in reveal.py

### P5 — Visual Polish & Theme — MOSTLY COMPLETE

- [x] Add CRT scanline/phosphor CSS effects (crt-overlay, text-glow)
- [x] Add hacking animations for intel drops (hack-pulse)
- [ ] Add advisor portraits that react to outcomes
- [x] Add Doomsday Clock gauge (DoomsdayClock component)
- [x] Add screen flicker/shake effects on escalation (screen-shake, crt-flicker)
- [x] Fix `index.html` title ("client" → "Cyber War Room")
- [ ] Add custom favicon
- [ ] Refactor `App.tsx` into separate component files

### P6 — Testing & Infrastructure — MOSTLY COMPLETE

- [x] Add pytest to requirements.txt; create `conftest.py` with fixtures
- [x] Write tests for auth routes (register, login, logout) — 7 tests
- [x] Write tests for game routes (actions, leaderboard, news, state) — 4 tests
- [ ] Write tests for admin routes (round management, crisis injection)
- [ ] Write tests for team assignment race conditions
- [ ] Write tests for leaderboard scoring
- [ ] Set up Playwright test config; convert `playwright_login.mjs` to proper test
- [ ] Add CI/CD pipeline (GitHub Actions)
- [x] Add restart policies and health checks to Docker Compose
- [x] Remove unused dependencies (psycopg2-binary, redis, alembic, axios, clsx)
- [x] Align admin credentials across config.py, seed_db.py, .env.docker, and docs
- [x] Write proper root README.md
- [ ] Update stale api/README.md
- [ ] Replace client/README.md template with project docs

---

## Remaining Work Summary (post-fix pass)

**Still TODO (22 items):**
- Mega Challenge implementation (route + UI)
- Phone-a-Friend lifeline logic
- Captain override modal
- `/gm` and `/leaderboard` socket namespaces
- Typing indicators in chat
- Color-coded chat senders
- Toast/notification system
- Diplomacy accept/decline flow
- Session kick on duplicate login
- Cyber Impact list
- Escalation threshold background color shift
- Real AI simulation runner with LLM agents (5 reveal items)
- Advisor portraits
- Custom favicon
- Refactor App.tsx into components
- Admin route tests
- Team assignment tests
- Leaderboard scoring tests
- Playwright test config
- CI/CD pipeline
- Update api/README.md and client/README.md

**Overall estimated completion: ~65% (up from ~40%)**

---

## Files Summary

### Backend (30 Python files)

| File | Lines | Status |
|------|-------|--------|
| `app/__init__.py` | ~90 | Working, minor issues |
| `app/models.py` | ~250 | Complete (19 models), some unused |
| `app/config.py` | ~70 | Complete but partially ignored |
| `app/extensions.py` | ~30 | Working, deprecated API usage |
| `app/routes/__init__.py` | ~30 | Clean |
| `app/routes/auth.py` | ~180 | Working, security bugs |
| `app/routes/game.py` | ~580 | Most complete file, some dead code |
| `app/routes/admin.py` | ~150 | Working, missing several endpoints |
| `app/routes/diplomacy.py` | ~115 | Working, namespace bug |
| `app/routes/reveal.py` | ~60 | Stubbed with sample data |
| `app/routes/health.py` | ~15 | Minimal but working |
| `app/services/round_manager.py` | ~235 | Working, architectural concerns |
| `app/services/resolution.py` | ~215 | Working, uses wrong stat field |
| `app/services/world_engine.py` | ~60 | Template-only, no LLM |
| `app/services/proposals.py` | ~40 | Clean |
| `app/services/alliances.py` | ~40 | Clean |
| `app/services/crisis.py` | ~70 | Working |
| `app/services/global_state.py` | ~130 | Working |
| `app/services/leaderboard.py` | ~25 | Clean |
| `app/services/lifelines.py` | ~55 | Clean |
| `app/services/rounds.py` | ~40 | Overlaps with round_manager |
| `app/services/schema.py` | ~55 | Fragile manual migrations |
| `app/services/team_assignment.py` | ~40 | Working, SQLite-specific |
| `app/data/actions.py` | ~190 | 17/27 actions defined |
| `app/data/crises.py` | ~45 | 3 crises defined |
| `app/data/ai_reveal.py` | ~40 | Static sample data |
| `app/seeds/team_data.py` | ~120 | Complete |
| `app/sockets/__init__.py` | ~10 | Essentially empty |
| `app/sockets/chat.py` | ~30 | Dead/broken code |
| `app/sockets/chat_events.py` | ~35 | Working |
| `app/utils/passwords.py` | ~25 | Clean |
| `scripts/seed_db.py` | ~65 | Working, credential issue |
| `scripts/run_ai_sim.py` | ~30 | Random-number stub |

### Frontend (8 source files)

| File | Lines | Status |
|------|-------|--------|
| `src/App.tsx` | 1491 | Monolithic but functional |
| `src/main.tsx` | ~10 | Standard entry point |
| `src/hooks/useChat.ts` | ~50 | Working |
| `src/hooks/useRoundTimer.ts` | ~70 | Working with interpolation |
| `src/lib/api.ts` | ~200 | 29 API functions, complete |
| `src/lib/socket.ts` | ~25 | Working, polling-only |
| `src/App.css` | ~15 | Minimal |
| `src/index.css` | ~20 | Fonts + Tailwind directives |

### Tests

| File | Coverage |
|------|----------|
| `api/tests/socket_chat_test.py` | 1 test (chat message persistence) |
| `playwright_login.mjs` | 1 standalone E2E script (not in framework) |
| **Everything else** | **Zero tests** |
