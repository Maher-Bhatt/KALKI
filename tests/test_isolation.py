"""Tests must never touch the real KALKI profile, however they're run."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.

import ast
import os
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent


class EveryTestFileIsolatesItself(unittest.TestCase):
    def test_isolation_comes_before_any_other_import(self):
        for path in sorted(TESTS.glob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
            names = [alias.name for node in imports for alias in node.names]
            self.assertIn("_isolation", names, path.name)
            first_other = next((n for n in names if n not in ("os", "sys", "_isolation")), None)
            if first_other:
                self.assertLess(names.index("_isolation"), names.index(first_other), path.name)

    def test_the_profile_is_temporary(self):
        temp = os.path.realpath(tempfile.gettempdir())
        for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME"):
            self.assertTrue(os.path.realpath(os.environ[key]).startswith(temp), key)


if __name__ == "__main__":
    unittest.main()
