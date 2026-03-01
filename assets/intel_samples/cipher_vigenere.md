# Intel Drop: Vigenere Cipher

**Puzzle Type:** cipher
**Difficulty:** Medium
**Answer:** ESCALATION

## Intercepted Transmission

Our SIGINT team captured an encrypted signal from an unknown proxy relay.
The analyst notes scrawled on the intercept read: "Key is FROSTBYTE".

```
JWTEXEHYBU
```

## Instructions

1. This is a Vigenere cipher.
2. The key is **FROSTBYTE**.
3. Decrypt the ciphertext to reveal the hidden word.
4. Submit the decrypted plaintext as your answer (all caps).

## GM Setup

To create this intel drop via the admin API:

```json
{
  "round_id": 1,
  "team_id": 1,
  "puzzle_type": "cipher",
  "clue": "Intercepted ciphertext: JWTEXEHYBU — analyst note says key is FROSTBYTE (Vigenere)",
  "solution": "ESCALATION",
  "reward_type": "false flag lifeline"
}
```
