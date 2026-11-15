"""Every screen imports the shared helpers it uses.

The Security page called skeletonRows() without importing it, so it crashed with
"skeletonRows is not defined" whenever it opened before its status had loaded."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import re
import unittest
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "app" / "ui"
SHARED = ["components/states.js", "components/dialog.js", "state/toasts.js", "lib/format.js", "lib/dom.js", "lib/icons.js"]


def exports(path):
    text = (UI / path).read_text(encoding="utf-8")
    names = set(re.findall(r"export\s+(?:async\s+)?function\s+(\w+)", text))
    names |= set(re.findall(r"export\s+const\s+(\w+)", text))
    return names


def imported_names(text):
    names = set()
    for group in re.findall(r"import\s*\{([^}]*)\}\s*from", text):
        for part in group.split(","):
            part = part.strip()
            if part:
                names.add(part.split(" as ")[-1].strip())
    return names


class Imports(unittest.TestCase):
    def test_shared_helpers_are_imported_where_used(self):
        shared = {name for path in SHARED for name in exports(path)}
        problems = []
        for js in sorted((UI / "features").glob("*.js")):
            text = js.read_text(encoding="utf-8")
            have = imported_names(text)
            defined = set(re.findall(r"(?:function|const|let|var)\s+(\w+)", text))
            for name in shared:
                if name in have or name in defined:
                    continue
                if re.search(r"(?<![\w.])" + re.escape(name) + r"\s*\(", text):
                    problems.append(f"{js.name} uses {name}() without importing it")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
