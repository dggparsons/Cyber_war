"""Operation GHOSTLINE — built-in mega challenge.

A multi-stage APT incident investigation requiring SOC, IR, pentest,
red-team / threat-intel, and DFIR skills.  Five artifacts, five keywords,
one passphrase — and an insider-threat twist that ties the whole
narrative together.

Solution: BREACH-PIVOT-SHELL-STORM-GHOST
"""
from __future__ import annotations

MEGA_CHALLENGE_SOLUTION = "BREACH-PIVOT-SHELL-STORM-GHOST"

MEGA_CHALLENGE_REWARD_TIERS = [15, 10, 5, 5]

MEGA_CHALLENGE_DESCRIPTION = r"""## CLASSIFIED // OPERATION GHOSTLINE // TLP:RED

**INCIDENT BRIEFING — FOR IMMEDIATE ANALYSIS**

At 0214 UTC, automated detection flagged anomalous activity on host
WS-FIN042 in the Finance VLAN.  Initial triage suggests a sophisticated
threat actor with command-and-control capability already established
inside your network.

But something doesn't add up.

The attacker navigated directly to sensitive internal systems that
aren't discoverable from the outside.  They knew which hosts to
target, which credentials to use, and which monitoring gaps to
exploit.  Your CISO suspects an insider may be feeding intelligence
to the threat actor — or worse, the threat actor may BE an insider.

**YOUR MISSION:** Analyse the five evidence artifacts below.  Each
conceals a single **KEYWORD**.  Extract all five keywords and submit
them as a single passphrase to close the case.

> **Format:** `KEYWORD1-KEYWORD2-KEYWORD3-KEYWORD4-KEYWORD5`
> All uppercase, separated by hyphens.

Time is critical.  The attacker is still active.

---

### ARTIFACT 1 — SIEM ALERT TRIAGE  *(SOC Analyst)*

Your SIEM exported four events from WS-FIN042 within the incident
window.  Three are routine.  **One is the attacker.**

```
EVENT A — 02:13:55 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\svc_backup
  Process    : powershell.exe
  Parent     : taskschd.exe
  CommandLine: powershell.exe -ExecutionPolicy Bypass
               -File C:\Scripts\nightly_backup.ps1
  Analyst    : Scheduled nightly backup — runs every day at 02:13.

EVENT B — 02:14:12 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : wuauclt.exe
  Parent     : svchost.exe
  CommandLine: wuauclt.exe /detectnow /updatenow
  Analyst    : Windows Update detection cycle.

EVENT C — 02:14:33 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\svc_backup
  Process    : powershell.exe
  Parent     : cmd.exe
  CommandLine: powershell.exe -nop -w hidden -enc QgBSAEUAQQBDAEgA
  Analyst    : *** NO MATCHING SCHEDULED TASK ***

EVENT D — 02:14:41 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : sc.exe
  Parent     : services.exe
  CommandLine: sc.exe start spooler
  Analyst    : Print spooler service restart.
```

**Find the malicious event.**  What to look for:

- `-nop` (no profile) and `-w hidden` (hidden window) are evasion
  flags that wouldn't appear in a legitimate admin script
- The parent process is `cmd.exe`, not `taskschd.exe` — it was
  launched interactively, not from a scheduled task
- The same service account `svc_backup` runs both the legitimate
  backup (Event A) and the suspicious command — the attacker
  hijacked this account
- There is no scheduled task on record for this execution

The `-enc` parameter is **Base64-encoded UTF-16LE** — the standard
encoding PowerShell uses for `-EncodedCommand`.

Decode `QgBSAEUAQQBDAEgA`.

**The plaintext is KEYWORD 1.**

---

### ARTIFACT 2 — NETWORK TRAFFIC ANALYSIS  *(Incident Response)*

Firewall and DNS logs from the compromised VLAN.  There is a lot of
legitimate traffic here.  **Find the C2 communication and extract
the hidden data drop.**

```
Timestamp      Act    Proto  Source         Destination            Info
--------------------------------------------------------------------
02:13:01       ALLOW  TCP    10.0.4.217     20.190.159.2:443       login.microsoftonline.com
02:13:15       ALLOW  TCP    10.0.4.55      104.16.132.229:443     Cloudflare CDN
02:13:22       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS query (google.com)
02:14:02       ALLOW  TCP    10.0.4.217     20.191.45.212:443      Windows telemetry
02:14:33       ALLOW  TCP    10.0.4.217     45.33.32.156:443       *** SEE ANALYST NOTE ***
02:14:55       ALLOW  TCP    10.0.4.217     185.220.101.34:443     TLS handshake
02:15:01       ALLOW  TCP    10.0.4.217     185.220.101.34:8443    SYN -> ESTABLISHED
02:15:22       DNS    --     10.0.4.217     --                     A? cdn-update.darkpulse.io -> 185.220.101.34
02:16:44       ALLOW  TCP    10.0.4.217     10.0.1.5:445           SMB session
02:17:11       DENY   TCP    10.0.4.217     10.0.1.5:3389          RDP blocked by GPO
02:17:33       ALLOW  TCP    10.0.4.217     10.0.1.12:5985         WinRM session
02:18:02       ALLOW  TCP    10.0.1.12      10.0.2.8:22            SSH to Linux jump box
02:18:30       ALLOW  TCP    10.0.4.55      104.16.133.229:443     Cloudflare (continued)
02:19:15       ALLOW  TCP    10.0.2.8       185.220.101.34:443     *** SECOND C2 CALLBACK ***
02:19:44       ALLOW  TCP    10.0.4.217     20.190.159.2:443       Microsoft token refresh
```

> **Analyst note on 45.33.32.156:** This is `scanme.nmap.org`, used
> by your own vulnerability management scanner on a weekly schedule.
> It is **NOT** attacker infrastructure.  Do not pursue this lead.

**Key observation:** The attacker pivoted 10.0.4.217 → 10.0.1.12 →
10.0.2.8, and the final Linux box made its own callback to the C2.
The attacker already had SSH credentials for a server they shouldn't
know exists.  Keep this in mind.

Your DNS team pulled all TXT records for the C2 domain:

```
;; ANSWER SECTION:
cdn-update.darkpulse.io.  300  IN  A    185.220.101.34
cdn-update.darkpulse.io.  300  IN  TXT  "v=spf1 include:_spf.darkpulse.io ~all"
cdn-update.darkpulse.io.  300  IN  TXT  "google-site-verification=Xk7mQnR2pT0zA"
cdn-update.darkpulse.io.  300  IN  TXT  "5049564F54"
```

Three TXT records.  Two are standard (SPF policy, Google site
verification).  The third is a standalone value — a hex-encoded
dead drop for the implant.

**Decode the hex string `5049564F54` to ASCII.**

**The decoded text is KEYWORD 2.**

---

### ARTIFACT 3 — C2 SERVER RECONNAISSANCE  *(Penetration Tester)*

Your red team probed the C2 at 185.220.101.34 and captured these
response headers:

```
HTTP/1.1 200 OK
Server: Apache/2.4.49 (Unix)
X-Powered-By: PHP/7.4.3
X-Backend: PAN-OS GlobalProtect 10.2.2-h5
Content-Type: text/html; charset=UTF-8
Set-Cookie: SESSID=a8f3bc9d; Path=/; HttpOnly
```

**Three services are exposed.  Only one has a critical
actively-exploited RCE.**

| Service | Verdict |
|---------|---------|
| `Apache/2.4.49` | **VULNERABLE** — Critical path-traversal to RCE (CVSS 9.8), mass-exploited in late 2021.  CVE-2021-_____ |
| `PAN-OS 10.2.2-h5` | The base version was hit by CVE-2024-3400, but `-h5` = **Hotfix 5 applied**.  Patched.  Dead end. |
| `PHP/7.4.3` | End-of-life but no unauthenticated RCE at this version.  Not the way in. |

The C2 server's access log shows two requests during the incident.
**Only one is the path-traversal exploit.**

```
[02:20:11] "GET /cgi-bin/.%2e/.%2e/.%2e/.%2e/home/mhawkins/tools/%53%48%45%4C%4C HTTP/1.1" 200
[02:20:14] "POST /api/v2/agent/%46%4C%41%52%45/checkin HTTP/1.1" 200
```

The `/.%2e/.%2e/` directory-traversal pattern is the **signature of
CVE-2021-41773**.  The second request is a routine agent check-in on
the C2's REST API — not the exploit.

**URL-decode the final path component of the path-traversal
request.**

**The decoded text is KEYWORD 3.**

> Watch the traversal path closely: it reaches into
> `/home/mhawkins/tools/`.  That is an operator home directory on
> the C2 server.  **Remember this name.**

---

### ARTIFACT 4 — THREAT INTELLIGENCE  *(Red Team / Intel Analyst)*

Your threat-intel platform matched the C2 infrastructure to a tracked
campaign.  The adversary encrypts operational codenames in their
beacons using a **Vigenere cipher**.

```
========== CIRCL MISP FEED — EVENT 2024-18442 ==========
Adversary       : APT-7291
TLP             : AMBER
Confidence      : HIGH
IOCs            : 185.220.101.34, cdn-update.darkpulse.io
Campaign Cipher : SIHRB
Cipher Method   : Vigenere (standard, A=0)
Cipher Key      : APT
Compilation TS  : 2024-03-14T16:32:00-05:00
PDB Debug Path  : C:\Users\mhawkins\Dev\ghostline\beacon.pdb
=========================================================
```

**Decrypt the campaign name:** Apply Vigenere decryption to `SIHRB`
with key **APT**.

The key repeats: **A-P-T-A-P**.

Use CyberChef ("Vigenere Decode"), dcode.fr, or work it manually
(subtract key letter positions from cipher letter positions, mod 26).

**The decrypted campaign name is KEYWORD 4.**

> Now look at the rest of this intel.
>
> **Compilation timestamp:** 2024-03-14 at 16:32 EST.  A Tuesday
> afternoon.  Business hours at your HQ.
>
> **PDB debug path:** `C:\Users\mhawkins\Dev\ghostline\beacon.pdb`
>
> The same `mhawkins` from the C2 server's `/home/mhawkins/tools/`
> directory.  This malware was compiled on someone's work laptop.
> Someone inside your organisation built this tool.

---

### ARTIFACT 5 — MALWARE FORENSICS  *(DFIR / Reverse Engineer)*

Volatility extracted the beacon configuration from the WS-FIN042
memory dump:

```
========= BEACON CONFIG (imagebase 0x7FFA200) =========
beacon_type    : HTTPS
c2_server      : cdn-update.darkpulse.io
c2_port        : 8443
sleep_interval : 60
jitter_pct     : 15
xor_key        : 0x23
user_agent     : Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1)
spawn_to_x86   : %windir%\syswow64\rundll32.exe
spawn_to_x64   : %windir%\sysnative\rundll32.exe
campaign_tag   : 64 6B 6C 70 77   [XOR-ENCRYPTED]
watermark      : 0x5E8A1F00
named_pipe     : \\.\pipe\msagent_##
========================================================
```

The `campaign_tag` is **single-byte XOR encrypted** with the key in
`xor_key` (`0x23`).

XOR each byte with `0x23` and convert to ASCII:

```
0x64 XOR 0x23 = ?
0x6B XOR 0x23 = ?
0x6C XOR 0x23 = ?
0x70 XOR 0x23 = ?
0x77 XOR 0x23 = ?
```

**The decrypted campaign tag is KEYWORD 5.**

*Hint: CyberChef -> "From Hex" -> "XOR" with key
`{"option":"Hex","string":"23"}`*

---

### CASE FILE CLOSED

Assemble the evidence.

The PDB path names `mhawkins`.  The compilation timestamp places
the build during business hours at HQ.  The C2 tool directory is
`/home/mhawkins/`.  The hijacked service account `svc_backup`?
Hawkins administered it.  The SSH credentials for the Linux jump
box at 10.0.2.8?  Hawkins configured that server last quarter.

Cross-referencing HR records:

```
HAWKINS, MARCUS J.
Department  : Cyber Threat Intelligence
Clearance   : TS/SCI
Badge #     : 40771
Start Date  : 2019-06-03
Supervisor  : REDACTED
```

Your own Threat Intelligence analyst leveraged their clearance and
knowledge of your defensive monitoring to engineer an attack chain
designed to look like a foreign APT.

**GHOSTLINE was never an outside threat.  It was an inside job.**

---

### SUBMIT YOUR FINDINGS

> **KEYWORD1-KEYWORD2-KEYWORD3-KEYWORD4-KEYWORD5**
>
> All uppercase.  Hyphens between each word.  First team to submit
> the correct passphrase earns maximum influence for their nation.
""".strip()
