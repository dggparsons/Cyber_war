"""Pool of intel-drop puzzles auto-assigned each round.

Each puzzle is TWO stages:
  Stage 1 — Technical decode (encoding method not disclosed)
  Stage 2 — The decoded text is a riddle requiring domain knowledge

Each puzzle has:
  puzzle_type  — category label shown in the UI
  clue         — the text the player sees (encoded payload + context)
  solution     — plaintext answer (case-insensitive matching)
  reward       — lifeline type awarded on solve
"""
from __future__ import annotations

INTEL_PUZZLE_POOL: list[dict] = [

    # ── 1. Base64 → Identify the tool ────────────────────────────
    {
        "puzzle_type": "Signal Intercept",
        "clue": (
            "Intercepted encoded transmission from hostile SIGINT relay. "
            "The payload was embedded in a covert channel burst:\n\n"
            "```\n"
            "Q3JlYXRlZCBieSBCZW5qYW1pbiBEZWxweSBha2EgZ2VudGlsa2l3aS4g\n"
            "SSBkdW1wIGNyZWRlbnRpYWxzIGZyb20gTFNBU1MgbWVtb3J5LiBEQ1N5\n"
            "bmMgYW5kIFBhc3MtdGhlLUhhc2ggYXJlIG15IHNwZWNpYWx0aWVzLiBL\n"
            "aXdpIGlzIG15IG1hc2NvdC4gTmFtZSB0aGUgdG9vbC4=\n"
            "```\n\n"
            "Decode the message. The answer is **not** the decoded text — "
            "it is what the decoded text describes."
        ),
        "solution": "MIMIKATZ",
        "reward": "phone_a_friend",
    },

    # ── 2. Hex → Identify the vulnerability ──────────────────────
    {
        "puzzle_type": "Memory Dump",
        "clue": (
            "Extracted from volatile memory during incident response. "
            "Raw bytes recovered from process heap:\n\n"
            "```\n"
            "43 56 45 2D 32 30 31 34 2D 30 31 36 30 2E 20 41\n"
            "20 6D 69 73 73 69 6E 67 20 62 6F 75 6E 64 73 20\n"
            "63 68 65 63 6B 20 69 6E 20 4F 70 65 6E 53 53 4C\n"
            "27 73 20 68 65 61 72 74 62 65 61 74 20 65 78 74\n"
            "65 6E 73 69 6F 6E 20 6C 65 61 6B 65 64 20 73 65\n"
            "72 76 65 72 20 6D 65 6D 6F 72 79 20 74 6F 20 61\n"
            "6E 79 20 61 74 74 61 63 6B 65 72 2E 20 4D 69 6C\n"
            "6C 69 6F 6E 73 20 6F 66 20 70 72 69 76 61 74 65\n"
            "20 6B 65 79 73 20 65 78 70 6F 73 65 64 2E 20 4E\n"
            "61 6D 65 20 74 68 69 73 20 76 75 6C 6E 65 72 61\n"
            "62 69 6C 69 74 79 2E\n"
            "```\n\n"
            "Decode the data. Then identify what it describes."
        ),
        "solution": "HEARTBLEED",
        "reward": "false_flag",
    },

    # ── 3. Caesar cipher (unknown shift) → Identify the exploit ──
    {
        "puzzle_type": "Cipher Intercept",
        "clue": (
            "Encrypted field communication intercepted from hostile "
            "operator. Substitution cipher suspected:\n\n"
            "```\n"
            "ZF17-010. Gur Funqbj Oebxref fgbyr zr sebz gur AFN'f\n"
            "Rdhngvba Tebhc. V gnetrg FZOi1 ba cbeg 445. JnaanPel\n"
            "naq AbgCrgln jrncbavfrq zr. Anzr gur rkcybvg.\n"
            "```\n\n"
            "Decrypt the message, then identify what it describes."
        ),
        "solution": "ETERNALBLUE",
        "reward": "phone_a_friend",
    },

    # ── 4. XOR encrypted → Identify the attack technique ─────────
    {
        "puzzle_type": "Malware Config",
        "clue": (
            "Encrypted string extracted from a beacon's configuration "
            "data. Single-byte encryption suspected. The key has not "
            "been recovered:\n\n"
            "```\n"
            "0f 0b 16 10 07 62 16 73 77 77 7a 6c 72 72 71 6c\n"
            "62 0b 62 30 27 33 37 27 31 36 62 31 27 30 34 2b\n"
            "21 27 62 36 2b 21 29 27 36 31 62 24 2d 30 62 11\n"
            "12 0c 31 62 36 2a 27 2c 62 21 30 23 21 29 62 36\n"
            "2a 27 2f 62 2d 24 24 2e 2b 2c 27 6c 62 0c 2d 62\n"
            "23 26 2f 2b 2c 62 2c 27 27 26 27 26 6c 62 0b 2f\n"
            "32 23 21 29 27 36 62 05 27 36 17 31 27 30 11 12\n"
            "0c 31 62 23 37 36 2d 2f 23 36 27 31 62 2f 27 6c\n"
            "62 0c 23 2f 27 62 36 2a 27 62 23 36 36 23 21 29 6c\n"
            "```\n\n"
            "Recover the key, decrypt the message, then identify "
            "the attack described."
        ),
        "solution": "KERBEROASTING",
        "reward": "false_flag",
    },

    # ── 5. Vigenere (key from context) → Identify the tool ───────
    {
        "puzzle_type": "COMINT Intercept",
        "clue": (
            "Encrypted dispatch from DARKPULSE field operator. Polyalphabetic "
            "cipher confirmed. Analyst note indicates the key is the "
            "five-letter word for the domain this war is fought in:\n\n"
            "```\n"
            "K KBT RERJZV FGSITVMSC RVRBGB RYULJ WQJRX IPBTY\n"
            "VFFSIA. QIEIRFPYEF GT QP EMMPVERPV. EGM4K MJ OW\n"
            "EEKCZBWV. C FVRKKLH HFI LBQVF KF.\n"
            "```\n\n"
            "Derive the key, decrypt, then identify the tool described."
        ),
        "solution": "BLOODHOUND",
        "reward": "phone_a_friend",
    },

    # ── 6. Multi-layer encoding → Identify the protocol ──────────
    {
        "puzzle_type": "Deep Forensics",
        "clue": (
            "Multi-layer encoded artifact recovered from attacker's staging "
            "server. At least two encoding layers are present. Peel them "
            "back to reveal the clue:\n\n"
            "```\n"
            "NTA2ZjcyNzQyMDM4MzgyZTIwNTQ0NzU0MjA2MTZlNjQyMDU0\n"
            "NDc1MzIwNzQ2OTYzNmI2NTc0NzMyZTIwNDc2ZjZjNjQ2NTZl\n"
            "MjA3NDY5NjM2YjY1NzQ3MzIwNjY2ZjcyNjc2NTIwNmQ3OTIw\n"
            "NzQ2ZjZiNjU2ZTczMmUyMDUzNjk2Yzc2NjU3MjIwNzQ2OTYz\n"
            "NmI2NTc0NzMyMDc0NjE3MjY3NjU3NDIwNzM2NTcyNzY2OTYz\n"
            "NjU3MzJlMjA1NzY5NmU2NDZmNzc3MzIwNjQ2ZjZkNjE2OTZl\n"
            "MjA2MTc1NzQ2ODY1NmU3NDY5NjM2MTc0Njk2ZjZlMjA2NDY1\n"
            "NzA2NTZlNjQ3MzIwNmY2ZTIwNmQ2NTJl\n"
            "```\n\n"
            "Decode all layers. The answer is what the final "
            "plaintext describes."
        ),
        "solution": "KERBEROS",
        "reward": "false_flag",
    },
]

assert len(INTEL_PUZZLE_POOL) >= 6, f"Need ≥6 puzzles, have {len(INTEL_PUZZLE_POOL)}"
