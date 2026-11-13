"""Password vault and screen reading quick commands."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import server  # noqa: E402
import commands_private as cp  # noqa: E402


def vault_deps(entries=None):
    vault = mock.Mock()
    vault.save_entry.return_value = {"ok": True}
    vault.find_entry.side_effect = lambda label: (entries or {}).get(label)
    vault.list_labels.return_value = [{"label": k} for k in (entries or {})]
    return {"vault": vault, "copy_briefly": mock.Mock(return_value=True),
            "queue": lambda text, fn: (True, f"waiting: {text}"), "random_password": lambda length: "x" * length}


def say(text, deps):
    return cp.vault_command(text.lower().strip(), text.strip(), deps)


class Vault(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(cp.config, "OWNER_TITLE", "", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_passwords_keep_their_capitals(self):
        for text, label, password in (("save my Netflix password as Tr0ub4dor&3", "netflix", "Tr0ub4dor&3"),
                                      ("save password Xy7Pq2Lm for github", "github", "Xy7Pq2Lm")):
            d = vault_deps()
            say(text, d)
            d["vault"].save_entry.assert_called_once_with(label, password=password)

    def test_a_found_password_is_copied_briefly(self):
        d = vault_deps({"netflix": {"label": "netflix", "password": "Secret1"}})
        reply = say("what is my netflix password", d)[1]
        d["copy_briefly"].assert_called_once_with("Secret1")
        self.assertNotIn("Secret1", reply)
        self.assertIn("in a minute", reply)

    def test_a_password_not_in_the_vault_is_left_for_wi_fi(self):
        self.assertIsNone(say("what is my wifi password", vault_deps()))

    def test_deleting_waits_for_approval(self):
        self.assertEqual(say("forget my netflix password", vault_deps()), (True, "waiting: Delete the netflix vault entry"))

    def test_generated_passwords_are_copied_briefly(self):
        d = vault_deps()
        reply = say("generate a strong password of 24", d)[1]
        d["copy_briefly"].assert_called_once_with("x" * 24)
        self.assertIn("24-character", reply)
        self.assertEqual(say("generate a password of 4", d)[1], "Password length must be between 8 and 128.")

    def test_questions_about_passwords_are_not_commands(self):
        self.assertIsNone(say("show me how to reset my wifi password", vault_deps()))


class Screen(unittest.TestCase):
    def test_only_clear_requests_capture_the_screen(self):
        for text in ("can you help me with this essay", "look at this code: print(1)", "help me with this bug in my app",
                     "solve this equation 2x+1=5", "what does this say in french"):
            self.assertFalse(cp.is_screen_request(text), text)
        for text in ("what's on my screen", "look at my screen and tell me the error", "solve this", "help me with this",
                     "read my screen"):
            self.assertTrue(cp.is_screen_request(text), text)

    def test_the_question_is_passed_on(self):
        analyze = mock.Mock(return_value={"mode": "vision", "reply": "It's a login page."})
        reply = cp.screen_command("look at my screen and tell me the error", "Look at my screen and tell me the error",
                                  {"analyze_screen": analyze, "ask": None})
        self.assertEqual(reply, (True, "It's a login page."))
        self.assertEqual(analyze.call_args[0][0], "and tell me the error")


class Routing(unittest.TestCase):
    def test_a_missing_vault_entry_no_longer_answers_for_wi_fi(self):
        with mock.patch.object(server.vault, "find_entry", return_value=None):
            handled, reply = server.handle_local("what is my wifi password")
        self.assertNotIn("no password saved", reply.lower())

    def test_wifi_password_for_a_network_reaches_the_wifi_feature(self):
        with mock.patch.object(server, "ask_native_permission", return_value=False) as ask:
            handled, reply = server.handle_local("wifi password for Home")
        self.assertTrue(handled)
        ask.assert_called_once()

    def test_essay_help_does_not_capture_the_screen(self):
        with mock.patch.object(server.vision, "analyze_screen") as analyze:
            server.handle_local("can you help me with this essay")
        analyze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
