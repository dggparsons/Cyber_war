# Cyber War Room API

Flask backend powering the Cyber War Room game — 45 REST endpoints, 4 Socket.IO namespaces, real-time game resolution, and AI shadow simulation.

## Setup

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_db.py   # Seeds 10 nations + UN, 6 rounds, admin account
python wsgi.py              # Starts dev server on :5050
```

## Configuration (.env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | (required) | Flask session secret |
| `DATABASE_URL` | `sqlite:///../instance/cyber_war_dev.db` | Database path |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `ROUND_COUNT` | `6` | Number of game rounds |
| `ROUND_DURATIONS` | `6,6,6,6,6,4` | Minutes per round |
| `NUKE_LOCKED_DEFAULT` | `true` | Start with nukes locked |
| `GM_USERNAME` | `admin@warroom.local` | Admin login email |
| `GM_PASSWORD` | `ChangeMe123!` | Admin login password |
| `ANTHROPIC_API_KEY` | (optional) | Enables LLM narrative + AI sim |

## API Endpoints

### Auth (`/api/auth`) — 5 endpoints
| Method | Path | Rate Limit | Purpose |
|--------|------|------------|---------|
| POST | `/register` | 5/min | Register player (name + email) |
| POST | `/join` | 10/min | Join team with code |
| POST | `/login` | 10/min | Login + auto-assign team |
| POST | `/logout` | — | Logout |
| GET | `/me` | — | Session check |

### Game (`/api/game`) — 16 endpoints, 60/min default
| Method | Path | Rate Limit | Purpose |
|--------|------|------------|---------|
| GET | `/state` | 60/min | Full game state (blocks admin) |
| GET | `/actions` | 60/min | Action catalog for team type |
| GET | `/proposals` | 60/min | Team proposals for current round |
| POST | `/proposals` | 10/min | Submit action proposal |
| POST | `/votes` | 30/min | Vote on proposal (+1/-1) |
| POST | `/proposals/veto` | 60/min | UN/GM veto |
| POST | `/proposals/captain-override` | 60/min | Captain lock proposal |
| GET | `/leaderboard` | 60/min | Scores + escalation + cyber impact |
| GET | `/news` | 60/min | Last 20 news events |
| GET | `/history` | 60/min | Last 30 resolved actions |
| GET | `/proposals/preview` | 60/min | UN/GM view all proposals |
| POST | `/intel/solve` | 60/min | Solve intel puzzle |
| POST | `/lifelines/false_flag` | 60/min | Apply false-flag to proposal |
| POST | `/lifelines/phone-a-friend` | 60/min | Reveal enemy action |
| GET | `/mega-challenge` | 60/min | Active mega challenge |
| POST | `/mega-challenge/solve` | 5/min | Solve mega challenge |

### Admin (`/api/admin`) — 17 endpoints, 30/min default
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/status` | Dashboard (rounds, teams, players, timer, crises) |
| GET | `/rounds` | All rounds with timestamps |
| POST | `/rounds/start` | Activate pending round |
| POST | `/rounds/advance` | Resolve + advance to next round |
| POST | `/rounds/reset` | Reset game state (keep players) |
| POST | `/full-reset` | Full wipe (removes players too) |
| POST | `/rounds/pause` | Pause timer |
| POST | `/rounds/resume` | Resume timer |
| POST | `/nukes/toggle` | Unlock/lock nuclear actions |
| POST | `/crisis/inject` | Inject crisis event |
| POST | `/crisis/clear` | Clear active crisis |
| POST | `/clear-doom` | Clear doomsday flag |
| GET | `/intel-drops` | List intel drops |
| POST | `/intel-drops` | Create intel drop |
| GET | `/mega-challenge` | Get mega challenge |
| POST | `/mega-challenge` | Create mega challenge |
| POST | `/narrative/rerun` | Re-generate world engine narrative |

### Diplomacy (`/api/diplomacy`) — 4 endpoints, 30/min default
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List channels + messages |
| POST | `/start` | Open channel with target team |
| POST | `/respond` | Accept/decline channel |
| POST | `/send` | Send message in channel |

### Reveal (`/api/reveal`) — 1 endpoint, 20/min
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Human vs AI comparison (gated by doom or admin) |

## Socket.IO Namespaces

| Namespace | Auth | Purpose |
|-----------|------|---------|
| `/team` | login required | Chat, typing, diplomacy, proposals |
| `/gm` | admin/gm only | GM control channel |
| `/leaderboard` | open | Public leaderboard updates |
| `/global` | open | Round events, news, escalation, doom |

### Key Events Emitted
`round:started`, `round:ended`, `round:tick`, `round:timer_end`, `round:paused`, `round:resumed`, `proposals:auto_locked`, `leaderboard:update`, `news:event`, `game:nuke_state`, `game:over`, `escalation:threshold`, `crisis:injected`, `crisis:cleared`, `diplomacy:channel_opened`, `diplomacy:channel_responded`, `diplomacy:message`, `proposal:vetoed`, `session:kick`

## Services

| Service | Purpose |
|---------|---------|
| `round_manager.py` | Timer state machine, background countdown task |
| `resolution.py` | Action execution, success calc, stat deltas, deterministic RNG |
| `world_engine.py` | LLM narrative generation (Claude Sonnet 4 + template fallback) |
| `ai_simulation.py` | 10-nation AI shadow game (Claude LLM + weighted-random fallback) |
| `leaderboard.py` | Outcome scoring: baseline + deltas - escalation |
| `lifelines.py` | Award/consume lifelines (false_flag, phone_a_friend, intel_hint) |
| `crisis.py` | Crisis injection with team stat modifiers |
| `intel_generator.py` | Distribute puzzles from 65-entry pool per round |
| `global_state.py` | Nuke/doom/crisis/escalation threshold management |
| `game_reset.py` | Soft reset (keep players) + full reset (wipe players) |
| `team_assignment.py` | Fair team distribution with waitlist overflow |
| `alliances.py` | Alliance formation/breaking |

## Data

| File | Content |
|------|---------|
| `data/actions.py` | 28 actions across 6 categories (de-escalation to nuclear) |
| `data/intel_puzzles.py` | 65 puzzles (base64, hex, ROT-3, binary, URL-encoded, reversed) |
| `data/mega_challenge.py` | Operation GHOSTLINE — 5-artifact APT forensics |
| `data/crises.py` | 3 crises (VOLT_TYPHOON, ZERO_DAY_MARKET, AUTONOMOUS_AGENT) |

## Testing

```bash
python -m pytest tests/ -v
# 113 tests: admin(28), resolution(21), lifelines(23), diplomacy(18), leaderboard(11), auth(7), game(4), chat(1)
```
