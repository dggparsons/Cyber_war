"""Pool of small intel-drop puzzles auto-assigned each round.

Each puzzle has:
  puzzle_type  — category label shown in the UI
  clue         — the text the player sees
  solution     — plaintext answer (case-insensitive matching)
  reward       — lifeline type awarded on solve
"""
from __future__ import annotations

INTEL_PUZZLE_POOL: list[dict] = [
    # ── Base64 ────────────────────────────────────────────────
    {"puzzle_type": "Signal Intercept", "clue": "Decoded radio burst (Base64):\n\n`U0hBRE9X`", "solution": "SHADOW", "reward": "phone_a_friend"},
    {"puzzle_type": "Signal Intercept", "clue": "Intercepted satellite uplink (Base64):\n\n`RklSRVdBTEw=`", "solution": "FIREWALL", "reward": "false_flag"},
    {"puzzle_type": "Signal Intercept", "clue": "Encrypted field report (Base64):\n\n`QkFDS0RPT1I=`", "solution": "BACKDOOR", "reward": "phone_a_friend"},
    {"puzzle_type": "Signal Intercept", "clue": "Captured beacon payload (Base64):\n\n`VFJPSkFO`", "solution": "TROJAN", "reward": "false_flag"},
    {"puzzle_type": "Signal Intercept", "clue": "Decoded embassy cable (Base64):\n\n`QUxMSUFOQ0U=`", "solution": "ALLIANCE", "reward": "phone_a_friend"},
    {"puzzle_type": "Signal Intercept", "clue": "Encrypted logistics channel (Base64):\n\n`U1RSSUtF`", "solution": "STRIKE", "reward": "false_flag"},
    {"puzzle_type": "Signal Intercept", "clue": "Monitoring station capture (Base64):\n\n`UEhJU0hJTkc=`", "solution": "PHISHING", "reward": "phone_a_friend"},
    {"puzzle_type": "Signal Intercept", "clue": "Covert ops broadcast (Base64):\n\n`UkFOU09N`", "solution": "RANSOM", "reward": "false_flag"},
    {"puzzle_type": "Signal Intercept", "clue": "Compromised relay (Base64):\n\n`Wk9NQklF`", "solution": "ZOMBIE", "reward": "phone_a_friend"},
    {"puzzle_type": "Signal Intercept", "clue": "Deep-cover agent burst (Base64):\n\n`U0FOQ1RJT04=`", "solution": "SANCTION", "reward": "false_flag"},

    # ── Hex ───────────────────────────────────────────────────
    {"puzzle_type": "Memory Dump", "clue": "Extracted from RAM dump:\n\n`4D414C57415245`", "solution": "MALWARE", "reward": "phone_a_friend"},
    {"puzzle_type": "Memory Dump", "clue": "Found in process memory:\n\n`50415443484544`", "solution": "PATCHED", "reward": "false_flag"},
    {"puzzle_type": "Memory Dump", "clue": "Registry artifact:\n\n`524F4F544B4954`", "solution": "ROOTKIT", "reward": "phone_a_friend"},
    {"puzzle_type": "Memory Dump", "clue": "Kernel memory string:\n\n`534E4946464552`", "solution": "SNIFFER", "reward": "false_flag"},
    {"puzzle_type": "Memory Dump", "clue": "Debug log extract:\n\n`5041594C4F4144`", "solution": "PAYLOAD", "reward": "phone_a_friend"},
    {"puzzle_type": "Memory Dump", "clue": "Stack trace artifact:\n\n`455850 4C4F4954`", "solution": "EXPLOIT", "reward": "false_flag"},
    {"puzzle_type": "Memory Dump", "clue": "Firmware image hex:\n\n`434F424 14C54`", "solution": "COBALT", "reward": "phone_a_friend"},
    {"puzzle_type": "Memory Dump", "clue": "Network buffer capture:\n\n`5448524541 54`", "solution": "THREAT", "reward": "false_flag"},
    {"puzzle_type": "Memory Dump", "clue": "Swap partition recovery:\n\n`564F4C54414745`", "solution": "VOLTAGE", "reward": "phone_a_friend"},
    {"puzzle_type": "Memory Dump", "clue": "Heap spray fragment:\n\n`43495048 4552`", "solution": "CIPHER", "reward": "false_flag"},

    # ── Caesar Cipher (shift 3) ───────────────────────────────
    {"puzzle_type": "Cipher Intercept", "clue": "Shift cipher detected (ROT-3):\n\n`EUHDFK`", "solution": "BREACH", "reward": "phone_a_friend"},
    {"puzzle_type": "Cipher Intercept", "clue": "Encrypted field note (ROT-3):\n\n`GHIHQVH`", "solution": "DEFENSE", "reward": "false_flag"},
    {"puzzle_type": "Cipher Intercept", "clue": "Agent dead-drop (ROT-3):\n\n`VKLHOG`", "solution": "SHIELD", "reward": "phone_a_friend"},
    {"puzzle_type": "Cipher Intercept", "clue": "Embassy cipher (ROT-3):\n\n`VXUYHLOODQFH`", "solution": "SURVEILLANCE", "reward": "false_flag"},
    {"puzzle_type": "Cipher Intercept", "clue": "Border patrol intercept (ROT-3):\n\n`GHWHFW`", "solution": "DETECT", "reward": "phone_a_friend"},
    {"puzzle_type": "Cipher Intercept", "clue": "Classified memo (ROT-3):\n\n`SUREH`", "solution": "PROBE", "reward": "false_flag"},
    {"puzzle_type": "Cipher Intercept", "clue": "Covert channel (ROT-3):\n\n`YHFWRU`", "solution": "VECTOR", "reward": "phone_a_friend"},
    {"puzzle_type": "Cipher Intercept", "clue": "Tactical dispatch (ROT-3):\n\n`DQRPDOB`", "solution": "ANOMALY", "reward": "false_flag"},
    {"puzzle_type": "Cipher Intercept", "clue": "Intelligence briefing (ROT-3):\n\n`SLYRW`", "solution": "PIVOT", "reward": "phone_a_friend"},
    {"puzzle_type": "Cipher Intercept", "clue": "Field operative note (ROT-3):\n\n`IRUHQVLFV`", "solution": "FORENSICS", "reward": "false_flag"},

    # ── Binary ────────────────────────────────────────────────
    {"puzzle_type": "Binary Fragment", "clue": "Recovered from corrupted drive:\n\n`01000001 01010100 01010100 01000001 01000011 01001011`", "solution": "ATTACK", "reward": "phone_a_friend"},
    {"puzzle_type": "Binary Fragment", "clue": "Embedded in firmware:\n\n`01000100 01000101 01001110 01011001`", "solution": "DENY", "reward": "false_flag"},
    {"puzzle_type": "Binary Fragment", "clue": "Steganography extract:\n\n`01010011 01010000 01001111 01001111 01000110`", "solution": "SPOOF", "reward": "phone_a_friend"},
    {"puzzle_type": "Binary Fragment", "clue": "Boot sector artifact:\n\n`01010111 01001111 01010010 01001101`", "solution": "WORM", "reward": "false_flag"},
    {"puzzle_type": "Binary Fragment", "clue": "BIOS dump extract:\n\n`01010000 01001000 01000001 01010011 01000101`", "solution": "PHASE", "reward": "phone_a_friend"},
    {"puzzle_type": "Binary Fragment", "clue": "Flash memory recovery:\n\n`01000100 01000101 01000011 01001111 01011001`", "solution": "DECOY", "reward": "false_flag"},
    {"puzzle_type": "Binary Fragment", "clue": "Radio protocol bits:\n\n`01001010 01000001 01001101`", "solution": "JAM", "reward": "phone_a_friend"},
    {"puzzle_type": "Binary Fragment", "clue": "Satellite telemetry:\n\n`01010010 01000101 01000011 01001111 01001110`", "solution": "RECON", "reward": "false_flag"},
    {"puzzle_type": "Binary Fragment", "clue": "USB implant payload:\n\n`01000010 01001100 01001111 01000011 01001011`", "solution": "BLOCK", "reward": "phone_a_friend"},
    {"puzzle_type": "Binary Fragment", "clue": "Drone control packet:\n\n`01000001 01000010 01001111 01010010 01010100`", "solution": "ABORT", "reward": "false_flag"},

    # ── URL Encode ────────────────────────────────────────────
    {"puzzle_type": "Web Traffic", "clue": "Suspicious GET parameter:\n\n`%41%43%43%45%53%53`", "solution": "ACCESS", "reward": "phone_a_friend"},
    {"puzzle_type": "Web Traffic", "clue": "Hidden form field value:\n\n`%49%4E%4A%45%43%54`", "solution": "INJECT", "reward": "false_flag"},
    {"puzzle_type": "Web Traffic", "clue": "Exfil URL path segment:\n\n`%54%55%4E%4E%45%4C`", "solution": "TUNNEL", "reward": "phone_a_friend"},
    {"puzzle_type": "Web Traffic", "clue": "Cookie value decoded:\n\n`%42%59%50%41%53%53`", "solution": "BYPASS", "reward": "false_flag"},
    {"puzzle_type": "Web Traffic", "clue": "API key fragment:\n\n`%54%4F%4B%45%4E`", "solution": "TOKEN", "reward": "phone_a_friend"},
    {"puzzle_type": "Web Traffic", "clue": "Redirect chain terminal:\n\n`%50%48%41%4E%54%4F%4D`", "solution": "PHANTOM", "reward": "false_flag"},
    {"puzzle_type": "Web Traffic", "clue": "POST body decode:\n\n`%53%50%4C%49%43%45`", "solution": "SPLICE", "reward": "phone_a_friend"},
    {"puzzle_type": "Web Traffic", "clue": "WebSocket payload:\n\n`%42%45%41%43%4F%4E`", "solution": "BEACON", "reward": "false_flag"},
    {"puzzle_type": "Web Traffic", "clue": "DNS TXT record value:\n\n`%4F%52%41%43%4C%45`", "solution": "ORACLE", "reward": "phone_a_friend"},
    {"puzzle_type": "Web Traffic", "clue": "Proxy log artifact:\n\n`%53%48%45%4C%4C`", "solution": "SHELL", "reward": "false_flag"},

    # ── Reverse String ────────────────────────────────────────
    {"puzzle_type": "Obfuscated Log", "clue": "Reversed string found in syslog:\n\n`ROODKCAB`", "solution": "BACKDOOR", "reward": "phone_a_friend"},
    {"puzzle_type": "Obfuscated Log", "clue": "Mirror text in crash dump:\n\n`TIOLPXE`", "solution": "EXPLOIT", "reward": "false_flag"},
    {"puzzle_type": "Obfuscated Log", "clue": "Inverted auth log entry:\n\n`HCNUAL`", "solution": "LAUNCH", "reward": "phone_a_friend"},
    {"puzzle_type": "Obfuscated Log", "clue": "Reversed DNS query:\n\n`RETLIF`", "solution": "FILTER", "reward": "false_flag"},
    {"puzzle_type": "Obfuscated Log", "clue": "Flipped audit trail:\n\n`KCOLDAED`", "solution": "DEADLOCK", "reward": "phone_a_friend"},
    {"puzzle_type": "Obfuscated Log", "clue": "Reversed process name:\n\n`TSOHG`", "solution": "GHOST", "reward": "false_flag"},
    {"puzzle_type": "Obfuscated Log", "clue": "Mirror malware sample:\n\n`ERIF`", "solution": "FIRE", "reward": "phone_a_friend"},
    {"puzzle_type": "Obfuscated Log", "clue": "Inverted C2 beacon:\n\n`ROTINOM`", "solution": "MONITOR", "reward": "false_flag"},
    {"puzzle_type": "Obfuscated Log", "clue": "Reversed registry key:\n\n`TPYRC`", "solution": "CRYPT", "reward": "phone_a_friend"},
    {"puzzle_type": "Obfuscated Log", "clue": "Backwards event ID:\n\n`EGATOBAS`", "solution": "SABOTAGE", "reward": "false_flag"},

    # ── Asset-Pack Puzzles (match assets/intel_samples/) ─────
    # These are higher-difficulty puzzles that correspond to the
    # detailed write-ups in the asset pack markdown files.

    # cipher_hex.md — Multi-word hex decode
    {
        "puzzle_type": "Satellite Intercept",
        "clue": "Intercepted hex payload from IRONVEIL satellite uplink. The burst was embedded in telemetry handshake data:\n\n`4F5045524154494F4E20424C41434B4F5554`\n\nConvert each hex pair to ASCII. Note: `0x20` = space.",
        "solution": "OPERATION BLACKOUT",
        "reward": "false_flag",
        "difficulty": "easy-medium",
        "asset_ref": "assets/intel_samples/cipher_hex.md",
    },

    # cipher_substitution.md — Caesar shift +7
    {
        "puzzle_type": "HUMINT Intercept",
        "clue": "Photographed note from SHADOWMERE officer's desk:\n\n`PUZPKLY AOYLHA KLALJALK`\n\nSuspected monoalphabetic substitution. Frequency analysis shows 'L' appears 4 times — in English the most common letter is E.",
        "solution": "INSIDER THREAT DETECTED",
        "reward": "phone_a_friend",
        "difficulty": "medium",
        "asset_ref": "assets/intel_samples/cipher_substitution.md",
    },

    # cipher_vigenere.md — Vigenere with key CIPHER
    {
        "puzzle_type": "COMINT Intercept",
        "clue": "Encrypted transmission from IRONVEIL proxy relay:\n\n`NIJUGY UMFBIEEM PSTYC`\n\nAnalyst note recovered from operator terminal: \"Key is CIPHER\" (Vigenere). Spaces are preserved; key advances only on letters.",
        "solution": "LAUNCH SEQUENCE ALPHA",
        "reward": "false_flag",
        "difficulty": "hard",
        "asset_ref": "assets/intel_samples/cipher_vigenere.md",
    },

    # stego_base64.md — Base64 hidden in diplomatic cable
    {
        "puzzle_type": "OSINT Collection",
        "clue": "CORALHAVEN diplomatic communique No. 2026-0147 has a suspicious archive reference field:\n\n`Q1JJVElDQUwgVlVMTkVSQUJJTElUWQ==`\n\nThis does not match their standard reference format (CH-YYYY-NNNNN). The trailing `==` is a Base64 padding signature.",
        "solution": "CRITICAL VULNERABILITY",
        "reward": "phone_a_friend",
        "difficulty": "medium",
        "asset_ref": "assets/intel_samples/stego_base64.md",
    },

    # stego_metadata.md — Hex hidden in EXIF Artist field
    {
        "puzzle_type": "Digital Forensics",
        "clue": "Seized laptop image has anomalous EXIF metadata. All fields match Samsung Galaxy S24 Ultra defaults except:\n\n`Artist: 455846494C5452415445`\n\nSamsung phones do not populate the Artist field. This value appears to be hex-encoded ASCII.",
        "solution": "EXFILTRATE",
        "reward": "false_flag",
        "difficulty": "medium-hard",
        "asset_ref": "assets/intel_samples/stego_metadata.md",
    },
]

# Verify we have enough for 10 teams × 6 rounds
assert len(INTEL_PUZZLE_POOL) >= 60, f"Need ≥60 puzzles, have {len(INTEL_PUZZLE_POOL)}"
