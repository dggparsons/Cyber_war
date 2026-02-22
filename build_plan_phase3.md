# Phase 3 Build Plan – Real-Time & Chat (Day 5)

## Objectives
- Enable rich, low-latency collaboration for teams and back-channel diplomacy.
- Harden Socket.IO infrastructure and client UX for real-time updates (round transitions, chat, GM broadcasts).

## Backend Tasks
1. **Socket Namespace Hardening**
   - Finalize authentication middleware for `/team`, `/gm`, `/leaderboard` namespaces.
   - Implement heartbeat/ping logging to monitor connection health.
2. **Team Chat Service**
   - Socket events: `chat:message`, `chat:history`, `chat:typing`.
   - In-memory buffer per team (Redis list or capped deque) with optional persistence to `messages` table.
   - Profanity filter/logging hook for moderation if needed.
3. **Diplomacy Channels**
   - API to open a diplomacy room between two nations (captain-only or GM approved).
   - Socket room naming convention `diplomacy:<teamA>:<teamB>`, with access control enforced server-side.
   - Expiration/closure logic at round end, with transcripts posted to both teams if desired.
   - Allow teams to exchange intel keys or lifeline codes securely; include a “share puzzle key” helper so collaboration is frictionless.
4. **Broadcast Infrastructure**
   - GM panel buttons trigger Socket events (`gm:announcement`, `gm:crisis`, `gm:reveal`).
   - Leaderboard namespace consumes summarized payloads and paints charts without polling.
5. **Session Management Enhancements**
   - Detect duplicate logins and emit `session:kick` to old sockets.
   - Track per-user connection metadata (IP, browser) for debugging mid-game.

## Frontend Tasks
1. **Team Chat UI**
   - Responsive message list with color-coded senders (player vs advisor vs GM).
   - Typing indicators, unread badges, ability to collapse chat for small screens.
2. **Diplomacy Drawer**
   - UI to request/open diplomacy chats; show active channels, participants, and close buttons.
   - Visual cue when a new diplomacy request arrives (notification toast + toast action to accept/decline).
   - Quick-share widgets for intel codes/lifeline trades so teams can negotiate puzzle keys.
3. **Real-Time Notifications**
   - Toast/alert system for GM announcements, crisis injections, session kicks, diplomacy invites.
4. **Leaderboard Screen Wiring**
   - Build real-time charts fed via Socket.IO (Recharts/Chart.js).
   - Include Doomsday Clock indicator synced to global escalation score.
5. **Connection Status Indicator**
   - Display WebSocket status (connected/reconnecting) so players know if they’re out of sync.

## Testing & Monitoring
- Simulate high-volume chat (script to broadcast 1k messages/min) and ensure no dropped events.
- Add Socket.IO logging middleware to capture unauthorized access attempts.
- Ensure diplomacy rooms are inaccessible to outside teams via integration tests.
