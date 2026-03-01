# Intel Drop: Hex in EXIF Metadata

**Puzzle Type:** steganography
**Difficulty:** Medium
**Answer:** ZERODAY

## Intercepted Image

Our digital forensics team examined a propaganda image shared on
IRONVEIL state media. The EXIF metadata contains an unusual
"Artist" field:

```
EXIF Data:
  Camera Model: Canon EOS R5
  Date: 2025-11-15
  Artist: 5a45524f444159
  GPS: [REDACTED]
```

## Instructions

1. The "Artist" field contains a hex-encoded string.
2. Convert each hex pair to ASCII: `5a`=Z, `45`=E, `52`=R, `4f`=O, `44`=D, `41`=A, `59`=Y
3. Submit the decoded word as your answer (all caps).

## GM Setup

```json
{
  "round_id": 3,
  "team_id": 5,
  "puzzle_type": "steganography",
  "clue": "Propaganda image EXIF 'Artist' field contains: 5a45524f444159 — decode the hex",
  "solution": "ZERODAY",
  "reward_type": "false flag lifeline"
}
```
