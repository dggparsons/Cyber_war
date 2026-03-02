# Intel Drop: Substitution Cipher

**Puzzle Type:** Cipher
**Difficulty:** Medium
**Category:** Classical Cryptography

---

## CLASSIFIED -- HUMINT INTERCEPT REPORT

**From:** MI6 Liaison Desk -- Station GREENWICH
**To:** FIVE EYES Cyber Threat Intelligence Fusion Cell
**Priority:** IMMEDIATE

A field operative embedded in SHADOWMERE's signals corps photographed a
handwritten note on a senior officer's desk before the office was swept.
The note uses a simple letter-substitution scheme. Frequency analysis
indicates a Caesar-family cipher with a consistent shift value.

### Intercepted Ciphertext

```
PUZPKLY AOYLHA KLALJALK
```

### Analyst Notes

- This is a monoalphabetic substitution cipher (Caesar variant).
- All letters are shifted by the same constant value.
- Spaces are preserved -- the plaintext has three words.
- The message appears to be a security alert phrase.

### Frequency Analysis Hint

The most common letter in the ciphertext is `L` (appears 4 times).
In standard English, the most common letters are E, T, A, O, I, N, S.

If `L` maps to `E`, the shift would be +7 (L is the 12th letter, E is
the 5th; 12 - 5 = 7).

### Hints (reveal progressively if team is stuck)

1. **Hint 1:** The cipher uses a fixed shift applied to every letter. Try shifts between 1 and 25.
2. **Hint 2:** The shift value is 7 (each letter is shifted forward by 7 positions in the alphabet, so subtract 7 to decrypt).
3. **Hint 3:** The first word is a cybersecurity term for someone with internal access.

### Decryption Table (shift = 7)

```
Cipher:  A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
Plain:   T U V W X Y Z A B C D E F G H I J K L M N O P Q R S
```

---

## GM SOLUTION

**Answer:** `INSIDER THREAT DETECTED`

**Walkthrough (subtract 7 from each letter):**
```
P->I  U->N  Z->S  P->I  K->D  L->E  Y->R
(space)
A->T  O->H  Y->R  L->E  H->A  A->T
(space)
K->D  L->E  A->T  L->E  J->C  A->T  L->E  K->D
```

Result: `INSIDER THREAT DETECTED`

**SHA-256 hash of solution:**
`3b87da75fb4219c2349db051c93a0adb735e9654c6389d83a7090dc844040d9d`

### GM Setup -- API Call

```json
{
  "puzzle_type": "cipher",
  "clue": "Photographed note from SHADOWMERE officer's desk reads: PUZPKLY AOYLHA KLALJALK -- suspected Caesar substitution cipher. Frequency analysis shows L appears most often.",
  "solution": "INSIDER THREAT DETECTED",
  "reward_type": "phone_a_friend"
}
```
