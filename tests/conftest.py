"""pytest loads this first. The setup itself lives in _isolation.py, which every test
file also imports, so tests stay out of the real profile however they're run."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401
