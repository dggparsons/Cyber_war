# Cyber War Room

An interactive, real-time conference game simulating AI escalation in cyber warfare scenarios. Based on the research paper "Escalation Risks from Language Models in Military and Diplomatic Decision-Making" (Rivera et al., FAccT 2024).

## Overview

100 players across 10 cyber-themed nation-states compete in 6 rounds of strategic decision-making. At the end, the game reveals that AI agents played the same scenario and escalated to catastrophic outcomes — driving home the risks of autonomous AI in military/cyber contexts.

## Tech Stack

- **Backend:** Flask + Flask-SocketIO + SQLAlchemy (SQLite)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Real-time:** Socket.IO (team chat, diplomacy, live updates)
- **Deployment:** Docker Compose

## Quick Start

### Local Development

```bash
# Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_db.py
python wsgi.py

# Frontend (separate terminal)
cd client
npm install
cp .env.example .env
npm run dev
```

### Docker

```bash
docker compose up --build
# Backend: http://localhost:5050
# Frontend: http://localhost:4173
```

## Project Structure

```
api/          Flask backend (routes, services, models, sockets)
client/       React frontend (Vite + Tailwind)
docs/         Deployment checklist, admin credentials, open questions
assets/       Intel puzzle samples and challenge outlines
```

## Documentation

- [Deployment Checklist](docs/deployment_checklist.md)
- [Admin Credentials](docs/default_admin_credentials.md)
- [Open Questions](docs/open_questions.md)
- [API README](api/README.md)
