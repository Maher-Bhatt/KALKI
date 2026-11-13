"""approvals.py and routes_pet.py, the two route groups moved out of server.py."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.


import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import approvals  # noqa: E402
import routes_pet  # noqa: E402


class Approvals(unittest.TestCase):
    def setUp(self):
        saved = dict(approvals.pending)
        approvals.pending.clear()
        self.addCleanup(lambda: (approvals.pending.clear(), approvals.pending.update(saved)))
        self.ran = []

    def hold(self, text="Send an email", ttl=30):
        return approvals.queue(text, lambda: self.ran.append(text) or "done", ttl=ttl)

    def test_waiting_list_shows_the_words_but_never_the_action(self):
        self.hold()
        [item] = approvals.waiting()
        self.assertEqual(item["description"], "Send an email")
        self.assertNotIn("action", item)

    def test_approve_runs_it_once(self):
        approval_id = self.hold()
        self.assertEqual(approvals.decide(approval_id, "approve"), ({"ok": True, "result": "done"}, 200))
        self.assertEqual(self.ran, ["Send an email"])
        payload, status = approvals.decide(approval_id, "approve")
        self.assertEqual(status, 400)
        self.assertEqual(self.ran, ["Send an email"])

    def test_deny_never_runs_it(self):
        approval_id = self.hold()
        self.assertEqual(approvals.decide(approval_id, "deny")[0]["result"], "Denied")
        self.assertEqual(self.ran, [])
        self.assertEqual(approvals.count(), 0)

    def test_expired_ones_neither_count_nor_run(self):
        approval_id = self.hold(ttl=1)
        approvals.pending[approval_id]["expires"] = time.time() - 1
        self.assertEqual(approvals.count(), 0)
        self.assertEqual(approvals.decide(approval_id, "approve")[1], 400)
        self.assertEqual(self.ran, [])

    def test_a_failing_action_reports_the_error(self):
        approval_id = approvals.queue("Break", lambda: 1 / 0)
        payload, status = approvals.decide(approval_id, "approve")
        self.assertEqual(status, 500)
        self.assertFalse(payload["ok"])

    def test_saying_confirm_with_one_waiting_runs_it(self):
        self.hold()
        self.assertEqual(approvals.answer_spoken("Confirm."), "done")

    def test_saying_confirm_with_two_waiting_never_guesses(self):
        self.hold("One")
        self.hold("Two")
        handled, reply = approvals.answer_spoken("confirm")
        self.assertTrue(handled)
        self.assertIn("2 actions are waiting", reply)
        self.assertEqual(self.ran, [])

    def test_cancel_drops_everything(self):
        self.hold("One")
        self.hold("Two")
        self.assertEqual(approvals.answer_spoken("never mind"), (True, "Cancelled."))
        self.assertEqual(approvals.count(), 0)
        self.assertIsNone(approvals.answer_spoken("cancel"))

    def test_other_words_are_left_alone(self):
        self.hold()
        self.assertIsNone(approvals.answer_spoken("confirm my booking for friday"))
        self.assertEqual(approvals.count(), 1)


class PetSettings(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="kalki_pet_")
        self.data_dir = os.path.join(root, "data")
        routes_pet.configure(self.data_dir, root, lambda: {"ok": True})

    def test_defaults_when_nothing_is_saved(self):
        self.assertEqual(routes_pet.get_pet({})[0]["pet"], routes_pet.DEFAULTS)

    def test_saving_keeps_valid_values_and_drops_the_rest(self):
        payload, status = routes_pet.save_pet({"species": "Dragon", "name": "  Ember  ", "sound": True,
                                               "level": 99, "color": "<script>", "enabled": "yes"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["pet"], {"species": "draco", "name": "Ember", "sound": True, "enabled": True})

    def test_unknown_species_and_long_names_are_refused(self):
        self.assertEqual(routes_pet.save_pet({"species": "unicorn"})[1], 400)
        routes_pet.save_pet({"name": "x" * 200})
        self.assertEqual(len(routes_pet.read_settings()["name"]), 24)

    def test_both_copies_are_written(self):
        routes_pet.save_pet({"species": "nova"})
        for path in (os.path.join(self.data_dir, "pet_state.json"),
                     os.path.join(os.path.dirname(self.data_dir), "pet_state.json")):
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["species"], "nova")

    def test_a_failed_save_says_so(self):
        with mock.patch.object(routes_pet.safe_json, "write_json", side_effect=OSError("disk full")):
            payload, status = routes_pet.save_pet({"species": "nova"})
        self.assertEqual(status, 500)
        self.assertIn("disk full", payload["error"])

    def test_a_damaged_file_falls_back_to_defaults(self):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(os.path.join(self.data_dir, "pet_state.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertEqual(routes_pet.read_settings(), routes_pet.DEFAULTS)


class DesktopPetProcess(unittest.TestCase):
    def setUp(self):
        routes_pet.configure(tempfile.mkdtemp(), tempfile.mkdtemp(), lambda: {})

    def test_toggling_while_running_closes_it_and_never_starts_a_second(self):
        with mock.patch.object(routes_pet, "overlay_running", return_value=True), \
                mock.patch.object(routes_pet, "_stop_overlay") as stop, \
                mock.patch.object(routes_pet, "_start_overlay") as start:
            self.assertEqual(routes_pet.toggle({}), ({"ok": True, "running": False}, 200))
        stop.assert_called_once()
        start.assert_not_called()

    def test_turning_on_while_running_does_nothing(self):
        with mock.patch.object(routes_pet, "overlay_running", return_value=True), \
                mock.patch.object(routes_pet, "_start_overlay") as start:
            self.assertEqual(routes_pet.set_overlay(True), ({"ok": True, "running": True}, 200))
        start.assert_not_called()

    def test_a_missing_install_is_reported(self):
        with mock.patch.object(routes_pet, "overlay_running", return_value=False):
            payload, status = routes_pet.set_overlay(True)
        self.assertEqual(status, 500)
        self.assertIn("isn't installed", payload["error"])


if __name__ == "__main__":
    unittest.main()
