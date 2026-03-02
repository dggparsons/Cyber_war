# Cyber War Room

An interactive, real-time conference game simulating AI escalation in cyber warfare scenarios. Based on the research paper "Escalation Risks from Language Models in Military and Diplomatic Decision-Making" (Rivera et al., FAccT 2024).

Up to 100 players across 10 cyber-themed nation-states compete in 6 rounds of strategic decision-making. A parallel AI shadow game runs the same scenario with LLM agents. At the end, the reveal shows how the AI escalated compared to human players — driving home the risks of autonomous AI in military/cyber contexts.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask 3.0, Flask-SocketIO, SQLAlchemy 2.0, SQLite |
| **Frontend** | React 19, TypeScript 5.9, Vite 7.3, Tailwind CSS 3.4, Recharts 3.7 |
| **Real-time** | Socket.IO — 4 namespaces (`/team`, `/gm`, `/leaderboard`, `/global`) |
| **AI** | Anthropic Claude (shadow game simulation + world engine narrative) |
| **Deployment** | Docker Compose (gunicorn + eventlet backend, nginx frontend) |

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
# Frontend: http://localhost:4173
# Backend:  http://localhost:5050
# Admin:    admin@warroom.local / ChangeMe123!
```

### Local Development

```bash
# Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_db.py
python wsgi.py
# API running at http://localhost:5050

# Frontend (separate terminal)
cd client
npm install
npm run dev
# UI running at http://localhost:5173
```

## How the Game Works

1. **Players register** with name + email, are auto-assigned to one of 10 nation-states (or UN)
2. **Each round** (timed), teams propose actions via vote — offensive cyber strikes, diplomacy, defense, espionage
3. **Captain override** can lock a proposal; UN can veto actions
4. **Resolution engine** executes actions, applies effects to team stats (prosperity, security, influence, escalation)
5. **Intel puzzles** (ciphers, stego, hex) award lifelines: phone-a-friend, false flags
6. **Diplomacy channels** let teams negotiate privately in real-time
7. **Mega Challenge** — a multi-stage forensics puzzle worth bonus influence
8. **Doomsday** — if escalation spirals or nukes land, the game ends immediately
9. **Reveal** — AI shadow game results shown side-by-side with human outcomes

## Project Structure

```
api/                  Flask backend
  app/
    routes/           6 blueprints (auth, game, admin, diplomacy, reveal, health)
    services/         17 service modules (resolution, round manager, AI sim, etc.)
    sockets/          Socket.IO namespaces + chat events
    data/             Action catalog (28), intel puzzles (65), crises (3), mega challenge
    models.py         21 SQLAlchemy models
  tests/              113 tests across 9 files
  scripts/            seed_db.py, run_ai_sim.py

client/               React frontend
  src/
    components/       19 component files (2,000+ lines)
    hooks/            useRoundTimer, useChat
    lib/              api.ts (30+ functions), gameUtils.ts
    App.tsx           Main orchestrator (780 lines)

assets/               Intel puzzle samples, briefing cards
scripts/              E2E smoke + full game test scripts
docs/                 Deployment checklist, admin creds, AI sim docs
```

## Key Numbers

| Metric | Count |
|--------|-------|
| API endpoints | 45 |
| Database models | 21 |
| Backend services | 17 |
| Socket.IO event types | 17 |
| Game actions | 28 |
| Intel puzzles | 65 |
| Frontend components | 19 |
| Unit tests | 113 |

## GM / Admin Panel

Admin users see a dedicated dashboard (never the player view):
- Start/pause/resume/advance rounds
- Inject crises, toggle nuclear options, clear doom
- View all team proposals, veto actions
- Create intel drops and mega challenges
- Re-generate world engine narrative
- Reset game (soft or full wipe)

## Testing

```bash
cd api
python -m pytest tests/ -v
# 113 tests covering: admin, resolution, diplomacy, lifelines, leaderboard, auth, game, chat
```

## Documentation

- [API Reference](api/README.md)
- [Frontend Guide](client/README.md)
- [Deployment Checklist](docs/deployment_checklist.md)
- [Admin Credentials](docs/default_admin_credentials.md)
- [AI Simulation Runner](docs/ai_sim_runner.md)
- [Game Design](plan.md)
- [Latest Audit](AUDIT5.md)
