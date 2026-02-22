# Phase 5 Build Plan – AI Shadow Game & Polish (Day 8-9)

## Objectives
- Run autonomous AI agents through the same scenario to generate comparison data for the reveal.
- Finalise crisis injection tooling, reveal presentation, and overall UX polish.
- Conduct focused playtests and incorporate feedback.

## Backend Tasks
1. **AI Simulation Runner**
   - Script/service that loads nation stats, boots LLM agents (Claude/GPT) with prompts mirroring team briefs, and loops through the same rounds/action menu.
   - Record per-round actions, outcomes, escalation scores, Outcome Scores, advisor quotes.
   - Store results in dedicated tables (`ai_runs`, `ai_actions`, `ai_scores`) for later display.
2. **Reveal Data API**
   - Endpoints delivering AI vs human comparisons: average escalation, time to first violent action, nuclear usage, Outcome Score deltas.
   - Prepare highlight snippets (LLM quotes) for the final presentation screen.
3. **Crisis & Intel Enhancements**
   - GM UI to preload crisis scripts, preview text, and push to teams with one click.
   - Logging around injected crises to include in the final narrative/reveal.
   - Asset manager for hackable intel drops: upload files, define puzzle type, reward, solution keys, and which teams hold fragments.
   - Lifeline ledger showing which team earned/used False Flag, Phone-a-Friend, etc.
4. **Polish & Accessibility**
   - Keyboard navigation for key UI elements, color contrast checks on retro palette, tooltip copy pass.
   - Performance tuning (bundle splitting, memoization) to keep the dashboard snappy.

## Frontend Tasks
1. **Reveal Screen**
   - Side-by-side comparison view: human Outcome Scores vs AI runs, escalation graphs, AI quote carousel.
   - Doom-state overlay if nukes fired; messaging emphasising “everyone loses” before showing AI results.
2. **Crisis & Intel UI**
   - GM modal to select crisis template, edit copy, preview, and broadcast; include countdown/confirmation.
   - Player-facing toast/overlay that dramatizes the crisis event.
   - Intel drop management panel: list of active puzzles, download links, submission form, status indicators, reward badges when solved.
   - False Flag + Phone-a-Friend buttons with confirmation dialogs and cooldown display.
3. **Micro-Interactions & Animations**
   - Advisor portraits reacting to round outcomes.
   - Hacking animations, CRT flickers, Doomsday Clock ticks when escalation rises.
4. **Playtest Instrumentation**
   - Lightweight analytics/logging to capture decision timestamps, chat volume, socket disconnects.

## Playtesting
- Run a 6-team internal session; collect notes on pacing, clarity, fairness.
- Adjust round durations, scoring weights, or UI hints based on feedback.
- Verify AI reveal data populates correctly and resonates with testers.
- Test hackable intel + lifelines end-to-end: measure solve times, ensure rewards trigger, confirm False Flag attribution changes are clear to everyone.

## Sample Asset Pack
- Maintain `/assets/intel_samples/` with ready-made puzzles for dev/testing and to guide anyone co-building the experience (including LLM assistants):
  - 3 cipher PDFs (Vigenère, substitution, XOR) with answer keys + instructions.
  - 2 stego images (hidden base64 text, LSB message) with extraction steps.
  - Example False Flag briefing card describing narrative and mechanical effects.
  - Sample Phone-a-Friend hint sheet to demonstrate tone/format.
  - One full Mega Challenge outline (story, multi-stage clues, final answer, reward tier structure) so everyone understands scope/format.
