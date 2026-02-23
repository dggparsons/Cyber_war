# AI Simulation Runner

The `scripts/ai_sim_runner.py` tool automates a full game loop by acting as the GM and 11 team agents. It is designed for generating repeatable AI runs you can showcase during the reveal, while still exercising the same REST endpoints real players use.

## Configuration

You can either supply a JSON config file or rely entirely on environment variables (recommended when using `.env.ai_sim`).

### JSON file (`ai_sim_config.json`)

```json
{
  "base_url": "http://localhost:5050",
  "gm_email": "gm@example.com",
  "gm_password": "SuperSecret!",
  "rounds": 6,
  "intel_success_chance": 0.25,
  "vote_positive_bias": 0.6,
  "teams": [
    { "display_name": "SIM-NEXUS", "join_code": "NEXUS-OPS" },
    { "display_name": "SIM-IRON", "join_code": "IRON-VANGUARD" }
    // ...one entry per team, including UN join code
  ]
}
```

Guidelines:

- Provide GM credentials with admin rights.
- Each team entry needs a join code (or existing email/password). The script will auto-register if needed.
- `rounds` controls how many cycles to run; make sure the DB has enough pending rounds.
- `intel_success_chance`/`vote_positive_bias` tune how aggressive agents are when “solving” intel and voting.

### Environment fallback

If you omit `--config`, the runner reads the following environment variables (load them via `.env.ai_sim`):

```
SIM_BASE_URL=http://localhost:5050
SIM_GM_EMAIL=gm@example.com
SIM_GM_PASSWORD=SuperSecret!
SIM_ROUNDS=6
SIM_INTEL_SUCCESS=0.25
SIM_VOTE_BIAS=0.6
SIM_TEAM_JOIN_CODES=NEXUS-OPS,IRON-VANGUARD,...
```

### Running the simulation

```bash
# load env first
export $(grep -v '^#' .env.ai_sim | xargs)
export $(grep -v '^#' .env.openai | xargs)

# ensure GM account exists (only needs to run once per DB)
python scripts/ensure_gm.py

python scripts/ai_sim_runner.py --output results/ai_run.json
```

What it does:

1. Logs in as the GM and each team agent.
2. For every round:
   - Starts the round via admin endpoint.
   - Each agent fetches `/api/game/state`, submits actions for empty slots, casts votes, and randomly attempts intel solves.
   - The GM advances the round and records the leaderboard snapshot.
3. Writes a summary JSON (`--output`) containing per-round leaderboards, ready to be ingested into the reveal view or archived.

## Notes & Next Steps

- Agents currently use simple heuristics (weighted random by action category). You can swap `_select_action` with LLM calls once Azure/OpenAI keys are available.
- Intel solving is simulated; without real solutions the endpoint will usually reject attempts, but the flow mimics timing/calls the real client would make.
- The output JSON matches the structure expected by `ai_reveal_samples.json`; you can integrate real runs by copying the relevant fields into that file before the presentation.

Review `scripts/ai_sim_runner.py` for additional customization hooks (e.g., logging, round delays). Feel free to extend the class for custom behaviours per team.
