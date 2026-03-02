# Intel Drop: Hex Decode

**Puzzle Type:** Cipher
**Difficulty:** Easy-Medium
**Category:** Encoding

---

## CLASSIFIED -- SIGINT INTERCEPT REPORT

**From:** NSA Tailored Access Operations -- Relay Station ECHO-7
**To:** Joint Cyber Command, Watch Floor
**Priority:** FLASH

Our passive collection platform intercepted an anomalous burst transmission
from a compromised satellite uplink belonging to IRONVEIL's military
C2 infrastructure. The transmission was embedded in routine telemetry
handshake data, disguised as calibration bytes. The hex payload is
reproduced below.

### Intercepted Payload

```
4F 50 45 52 41 54 49 4F 4E 20 42 4C 41 43 4B 4F 55 54
```

Alternate (no spaces):
```
4F5045524154494F4E20424C41434B4F5554
```

### Analyst Notes

- Each pair of hex digits represents one ASCII character.
- `0x20` is the ASCII code for a space character.
- Standard hex-to-ASCII conversion table applies.
- The decoded message appears to be an operation codename.

### Hints (reveal progressively if team is stuck)

1. **Hint 1:** Each hex pair maps to one letter. Start with `4F` = O.
2. **Hint 2:** The first word is a 9-letter military term starting with O.
3. **Hint 3:** `42 4C 41 43 4B` spells a color.

---

## GM SOLUTION

**Answer:** `OPERATION BLACKOUT`

**Walkthrough:**
```
4F=O  50=P  45=E  52=R  41=A  54=T  49=I  4F=O  4E=N
20=(space)
42=B  4C=L  41=A  43=C  4B=K  4F=O  55=U  54=T
```

**SHA-256 hash of solution:**
`2c241443923898e70335e208823c2cf487c00c4462d7d1dfb3d04e944945bfb7`

### GM Setup -- API Call

```json
{
  "puzzle_type": "cipher",
  "clue": "Intercepted hex payload from IRONVEIL satellite uplink: 4F5045524154494F4E20424C41434B4F5554 -- decode the ASCII",
  "solution": "OPERATION BLACKOUT",
  "reward_type": "false_flag"
}
```
