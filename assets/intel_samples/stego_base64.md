# Intel Drop: Base64 Hidden in Document

**Puzzle Type:** steganography
**Difficulty:** Medium
**Answer:** SHADOWMERE

## Intercepted Document

A leaked diplomatic cable from CORALHAVEN's foreign ministry contains an
unusual footer:

---

> *This cable is classified OFFICIAL-SENSITIVE. Distribution limited to
> FIVE EYES desk officers. Archive reference: U0hBRE9XTUVS Rq.*
>
> End of transmission.

---

## Instructions

1. Find the Base64 string hidden in the archive reference.
2. The string `U0hBRE9XTUVS` is Base64-encoded.
3. Decode it to reveal the hidden word.
4. Submit the decoded word as your answer (all caps).

## GM Setup

```json
{
  "round_id": 2,
  "team_id": 4,
  "puzzle_type": "steganography",
  "clue": "Leaked CORALHAVEN cable has suspicious archive ref: U0hBRE9XTUVS — decode it",
  "solution": "SHADOWMERE",
  "reward_type": "phone a friend lifeline"
}
```
