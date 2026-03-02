# Intel Drop: Base64 Steganography

**Puzzle Type:** Steganography
**Difficulty:** Medium
**Category:** Encoding / Data Hiding

---

## CLASSIFIED -- OSINT COLLECTION REPORT

**From:** Cyber Threat Intelligence -- Open Source Desk
**To:** Joint Cyber Command, Analysis Branch
**Priority:** ROUTINE (upgraded to IMMEDIATE upon discovery)

During routine monitoring of CORALHAVEN's government press releases,
an analyst flagged an unusual pattern in a diplomatic communique
published on their Ministry of Foreign Affairs website. The document
appears benign, but contains an anomalous string embedded in what
looks like a routine archival reference.

### Intercepted Document

---

> **REPUBLIC OF CORALHAVEN -- MINISTRY OF FOREIGN AFFAIRS**
>
> *Communique No. 2026-0147*
>
> The Ministry wishes to inform all diplomatic missions that the
> annual review of bilateral trade agreements has been completed.
> All signatories are requested to confirm their participation in
> the upcoming summit scheduled for Q2 2026.
>
> The Ministry further notes that cybersecurity cooperation
> frameworks remain a priority for regional stability. Member
> states are encouraged to share threat intelligence through
> established channels.
>
> For questions regarding this communique, contact the Protocol
> Division at extension 4401.
>
> ---
> *Classification: OFFICIAL -- Distribution: Unrestricted*
> *Archive Reference: Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==*
> *Document hash: 7a3f... [TRUNCATED]*
> *End of transmission.*

---

### Analyst Notes

- The "Archive Reference" field contains a Base64-encoded string.
- Base64 strings commonly end with `=` or `==` padding characters.
- The string `Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==` does not match
  CORALHAVEN's standard reference numbering format (which uses
  `CH-YYYY-NNNNN`).
- Standard Base64 decoding tools can extract the hidden message.

### Hints (reveal progressively if team is stuck)

1. **Hint 1:** Look for the string that does not belong -- it is in the footer metadata.
2. **Hint 2:** The Base64 string is `Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==`. Paste it into any Base64 decoder.
3. **Hint 3:** The decoded message is two words describing a severe security finding.

---

## GM SOLUTION

**Answer:** `CRITICAL VULNERABILITY`

**Walkthrough:**
```
Base64 input:  Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==
Decoded ASCII: CRITICAL VULNERABILITY
```

Verification (Python):
```python
import base64
base64.b64decode("Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==").decode()
# -> 'CRITICAL VULNERABILITY'
```

**SHA-256 hash of solution:**
`4e5188bdf6a33d695c6a188f2cb91683f360787e3226c0419a2f5ed06b99c5c8`

### GM Setup -- API Call

```json
{
  "puzzle_type": "steganography",
  "clue": "CORALHAVEN diplomatic communique has suspicious archive reference: Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ== -- suspected Base64 encoded message. Decode it.",
  "solution": "CRITICAL VULNERABILITY",
  "reward_type": "phone_a_friend"
}
```
