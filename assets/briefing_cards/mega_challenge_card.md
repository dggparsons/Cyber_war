# Briefing Card: Mega Challenge

```
+--------------------------------------------------+
|  [TOP SECRET]     MEGA CHALLENGE BRIEFING         |
|                                                    |
|     ///  OPERATION DAWNSHIELD  \\\                  |
|                                                    |
|  "The ultimate test of your collective skill."     |
+--------------------------------------------------+
```

---

## What Is the Mega Challenge?

The **Mega Challenge** is a multi-stage, shared puzzle that becomes
available during the later rounds of the game. Unlike standard intel
drops (which are assigned per-team), the Mega Challenge is a single
high-difficulty puzzle accessible to ALL teams simultaneously.

It is a race: the first team to solve all stages claims the top
reward tier, the second team gets the next tier, and so on.

### Story Hook

> An unknown threat actor has deployed a sophisticated malware framework
> across critical infrastructure in multiple nations. A partial config
> file has been recovered, but it is encrypted. Your team must solve a
> chain of puzzles to decrypt the config, identify the kill-switch
> domain, and neutralize the threat before your rivals do.

---

## Challenge Stages

### Stage 1: Cipher Layer

**Type:** Vigenere Cipher
**Difficulty:** Hard

Your team receives an encrypted string and a hint pointing to the
key. Decrypt the Vigenere cipher to reveal a URL or passphrase that
unlocks Stage 2.

- The key word is thematically related to the game (e.g., "DAWNSHIELD").
- Teams must demonstrate knowledge of polyalphabetic decryption.
- Partial credit is not awarded -- you need the full plaintext.

### Stage 2: Steganography Layer

**Type:** Base64 / Hidden Data
**Difficulty:** Hard

The output from Stage 1 leads to a document, image description, or
data dump. Somewhere within it, a Base64-encoded message is hidden.

- Teams must identify which part of the data is anomalous.
- Decode the Base64 to obtain coordinates, a passphrase, or a
  configuration key.
- Red herrings may be present -- not every encoded-looking string
  is the answer.

### Stage 3: Malware Config Analysis

**Type:** Technical Analysis
**Difficulty:** Expert

The passphrase from Stage 2 unlocks a JSON "malware configuration"
file. Teams must analyze the config to identify the **kill-switch
domain** -- the domain that, when resolved, causes the malware to
self-destruct.

- The config contains multiple domains, IPs, and parameters.
- Teams must identify which field is the kill-switch based on
  malware analysis conventions (e.g., the domain checked before
  execution begins).
- Submit the kill-switch domain as the final answer.

---

## Reward Tiers

Rewards are assigned based on solve order across all teams:

| Place | Influence | Lifeline Reward          | Bonus                    |
|-------|-----------|--------------------------|--------------------------|
| 1st   | +15       | False Flag token         | Public shout-out + trophy |
| 2nd   | +10       | Phone-a-Friend token     | --                        |
| 3rd   | +5        | +2 Defense buff (1 round)| --                        |
| 4th+  | +2        | --                       | --                        |

### Important Notes on Rewards

- Influence points are added to your team's score immediately upon
  verified solve.
- Lifeline tokens are usable in any subsequent round.
- The defense buff (+2 to defense stat) lasts for one round only.
- Teams that do not solve the Mega Challenge receive nothing but
  can still win the overall game through other means.

---

## Competitive Element

### The Race

- All teams receive the Stage 1 puzzle at the same time.
- There is no turn order -- it is pure speed and skill.
- The GM announces each solve in the world news feed:
  > "IRONVEIL has cracked Stage 1 of the Mega Challenge!"
- This creates psychological pressure on remaining teams.

### Collaboration vs. Competition

- Teams may attempt to trade partial solutions through diplomacy,
  but this is risky: sharing Stage 1 answers helps a rival reach
  Stage 2 faster.
- Allied teams could theoretically divide and conquer (one team
  focuses on Stage 1, the other on Stage 2 prep), but the reward
  structure incentivizes individual team completion.

### Timing

- The Mega Challenge typically opens in **Round 3 or 4** (GM
  discretion).
- Teams must balance Mega Challenge efforts with their normal
  round proposals, voting, and diplomacy.
- There is no time limit on the Mega Challenge beyond the end of
  the game itself.

---

## Tips for Teams

1. **Assign a puzzle specialist.** Designate 1-2 team members to
   focus on the Mega Challenge while others handle round strategy.

2. **Do not neglect your round.** The Mega Challenge is valuable
   but not worth losing a critical round over. Balance your effort.

3. **Stage 1 is the bottleneck.** Most teams get stuck here. If
   you have cryptography experience, lead with that.

4. **Document everything.** Write down partial solutions, failed
   attempts, and key observations. The stages build on each other.

5. **Watch the news feed.** If another team solves Stage 1, the
   pressure is on. Decide whether to accelerate your Mega Challenge
   effort or pivot to round strategy.

---

## GM Notes

### Setup

- Prepare the three-stage puzzle chain before the game.
- Use the `mega_challenge_outline.md` in `assets/intel_samples/` as
  the reference for puzzle content.
- Distribute Stage 1 to all teams simultaneously via the admin panel.
- Manually verify Stage 2 and Stage 3 submissions (or use the
  solution hash in the API).

### Pacing

- If no team has solved Stage 1 after 15 minutes, consider releasing
  an additional hint.
- If multiple teams are stuck on Stage 2, the GM may broadcast a
  general hint to all teams.
- The Mega Challenge should not overshadow the core game loop --
  keep it as an exciting side quest, not a mandatory grind.

---

```
+--------------------------------------------------+
|  Classification: ALL TEAMS                        |
|  This briefing is shared with every team at       |
|  Mega Challenge launch.                           |
+--------------------------------------------------+
```
