# KALKI verification sandbox

Run the sandbox from the `app` folder with KALKI's normal Python runtime:

```powershell
python verification_sandbox.py --report ..\data\verification_report.json
```

It is safe to run before each release. The runner creates a temporary `APPDATA`
and KALKI data folder, starts the real local HTTP handler on an ephemeral port,
and deletes the temporary files at the end.

It verifies:

- Python source syntax for the application source tree.
- AI tool-schema contracts and deterministic local utility functions.
- KALKI's static UI routes, health/status/settings/model/dashboard API reads,
  isolated settings persistence, and safe list routes.
- Local-origin protection against cross-site localhost requests.
- An inventory of every declared API route, including routes that cannot be
  safely executed unattended.

The sandbox intentionally does not trigger AI providers, OAuth connections,
microphone/TTS, browser automation, cyber scans, OS controls, resets, backups,
or file-changing operations. Those require valid credentials, actual hardware,
or explicit user confirmation and are listed in the JSON report for manual
acceptance testing.

The command exits with a non-zero status when any automated check fails, so it
can be used as a release/build gate.
