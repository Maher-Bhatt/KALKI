"""Clipboard, note capture, site watching and PC control quick commands."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import commands_desktop as cd  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(cd.config, "OWNER_TITLE", "", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)


class Capture(Base):
    def deps(self, clip=""):
        clipboard = mock.Mock()
        clipboard.read_text.return_value = clip
        return {"notes": mock.Mock(), "memory": mock.Mock(), "clipboard": clipboard, "log": print}

    def test_remember_saves_with_your_capitals(self):
        d = self.deps()
        reply = cd.capture_command("remember that the wi-fi code is on the fridge",
                                   "Remember that the Wi-Fi code is on the Fridge", {}, d)
        d["notes"].add_note.assert_called_once_with("the Wi-Fi code is on the Fridge")
        self.assertIn("Saved to your notes", reply[1])

    def test_save_on_its_own_is_not_a_note(self):
        for text in ("save my work", "save the file", "save it for later"):
            d = self.deps()
            self.assertIsNone(cd.capture_command(text, text, {}, d), text)
            d["notes"].add_note.assert_not_called()

    def test_save_with_a_colon_is_a_note(self):
        d = self.deps()
        cd.capture_command("save note: call the plumber", "save note: call the plumber", {}, d)
        d["notes"].add_note.assert_called_once_with("call the plumber")

    def test_clipboard_capture_shows_what_was_saved(self):
        d = self.deps(clip="meeting moved to 4pm on thursday")
        reply = cd.capture_command("remember this", "remember this", {}, d)[1]
        self.assertIn("meeting moved to 4pm", reply)

    def test_empty_clipboard_asks_then_saves_the_answer(self):
        state = {}
        d = self.deps()
        self.assertIn("What would you like", cd.capture_command("save this", "save this", state, d)[1])
        self.assertTrue(state["pending_note_capture"])
        cd.capture_command("buy milk", "Buy milk", state, d)
        d["notes"].add_note.assert_called_with("Buy milk")
        self.assertFalse(state["pending_note_capture"])


class Sites(Base):
    def deps(self):
        return {"clipboard": mock.Mock(), "watchdog": mock.Mock(), "browser_url": mock.Mock(), "speak": lambda s: None}

    def test_a_sentence_ending_in_a_full_stop_is_not_a_site(self):
        d = self.deps()
        self.assertIsNone(cd.clipboard_and_sites_command("watch the news.", "watch the news.", d))
        d["watchdog"].add_site.assert_not_called()

    def test_a_real_site_is_watched(self):
        d = self.deps()
        cd.clipboard_and_sites_command("watch example.com", "watch example.com", d)
        d["watchdog"].add_site.assert_called_once_with("example.com")


class PcControl(Base):
    def deps(self):
        clipboard = mock.Mock()
        clipboard.read_text.return_value = "def f(:\n pass"
        return {"lock": mock.Mock(), "queue": lambda text, fn: (True, f"waiting: {text}"), "clipboard": clipboard,
                "fix_code": mock.Mock(return_value="```python\ndef f():\n    pass\n```")}

    def test_risky_ones_wait_for_approval(self):
        d = self.deps()
        self.assertEqual(cd.pc_control_command("shut down", d), (True, "waiting: Shut down your PC"))
        self.assertEqual(cd.pc_control_command("empty recycle bin", d), (True, "waiting: Empty the recycle bin"))

    def test_a_failed_recycle_bin_is_reported(self):
        captured = {}
        d = self.deps()
        d["queue"] = lambda text, fn: captured.setdefault("fn", fn) and (True, "waiting")
        cd.pc_control_command("empty the recycle bin", d)
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="Access denied")
        with mock.patch.object(cd.subprocess, "run", return_value=failed):
            self.assertIn("wasn't emptied", captured["fn"]()[1])

    def test_vs_code_without_a_shell(self):
        with mock.patch.object(cd.shutil, "which", return_value=None):
            self.assertIn("couldn't find VS Code", cd.pc_control_command("open vs code", self.deps())[1])
        with mock.patch.object(cd.shutil, "which", return_value="C:/code.cmd"), \
                mock.patch.object(cd.subprocess, "Popen") as popen:
            cd.pc_control_command("open vs code", self.deps())
        popen.assert_called_once_with(["C:/code.cmd"])

    def test_fixed_code_goes_back_to_the_clipboard_without_fences(self):
        d = self.deps()
        cd.pc_control_command("fix my code", d)
        d["clipboard"].set_text.assert_called_once_with("def f():\n    pass")


class Routing(unittest.TestCase):
    def test_fix_my_code_uses_the_ai(self):
        with mock.patch.object(server.clipboard_mod, "read_text", return_value="print(1"),                 mock.patch.object(server.clipboard_mod, "set_text") as put,                 mock.patch.object(server, "ask_ai", return_value="print(1)"):
            self.assertEqual(server.handle_local("fix my code")[0], True)
        put.assert_called_once_with("print(1)")

    def test_handle_local_routes_them(self):
        with mock.patch.object(server.notesmod, "add_note") as add, \
                mock.patch.object(server.semantic_memory.memory, "add_memory"):
            handled, _ = server.handle_local("remember that the spare tyre is in the boot")
        self.assertTrue(handled)
        add.assert_called_once()
        self.assertFalse(server.handle_local("save my work")[0] and "notes" in server.handle_local("save my work")[1])


if __name__ == "__main__":
    unittest.main()
