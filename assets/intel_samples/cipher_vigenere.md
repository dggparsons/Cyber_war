# Intel Drop: Vigenere Cipher

**Puzzle Type:** Cipher
**Difficulty:** Hard
**Category:** Polyalphabetic Cryptography

---

## CLASSIFIED -- COMINT INTERCEPT REPORT

**From:** GCHQ Bude Station -- ECHELON Watch
**To:** Joint Cyber Command, Strategic Intelligence Division
**Priority:** FLASH

Our SIGINT collection platform intercepted an encrypted transmission from
an unknown proxy relay operating on a frequency associated with IRONVEIL's
covert operations network. A partial key was recovered from a compromised
operator terminal. The analyst's marginal note reads:

> "Key recovered from operator's notebook: **CIPHER**"

### Intercepted Ciphertext

```
NIJUGY UMFBIEEM PSTYC
```

### Analyst Notes

- This is a Vigenere cipher -- a polyalphabetic substitution.
- The key word is **CIPHER** (6 letters), repeating across the plaintext.
- Spaces in the ciphertext correspond to spaces in the plaintext.
- Only alphabetic characters are enciphered; spaces pass through unchanged.
- The key only advances on alphabetic characters.

### Vigenere Decryption Method

For each letter in the ciphertext:
1. Find the corresponding key letter (cycling through C-I-P-H-E-R).
2. Subtract the key letter's position from the ciphertext letter's position (mod 26).
3. `plaintext = (ciphertext - key) mod 26`

### Worked Example (first 3 letters)

```
Ciphertext:  N  I  J
Key:         C  I  P
Key values:  2  8  15

N(13) - C(2)  = 11 = L
I(8)  - I(8)  = 0  = A
J(9)  - P(15) = -6 mod 26 = 20 = U
```

### Hints (reveal progressively if team is stuck)

1. **Hint 1:** The key is CIPHER. Write it repeating under the ciphertext, skipping spaces.
2. **Hint 2:** The first word decrypts to a 6-letter word meaning "to initiate" or "to send off".
3. **Hint 3:** The full plaintext is a military command phrase in three words.

---

## GM SOLUTION

**Answer:** `LAUNCH SEQUENCE ALPHA`

**Full Decryption:**
```
Ciphertext: N  I  J  U  G  Y     U  M  F  B  I  E  E  M     P  S  T  Y  C
Key:        C  I  P  H  E  R     C  I  P  H  E  R  C  I     P  H  E  R  C
Key vals:   2  8  15 7  4  17    2  8  15 7  4  17 2  8     15 7  4  17 2

N(13)-C(2) =11=L    U(20)-C(2) =18=S    P(15)-P(15)=0 =A
I(8) -I(8) =0 =A    M(12)-I(8) =4 =E    S(18)-H(7) =11=L
J(9) -P(15)=20=U    F(5) -P(15)=16=Q    T(19)-E(4) =15=P
U(20)-H(7) =13=N    B(1) -H(7) =20=U    Y(24)-R(17)=7 =H
G(6) -E(4) =2 =C    I(8) -E(4) =4 =E    C(2) -C(2) =0 =A
Y(24)-R(17)=7 =H    E(4) -R(17)=13=N
                     E(4) -C(2) =2 =C
                     M(12)-I(8) =4 =E
```

Result: `LAUNCH SEQUENCE ALPHA`

**SHA-256 hash of solution:**
`8f667d56b619aab595ef8b39863b72e0a8430eb17fdf7ea965316ee4ff9a59d4`

### GM Setup -- API Call

```json
{
  "puzzle_type": "cipher",
  "clue": "Intercepted encrypted transmission: NIJUGY UMFBIEEM PSTYC -- recovered key from operator notebook: CIPHER (Vigenere)",
  "solution": "LAUNCH SEQUENCE ALPHA",
  "reward_type": "false_flag"
}
```
