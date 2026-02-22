# Phase 1 Build Plan (Backend + Frontend)

## Architecture Overview
- **Repo Layout**
  - `api/`: Flask application (app factory, blueprints, Socket.IO server, SQLAlchemy models, migrations, seed scripts).
  - `client/`: Vite + React frontend (Tailwind theme, war-room dashboard, GM view).
  - `infrastructure/`: deployment manifests, Azure notes, local dev scripts.
- **Config**
  - Module exporting: round durations (6/6/6/4 mins), total rounds (6), `NUKE_LOCKED=True`, GM credentials, SQLite path (`/home/site/data/cyber_war.db`), rate-limit settings.
  - Environment-specific overrides via `.env` (dev vs Azure).
- **Runtime Stack**
  - Flask + Flask-SocketIO (eventlet) behind Gunicorn in production.
  - SQLAlchemy + Alembic for persistence (SQLite in dev, Azure Files or Postgres later).
  - Socket namespaces: `/team`, `/gm`, `/leaderboard`.

## Backend Tasks
1. **Project Bootstrap**
   - Create virtualenv, `pip install flask flask-socketio flask-login sqlalchemy alembic python-dotenv`.
   - App factory (`create_app`) with blueprint placeholders (`auth`, `game`, `admin`).
   - Socket.IO initialization with custom namespaces and authentication middleware.
2. **Database Models & Migrations**
   - Tables: `User`, `Team`, `Round`, `ActionProposal`, `ActionVote`, `Action`, `Message`, `Waitlist`.
   - Alembic initial migration + seed script for 10 nations + UN, advisor metadata, baseline scores.
3. **Auth & Registration**
   - Routes: `POST /api/register` (generate random password, hash, show to user), `POST /api/login` (session cookie + session token).
   - Admin routes for password reset, user listing, team reassignment.
   - Rate limiting + optional invite code check.
4. **Team Assignment Service**
   - Function `assign_team(user)`:
     - Begin transaction (`BEGIN IMMEDIATE` for SQLite).
     - Query team with lowest occupancy under `seat_cap`, lock row, assign user, commit.
     - If none available, insert into `waitlist`.
   - Emit Socket.IO event notifying team of new member.
5. **Round/Timer State Machine**
   - `RoundService` with states `pending → active → resolving → reveal`.
   - Scheduler/timer that broadcasts `round_tick`, auto-submits “Wait” for missing actions at zero.
   - Nuclear lock flag: refuse catastrophic actions unless GM toggles crisis; if a nuke succeeds, emit `doom_event` and end game.
6. **Socket.IO Events**
   - Team namespace: `proposal:create`, `proposal:vote`, `chat:message`, `session:kick`.
   - GM namespace: `round:start`, `round:end`, `crisis:inject`, `nuke:toggle`, `reveal:trigger`.
   - Leaderboard namespace for broadcast-only events.
   - Server-side auth checks on every handler (`current_user.team_id`, roles).
7. **GM/Admin APIs & Dashboard Data**
   - `/admin/dashboard` JSON: round info, team summaries, pending proposals, chat logs, action queues.
   - Controls to trigger crises, toggle nuclear lock, reset timers, broadcast messages.

## Frontend Tasks
1. **Scaffold Vite/React Project**
   - Install dependencies: `react-router`, `socket.io-client`, `axios`, `tailwindcss`, `clsx`.
   - Configure Tailwind with retro palette, fonts (Inter + Press Start 2P), utility classes for CRT effect.
2. **Auth Views**
   - `/register`: form for display name/email; on success, show generated password + instructions.
   - `/login`: username/password form, error handling, redirect to dashboard.
3. **Player Dashboard Shell**
   - Layout with three zones: nation brief/advisors, action proposal grid, chat/roster/timer column.
   - Fetch `/api/me` on load to populate team info, baseline score, round state.
   - Hook Socket.IO client to receive `round_tick`, `round_results`, chat events.
4. **Action Proposal & Voting UI**
   - Three slots with dropdowns for action + target; show escalation color badges + payoff text.
   - Vote tally list with “locked” indicator when timer expires.
   - Disable nuclear options until backend `nukeUnlocked` flag true.
5. **Chat & Roster Panel**
   - Real-time chat feed, input box, sentiment/advisor quips.
   - Roster list showing teammate names and roles (captain, GM, UN).
6. **Leaderboard & GM Dashboard**
   - `/leaderboard`: bar chart with Outcome Score + Δ baseline, escalation line chart, news ticker.
   - `/admin`: table view of teams/actions, round controls, nuclear lock toggle, reveal button; designed for screen sharing during Teams session.

## Integration & Validation
- Create seed/test script to register 12 fake users and confirm deterministic team assignment.
- CLI simulator to progress rounds, ensuring “auto Wait” and doom-event logic works.
- Write unit tests for team assignment race conditions and auth decorators.
- Smoke test Socket.IO by attempting cross-team message injection (should be rejected server-side).
- Document Azure deployment steps (App Service env vars, `/home/site/data` creation) alongside plan.
