"""
TOMMY Demo Runner
==================
Plays through a scripted showcase of TOMMY features, one command at a time.
Each command waits for TOMMY to FINISH SPEAKING before the next one fires.

Usage:
    py -3.11 demo.py            # full ~3 minute demo
    py -3.11 demo.py --short    # short ~90 second highlight reel
    py -3.11 demo.py --cyber    # cyber-focused (good for LinkedIn cybersec angle)

Press Ctrl+C at any time to abort.
"""

import sys
import json
import time
import urllib.request

BASE = "http://localhost:8888"

# ── ANSI colours (auto-enabled on Win10+) ───────────────────
import os
os.system("")

C = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "white":   "\033[97m",
    "cyan":    "\033[96m",
    "magenta": "\033[95m",
    "green":   "\033[92m",
    "orange":  "\033[93m",
    "red":     "\033[91m",
    "gray":    "\033[90m",
}


def http(method, path, body=None, timeout=60):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def status():
    try:
        return http("GET", "/api/status", timeout=4)
    except Exception:
        return {}


def chat(text):
    return http("POST", "/api/chat", {
        "messages": [{"role": "user", "content": text}],
        "source": "voice",
    }, timeout=90)


def wait_for_speak_end(max_wait=60):
    """Block while TOMMY is speaking. Returns when speaking==False."""
    # Allow up to 4s for speech to BEGIN
    deadline = time.time() + 4
    while time.time() < deadline:
        if status().get("speaking"):
            break
        time.sleep(0.12)
    # Then wait for speech to END
    spinner = ["⢿","⣻","⣽","⣾","⣷","⣯","⣟","⡿"]
    i = 0
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if not status().get("speaking"):
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()
            return True
        sys.stdout.write(
            f"\r{C['gray']}  {spinner[i % len(spinner)]} TOMMY speaking…{C['reset']}"
        )
        sys.stdout.flush()
        i += 1
        time.sleep(0.13)
    sys.stdout.write("\r" + " " * 50 + "\r"); sys.stdout.flush()
    return False


def banner():
    print(C["bold"] + C["magenta"])
    print("═" * 72)
    print("           T . O . M . M . Y .   —   DEMO RUNNER")
    print("═" * 72)
    print(C["reset"])
    print(f"  {C['gray']}Each command waits for TOMMY to finish speaking before the next.")
    print(f"  Press Ctrl+C to abort.{C['reset']}")
    print()


def section(idx, total, title):
    print()
    print(f"{C['bold']}{C['magenta']}╭{'─'*70}╮{C['reset']}")
    print(f"{C['bold']}{C['magenta']}│  STEP {idx:>2}/{total}  {C['white']}{title:<54}{C['magenta']}│{C['reset']}")
    print(f"{C['bold']}{C['magenta']}╰{'─'*70}╯{C['reset']}")


def narrate(text):
    print(f"{C['gray']}  ▸ {text}{C['reset']}")


def run(text, show_reply=True, max_wait=60):
    print(f"  {C['cyan']}{C['bold']}YOU   →{C['reset']}  {text}")
    try:
        r = chat(text)
    except Exception as e:
        print(f"  {C['red']}✗ request failed: {e}{C['reset']}")
        return
    if show_reply:
        src = r.get("source", "?")
        reply = (r.get("reply", "") or "").strip()
        # Strip code fences for cleaner console — TOMMY still shows them in the UI
        compact = " ".join(reply.split())[:280]
        tag = "ai" if src == "ai" else "loc"
        tag_col = C["orange"] if src == "ai" else C["green"]
        print(f"  {tag_col}{C['bold']}TOMMY← [{tag}]{C['reset']}  {compact}")
    wait_for_speak_end(max_wait=max_wait)


def pause(sec):
    time.sleep(sec)


# ══════════════════════════════════════════════════════════════════
# DEMO SEQUENCES
# ══════════════════════════════════════════════════════════════════

