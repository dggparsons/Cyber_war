# Intel Drop: Hex Decode

**Puzzle Type:** cipher
**Difficulty:** Easy
**Answer:** NUKEKEY

## Intercepted Transmission

Telemetry logs from a compromised satellite uplink contain an anomalous
hex sequence embedded in the handshake payload:

```
4e554b454b4559
```

## Instructions

1. Convert each pair of hex digits to its ASCII character.
2. `4e` = N, `55` = U, `4b` = K, `45` = E, `4b` = K, `45` = E, `59` = Y
3. Submit the decoded word as your answer (all caps).

## GM Setup

```json
{
  "round_id": 2,
  "team_id": 3,
  "puzzle_type": "cipher",
  "clue": "Anomalous hex in satellite handshake: 4e554b454b4559",
  "solution": "NUKEKEY",
  "reward_type": "false flag lifeline"
}
```
