"""Send every test to a throwaway profile, however the tests are run.

Each test file imports this first, before anything from the app. pytest also loads it
through conftest.py. Running a file directly or through `python -m unittest` doesn't use
conftest.py, so the import in each file is what keeps tests out of the real profile.
"""

import os
import tempfile

if not os.environ.get("KALKI_TEST_HOME"):
    _home = tempfile.mkdtemp(prefix="kalki_tests_")
    os.environ["KALKI_TEST_HOME"] = _home
    for _key in ("HOME", "APPDATA", "LOCALAPPDATA", "USERPROFILE"):
        os.environ[_key] = _home
    os.environ["KALKI_TEST"] = "1"
