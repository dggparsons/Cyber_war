# Phase 6 Deployment & Runbook

## Pre-Event Deployment
1. **Backend**
   - Build image or zip deploy folder `api/` with `.venv` excluded.
   - Set env vars on App Service: `SECRET_KEY`, `DATABASE_URL=/home/site/data/cyber_war.db`, `ROUND_COUNT`, `ROUND_DURATIONS`, `NUKE_LOCKED_DEFAULT`.
   - Copy `instance/` folder to `/home/site` (includes SQLite DB). If empty, run `python scripts/seed_db.py` on server.
   - Run `python scripts/run_ai_sim.py` to seed AI reveal data.
2. **Frontend**
   - Build via `npm run build`; upload `client/dist` to static hosting (Azure Static Web Apps or blob).
   - Set `VITE_API_BASE_URL` to backend URL and rebuild if base differs.
3. **Network**
   - Verify Socket.IO works through HTTPS (configure `CORS_ORIGINS` env).
   - Open necessary ports if running on local LAN.

## Smoke Test Script
- `curl https://server/api/health/`
- Register/login via `/api/auth/register`, `/api/auth/login` with sample user.
- Hit `/api/game/state` to ensure team assigned and intel drop present.
- Open leaderboard route `/api/game/leaderboard` and `/api/reveal/` to confirm data.

## Game-Day Checklist
- T-30: open registration, monitor DB for seat counts.
- T-10: run `python scripts/run_ai_sim.py` if you want fresh AI data.
- T-5: broadcast Teams link, share leaderboard screen.
- During game: monitor Flask logs for Socket.IO disconnects, keep GM dashboard on projector.
- Post-game: export `instance/cyber_war_dev.db` for records; reset DB if running multiple sessions.

## Contingencies
- Keep `scripts/run_ai_sim.py` handy to regenerate AI stats if DB wiped.
- Have `npm run build` artifacts locally in case CDN fails; serve via `npm run dev` as fallback.
