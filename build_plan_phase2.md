# Phase 2 Build Plan – Game Core (Day 3-4)

## Objectives
- Implement the deterministic game mechanics that sit under the UI: nation stats, action definitions, proposal locking, round timer/resolution, and world-state persistence.
- Deliver an end-to-end loop where teams submit actions, the backend resolves them, and results are broadcast to clients.

## Backend Tasks
1. **Nation Data & Action Catalog**
   - Define a static JSON/YAML describing each nation’s starting stats, advisor metadata, and baseline scores (reuse for seed script).
   - Create an `actions.py` registry listing action codes, categories, escalation scores, resource modifiers, success formulas, and unlock conditions (e.g., nuclear lock).
2. **Action Proposal Pipeline**
   - Implement `/api/proposals` endpoints (create/update/delete) tied into the voting tables from Phase 1.
   - Enforce per-round/per-slot limits, validate targets, and ensure proposals freeze when the round transitions to `resolving`.
3. **Round Timer + Scheduler**
   - Add a background job (Celery, APScheduler, or simple event loop) to tick down the active round; broadcast `round_tick` via Socket.IO.
   - On timer expiry, auto-fill any missing action slots with “WAIT” proposals, mark all proposals `locked`, and enqueue resolution.
4. **Resolution Engine**
   - Build deterministic stat comparison helpers (attack vs defense rolls, RNG seeded per round for reproducibility).
   - Apply action effects: update nation stats, escalation scores, prosperity/influence, damage logs, alliances, etc.
   - Persist resolved actions and emit narrative hooks for Phase 4’s World Engine.
5. **Intel Drop, Lifeline & Mega Challenge Mechanics**
   - Extend schema with `intel_drops` table (id, round_id, team_id, puzzle_type, clue, reward).
   - Lifeline tokens model (`lifelines` table) tracking availability and usage (false flag, phone-a-friend, vote boost); enforce once-per-game constraints.
   - API to claim rewards when a team submits a correct solution code; GM override to grant hints.
   - Add `mega_challenge` table describing the long-form puzzle (description, hints, solution, reward tiers). Track submission timestamps to award descending influence bonuses based on solve order (+15/+10/+5, etc.) and log unique perks for top teams.
6. **State Machine Enforcement**
   - Functions to transition rounds: `start_round`, `close_submissions`, `resolve_round`, `publish_results`.
   - Guard API/SockeIO handlers so actions only occur in valid states (no proposals while resolving, etc.).
7. **Testing & Simulation**
   - CLI command `simulate_round` that seeds dummy proposals and runs the resolver—used for unit tests and load rehearsal.
   - Unit tests for action math, RNG seeding, and escalation score updates.

## Frontend Tasks
1. **Action Menu Rendering**
   - Fetch action catalog, render grouped by category with escalation colours and tooltip explaining payoff/risk.
   - Show per-slot selection UI with validation states (target required, resources insufficient, locked).
2. **Voting UX Enhancements**
   - Live vote counters, “locked” badges when the timer expires, captain override modal when proposals missing.
   - Display advisory hints per action (from advisor metadata) to encourage discussion.
3. **Timer & Round State Indicators**
   - Prominent countdown component synced via Socket.IO events.
   - Status chips (“Submissions Open”, “Resolving…”, “Results Ready”) so teams know what phase they’re in.
4. **Intel Drop & Mega Challenge UI**
   - Panel showing current puzzle (download button, instructions, countdown). Input form to submit solution; show earned lifelines/buffs when solved.
   - Separate card for the long-form Mega Challenge with progress tracker (hints unlocked, submissions remaining) plus a leaderboard showing which rewards are still available.
5. **Results Panel**
   - After each round, show per-action outcome (success/failure, stat changes, target reactions) with animation hooks for Phase 4.

## Deliverables by End of Phase 2
- Backend can process a full round cycle without manual intervention.
- Frontend users can submit/vote on actions, watch timer expire, and view resolved results.
- Unit tests covering key resolution mechanics and state transitions.