SEQUENCES = {

    "full": [
        ("OPENING — HUMANIZED GREETING",
         "TOMMY introduces itself in a natural, varied way",
         ["hi"]),

        ("LOCAL HANDLERS (zero API cost)",
         "Instant answers from local code — no LLM round-trip",
         ["what time is it",
          "system info",
          "weather"]),

        ("GOOGLE CALENDAR + GMAIL (OAuth)",
         "Reads real events and important unread mail (Primary inbox only)",
         ["what is on my calendar",
          "check gmail"]),

        ("CYBERSEC — HASH TOOLS",
         "MD5, identify, NTLM — all via Python stdlib + cybertools",
         ["md5 of admin123",
          "identify hash 5f4dcc3b5aa765d61d8327deb882cf99",
          "ntlm of password123"]),

        ("CYBERSEC — RECON + INTEL",
         "Live CVE feed (NVD) + GitHub dorks",
         ["recent critical cves",
          "github dorks for example.com"]),

        ("CYBERSEC — REVERSE SHELL PAYLOAD",
         "Generated payload appears as a copyable code block in the UI",
         ["reverse shell python 10.10.14.5 4444"]),

        ("ENCODING / DECODING",
         "Built-in codecs without leaving TOMMY",
         ["base64 encode TOMMY online and operational",
          "rot13 hello world"]),

        ("DPAPI PASSWORD VAULT",
         "Encrypted with your Windows user account — no master password",
         ["save my demo password as DemoTr0n2026",
          "what is my demo password"]),

        ("AI + WEB SEARCH",
         "Groq LLaMA 3.3 70B with live DuckDuckGo result injection",
         ["what is the latest news on AI agents"]),

        ("TASKS, NOTES, MEMORY",
         "Persistent personal assistant features",
         ["add task ship TOMMY to GitHub tonight",
          "take a note TOMMY demo recorded for LinkedIn",
          "remember I prefer the smart model llama 3.3 70b"]),

        ("WORKFLOW MODES",
         "Single phrase fires a multi-step action chain",
         ["ctf mode"]),

        ("CLOSING",
         "Demo complete",
         ["thanks TOMMY"]),
    ],

    "short": [
        ("WAKE + GREETING",
         "Natural humanized opener",
         ["hi"]),
        ("CALENDAR",
         "Real Google Calendar data",
         ["what is on my calendar"]),
        ("CYBER",
         "Hash + CVE + reverse shell payload",
         ["md5 of admin123",
          "reverse shell python 10.10.14.5 4444"]),
        ("VAULT",
         "DPAPI-encrypted password store",
         ["save my demo password as DemoTr0n2026",
          "what is my demo password"]),
        ("WORKFLOW",
         "CTF mode fires a chain of actions",
         ["ctf mode"]),
        ("CLOSE",
         "Note for the LinkedIn post",
         ["take a note TOMMY demo recorded"]),
    ],

    "cyber": [
        ("OPENING",
         "Just TOMMY doing its thing",
         ["hi"]),
        ("HASH ID + GENERATION",
         "MD5, identify, NTLM — all local",
         ["md5 of admin123",
          "identify hash 5f4dcc3b5aa765d61d8327deb882cf99",
          "ntlm of password123",
          "sha256 of CTF{flag_here}"]),
        ("ENCODING",
         "Codec swiss army knife",
         ["base64 encode the eagle has landed",
          "rot13 plaintext",
          "decode base64 SkFSVklTIGlzIG9ubGluZQ=="]),
        ("CVE INTEL (live NVD)",
         "Lookup + recent critical feed",
         ["lookup CVE-2024-3094",
          "recent critical cves"]),
        ("RECON",
         "DNS, headers, IP, subdomains",
         ["what is my ip",
          "ip info",
          "dns google.com",
          "headers for example.com"]),
        ("REVERSE SHELL ARSENAL",
         "Payloads in 4 languages — each is a copyable code block",
         ["reverse shell python 10.10.14.5 4444",
          "reverse shell powershell 10.10.14.5 4444",
          "reverse shell bash 10.10.14.5 4444",
          "reverse shell perl 10.10.14.5 4444"]),
        ("CLOSE",
         "Vault save",
         ["save my htb password as RootIsB3st"]),
    ],
}


def main():
    mode = "full"
    if "--short" in sys.argv: mode = "short"
    if "--cyber" in sys.argv: mode = "cyber"

    seq = SEQUENCES[mode]
    total_cmds = sum(len(items) for _, _, items in seq)

    banner()
    print(f"  Mode:  {C['bold']}{mode.upper()}{C['reset']}   "
          f"Commands queued: {C['bold']}{total_cmds}{C['reset']}")
    print()
    print(f"  {C['orange']}↪ START YOUR SCREEN RECORDER NOW.{C['reset']}")
    print(f"  {C['gray']}Demo starts in 5 seconds…{C['reset']}")
    for i in range(5, 0, -1):
        print(f"  {C['gray']}  {i}…{C['reset']}", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30)

    # Sanity check server
    s = status()
    if not s.get("online"):
        print(f"  {C['red']}✗ TOMMY server not reachable at {BASE}{C['reset']}")
        print(f"  {C['red']}  Run START.bat first.{C['reset']}")
        sys.exit(1)

    idx = 0
    try:
        for sec_idx, (title, narration, items) in enumerate(seq, 1):
            section(sec_idx, len(seq), title)
            narrate(narration)
            pause(0.7)
            for cmd in items:
                idx += 1
                run(cmd)
                pause(0.6)
    except KeyboardInterrupt:
        print(f"\n  {C['orange']}Aborted by user.{C['reset']}")
        return

    print()
    print(f"  {C['bold']}{C['green']}✓ DEMO COMPLETE — {idx} commands executed.{C['reset']}")
    print()


if __name__ == "__main__":
    main()
