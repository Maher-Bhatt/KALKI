"""Every test run uses a throwaway profile, set before any test module is imported.

Without this, the first test file to import the server decided where data went, and a
file that didn't set a temporary profile first sent tests into the real one.
"""

import os
import tempfile

_HOME = tempfile.mkdtemp(prefix="kalki_tests_")
for _key in ("HOME", "APPDATA", "LOCALAPPDATA", "USERPROFILE"):
    os.environ[_key] = _HOME
os.environ["KALKI_TEST"] = "1"
