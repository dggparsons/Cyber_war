# Phase 4 Build Plan – Leaderboard & World Engine (Day 6-7)

## Objectives
- Turn raw game data into a polished “war room” display with real-time charts and narrative flavour.
- Integrate the LLM World Engine for post-round summaries while keeping mechanics deterministic.
- Implement nuclear lock controls and the automatic “everyone loses” trigger.

## Backend Tasks
1. **Outcome Score Pipeline**
   - Compute normalised prosperity/security/influence deltas per nation after each round.
   - Store Outcome Score history for charting; include Δ vs baseline calculation.
2. **Leaderboard API**
   - Expose `/api/leaderboard` returning standings, escalation history, Cyber Impact logs, advisor quotes.
   - Push incremental updates via Socket.IO (`leaderboard:update`).
3. **World Engine Integration**
   - Service module that formats round context (actions, results, crises) and calls Anthropic/OpenAI.
   - Async job queue to avoid blocking main loop; retries with degraded mode (fallback to templated narrative) if API fails.
4. **Nuclear Lock Controls**
   - GM endpoints to toggle `nuke_unlocked` flag, log crisis reasons, and broadcast state to clients.
   - Doom detector: once a nuclear/catastrophic action succeeds, set global `game_state='doom'`, halt timers, emit reveal trigger, zero out Outcome Scores.
5. **News Ticker & Event Log**
   - Maintain a rolling log of notable events (alliances, attacks, crises) for the ticker; expose via API and sockets.
    - Include intel drop solves (who cracked what, what reward earned) and false flag usage so the audience sees those twists.

## Frontend Tasks
1. **Leaderboard Dashboard**
   - Full-screen SOC-style layout with:
     - Outcome Score bar chart + Δ baseline badges.
     - Escalation multi-line chart.
     - Cyber Impact list (who attacked whom, successes/failures).
     - Doomsday Clock gauge tied to global escalation.
     - News ticker with LLM-generated headlines.
   - Auto-refresh via Socket.IO; fallback to polling if disconnected.
2. **World News Panel**
   - Modal or collapsible panel showing the latest LLM narrative per round.
   - Support “degraded mode” message if LLM unavailable.
3. **GM Controls UI Enhancements**
   - Toggle buttons for nuclear lock, crisis injections, and reveal mode with clear state indicators.
   - Display queue of pending LLM narratives and allow manual re-run if needed.
4. **Player Dashboard Enhancements**
   - Integrate the latest narrative summary and scoreboard highlights into the team view after each round.
   - Visual cues when global escalation passes thresholds (color-shifted background, sirens, etc.).

## Testing & Validation
- Mock World Engine calls during automated tests; ensure fallback text renders gracefully.
- Verify the doom trigger stops all timers/actions and flips UI to reveal prep mode.
- Load-test chart updates with multiple simultaneous viewers (leaderboard route shared over Teams/projector).
