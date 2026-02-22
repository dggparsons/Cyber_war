# Cyber War Room API

Phase 1 PoC backend built with Flask + Flask-SocketIO.

## Getting Started

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
cp .env.example .env
flask --app wsgi:app run --reload
```

The default configuration uses SQLite at `instance/cyber_war_dev.db`. Update `DATABASE_URL` in `.env` to point at `/home/site/data/cyber_war.db` when deploying to Azure App Service.

### Database Initialisation

Before running the app, seed the teams and rounds:

```bash
python scripts/seed_db.py
```

This creates the 10 nations + UN team along with placeholder rounds defined in `plan.md`.

## Next Steps
- Implement SQLAlchemy models + migrations (Phase 1 task).
- Build auth/team assignment routes.
- Add Socket.IO namespaces per `build_plan_phase1.md`.
