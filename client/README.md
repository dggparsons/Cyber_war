# Cyber War Room Client

React + TypeScript frontend for the Cyber War Room game. Real-time multiplayer war room interface with CRT visual effects, live charts, team chat, and diplomacy.

## Setup

```bash
cd client
npm install
npm run dev        # Dev server at http://localhost:5173
npm run build      # Production build to dist/
npx tsc --noEmit   # Type check
```

## Architecture

### App.tsx (780 lines) — Main Orchestrator
- Session bootstrap + auth flow
- Socket.IO event listeners (15+ event types)
- Game state polling (leaderboard 10s, history 10s, UN preview 7s)
- Routing: spectator | admin | player (with auth gate)
- Toast notifications, audio cues, escalation tint

### Components (19 files, 2,000+ lines)

| Component | Lines | Purpose |
|-----------|-------|---------|
| **AdminPanel** | 407 | GM dashboard — round controls, crisis, resets, proposal oversight |
| **modals** | 366 | BriefingModal, NationsModal, HowToPlayModal, IntelModal, MegaChallengeModal |
| **ActionConsole** | 145 | Proposal submission, voting, false flags, captain override |
| **SpectatorView** | 119 | Public read-only view — leaderboard, escalation, cyber impact |
| **RevealView** | 117 | Human vs AI comparison charts + reasoning excerpts |
| **DiplomacyPanel** | 102 | Channels, accept/decline, messaging, alliances |
| **GameSidebar** | 169 | Leaderboard, escalation chart, roster, chat, news, history |
| **GameHeader** | 76 | Timer, progress bar, escalation counter, doomsday clock |
| **AuthPanel** | 71 | Registration (name + email) and login |
| **charts** | 70 | EscalationChart, LeaderboardBarChart (Recharts) |
| **overlays** | 52 | DoomOverlay, CrisisAlert, EscalationAlert, ActiveCrisisBanner |
| **AdvisorsPanel** | 50 | Advisor cards with avatars, mood colors, strategy hints |
| **ChatComposer** | 45 | Message input with typing indicators |
| **IntelPanel** | 42 | Intel drops with click-to-solve modals |
| **LifelinesPanel** | 42 | Lifeline inventory, phone-a-friend |
| **PeaceCouncilPanel** | 35 | UN veto interface |
| **ErrorBoundary** | 35 | Error handler with retry |
| **DoomsdayClock** | 18 | Circular escalation gauge |
| **NewsTicker** | 16 | Marquee news feed |

### Hooks

| Hook | Purpose |
|------|---------|
| **useRoundTimer** | Timer sync via socket, client-side 250ms interpolation |
| **useChat** | Chat history/message/typing via socket, 3s typing timeout |

### API Client (lib/api.ts)
30+ typed functions covering auth, game, proposals, diplomacy, intel, lifelines, mega challenge, reveal, and admin operations. All use `apiFetch` wrapper with credentials and error handling.

### Utilities (lib/gameUtils.ts)
- `GameState`, `Proposal` type definitions
- `SLOT_IDS`, `NATION_COLORS` constants
- `getCategoryColor()`, `formatTimerDisplay()` helpers

## Styling

- **Tailwind theme:** Custom warroom colors (blue, slate, cyan, amber), Press Start 2P pixel font
- **CRT effects:** Scanlines overlay, phosphor text glow, screen shake, 4s flicker cycle, hack-pulse borders
- **Animations:** Marquee scroll, doomsday gauge (conic gradient), escalation alert pulse

## Socket.IO Integration

Two socket connections:
- `/team` — Chat messages, typing indicators, diplomacy events, proposal vetoes, session kicks
- `/global` — Round events (tick, start, end, pause), game state (nukes, doom, crisis), news, escalation

## Views

| URL Param | View | Description |
|-----------|------|-------------|
| (none) | Player | Full game interface with auth gate |
| `?view=spectator` | Spectator | Read-only leaderboard + live stats |
| `?view=gm` | Admin | GM dashboard (also auto-routed for admin users) |

## Dependencies

| Package | Purpose |
|---------|---------|
| react, react-dom | UI framework |
| socket.io-client | Real-time WebSocket communication |
| recharts | Line charts, bar charts for leaderboard/escalation |
| react-markdown + remark-gfm | Markdown rendering in modals |
| tailwindcss | Utility-first CSS |
| vite | Build tooling |
| typescript | Type safety |
