"""Typing is never interrupted by background updates.

Every status poll used to re-render the whole screen, every 10 seconds (2 while
busy), which replaced the field you were typing in. These checks keep the two
guards in place: polls only re-render on a visible change, and any re-render
keeps the focused field's text, cursor and focus. The behaviour itself was
checked in a browser."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import re
import unittest
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "app" / "ui"


class StatusPolls(unittest.TestCase):
    def test_a_poll_renders_only_when_something_changed(self):
        source = (UI / "state" / "status.js").read_text(encoding="utf-8")
        tick = source[source.index("async function tick"):source.index("let lastSignature")]
        after_store = tick[tick.index("store.status = s;"):]
        self.assertIn("if (sig !== lastSignature)", after_store)
        # The only notify after the status is stored is the guarded one.
        self.assertEqual(len(re.findall(r"\bnotify\(\)", after_store)), 1)

    def test_fast_changing_readings_are_ignored(self):
        source = (UI / "state" / "status.js").read_text(encoding="utf-8")
        for key in ("uptimeSec", "cpu", "remainingSec", "listenerSeenAt"):
            self.assertIn(f"'{key}'", source)


class Mount(unittest.TestCase):
    def test_mount_keeps_the_focused_field(self):
        source = (UI / "lib" / "dom.js").read_text(encoding="utf-8")
        body = source[source.index("export function mount"):source.index("export const qs")]
        self.assertIn("captureTyping(container)", body)
        self.assertIn("restoreTyping(container, typing)", body)
        self.assertIn("setSelectionRange", source)


if __name__ == "__main__":
    unittest.main()
