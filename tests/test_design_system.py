"""The design system and the pets: what a browser can't catch by accident."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "app" / "ui"
sys.path.insert(0, str(ROOT / "app"))

import pet_window  # noqa: E402
import server  # noqa: E402

PETS = (UI / "pet_sprites.js").read_text(encoding="utf-8")


def ui_files(*suffixes):
    for path in UI.rglob("*"):
        if path.suffix in suffixes and "assets" not in path.parts:
            yield path


class Tokens(unittest.TestCase):
    def test_every_css_variable_used_is_defined(self):
        text = {path: path.read_text(encoding="utf-8") for path in ui_files(".css", ".js", ".html")}
        everything = "\n".join(text.values()) + (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        defined = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", everything))
        used = set(re.findall(r"var\((--[a-zA-Z0-9-]+)", everything))
        self.assertEqual(sorted(used - defined), [])

    def test_the_scales_exist(self):
        tokens = (UI / "tokens.css").read_text(encoding="utf-8")
        for name in ("--type-base", "--space-4", "--radius-md", "--shadow-2", "--dur", "--ease", "--ui", "--mono"):
            self.assertIn(f"{name}:", tokens, name)

    def test_a_font_that_is_not_installed_is_not_named(self):
        for path in [*ui_files(".css"), ROOT / "app" / "index.html"]:
            self.assertNotIn("Instrument Sans", path.read_text(encoding="utf-8"), path.name)


class PlainLanguage(unittest.TestCase):
    BANNED = ("Sovereign", "neural intelligence", "ShieldCore", "DESKTOP OS CORE", "Executive", ", Sir",
              "Attitude Enforcement", " 1.1 s", "Eliminate", "Quarantine Vault")

    def test_text_is_not_garbled(self):
        for path in ui_files(".js", ".html", ".css"):
            content = path.read_text(encoding="utf-8")
            self.assertNotRegex(content, "[\u00c2\u00c3\u00e2][\u0080-\u203a]", path.name)

    def test_every_switch_is_a_real_control(self):
        for path in ui_files(".js"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("h('i.tg", content, path.name)
            self.assertNotIn("h(`i.tg", content, path.name)

    def test_marketing_words_are_gone_from_the_interface(self):
        for path in ui_files(".js", ".html"):
            content = path.read_text(encoding="utf-8")
            for word in self.BANNED:
                self.assertNotIn(word, content, f"{word} in {path.name}")


class Navigation(unittest.TestCase):
    def test_the_sidebar_uses_the_chosen_names(self):
        shell = (UI / "features" / "shell.js").read_text(encoding="utf-8")
        for label in ("Ask", "Today", "Memory", "Workbench", "Security"):
            self.assertIn(f"label: '{label}'", shell)
        for old in ("Antivirus", "Oversight", "Library", "Studio"):
            self.assertNotIn(f"label: '{old}", shell)
        # Activity moved to the bell in the top bar, which also counts approvals.
        self.assertIn("go('oversight')", shell)
        self.assertIn("bellCount", shell)

    def test_the_look_is_loaded(self):
        index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/ui/theme.css"', index)
        tokens = (UI / "tokens.css").read_text(encoding="utf-8")
        self.assertIn("--serif:", tokens)
        self.assertIn('html[data-theme="light"]', tokens)

    def test_voice_mode_says_when_voice_is_off(self):
        voice = (UI / "features" / "voice.js").read_text(encoding="utf-8")
        self.assertIn("voice listener isn", voice)
        self.assertIn("parts.mainBtn.disabled = !online", voice)

    def test_the_top_bar_has_no_chips(self):
        shell = (UI / "features" / "shell.js").read_text(encoding="utf-8")
        for gone in ("micChip", "modeBadge", "badge-core", "win-btn"):
            self.assertNotIn(gone, shell)

    def test_first_run_starts_with_the_app(self):
        main = (UI / "main.js").read_text(encoding="utf-8")
        self.assertIn("maybeShowFirstRun();", main)

    def test_today_has_no_made_up_suggestion(self):
        today = (UI / "features" / "today.js").read_text(encoding="utf-8")
        self.assertNotIn("KALKI noticed a long block of text", today)
        self.assertNotIn("Prepared 08:00", today)


class Sprites(unittest.TestCase):
    def species(self):
        return re.findall(r"(\w+): \{\n\s+name: .*?colors: \{(.*?)\},\n\s+rows: \[(.*?)\],", PETS, re.S)

    def test_all_six_characters_are_there(self):
        self.assertEqual({name for name, _, _ in self.species()}, {"gobi", "kittu", "byte", "draco", "kitsu", "nova"})

    def test_every_sprite_is_well_formed(self):
        for name, colors, block in self.species():
            rows = re.findall(r"'([^']+)'", block)
            self.assertLessEqual(len(rows), 22, f"{name} is too tall to leave room for its status")
            for row in rows:
                self.assertEqual(len(row), 12, f"{name}: {row}")
            used = set("".join(rows)) - {".", "E", "e", "T", "t"}
            palette = set(re.findall(r"\b(\w+):", colors))
            self.assertLessEqual(used, palette, name)
            self.assertIn("E", "".join(rows) + "E", name)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class PetStates(unittest.TestCase):
    def resolve(self, inputs):
        script = (
            f"require({json.dumps(str(UI / 'pet_sprites.js'))});"
            f"console.log(globalThis.KalkiPets.resolveState({json.dumps(inputs)}))"
        )
        return subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout.strip()

    def test_a_request_for_approval_always_shows(self):
        self.assertEqual(self.resolve({"pending": 1, "working": True, "music": True, "idleMs": 10 ** 9}), "waiting")

    def test_order_of_the_others(self):
        self.assertEqual(self.resolve({"working": True, "music": True}), "working")
        self.assertEqual(self.resolve({"listening": True, "doneRecently": True}), "listening")
        self.assertEqual(self.resolve({"doneRecently": True, "music": True}), "done")
        self.assertEqual(self.resolve({"music": True, "idleMs": 10 ** 9}), "music")
        self.assertEqual(self.resolve({"idleMs": 10 ** 9}), "asleep")
        self.assertEqual(self.resolve({}), "idle")


class ToolCards(unittest.TestCase):
    def setUp(self):
        server._take_tool_cards()
        self.addCleanup(server._take_tool_cards)

    def test_a_tool_that_ran_says_it_did(self):
        with unittest.mock.patch.object(server, "_run_tool_call", return_value="ok"):
            server.execute_tool_call("manage_tasks", json.dumps({"action": "list"}))
        card = server._take_tool_cards()[0]
        self.assertEqual((card["label"], card["status"]), ("Checked your tasks", "done"))

    def test_waiting_for_approval_never_says_done(self):
        server.execute_tool_call("send_email", json.dumps({"to_address": "a@example.com", "subject": "s", "body": "private"}))
        card = server._take_tool_cards()[0]
        self.assertEqual((card["label"], card["status"]), ("Send an email", "waiting"))
        with server._pending_lock:
            for key in [k for k, v in server._pending_approvals.items() if "a@example.com" in v["description"]]:
                del server._pending_approvals[key]

    def test_a_failure_is_shown_as_one(self):
        with unittest.mock.patch.object(server, "_run_tool_call", return_value="Error: no connection"):
            server.execute_tool_call("search_web", json.dumps({"query": "weather"}))
        card = server._take_tool_cards()[0]
        self.assertEqual((card["label"], card["status"], card["detail"]), ("Search the web", "failed", "weather"))

    def test_private_arguments_stay_off_the_card(self):
        card = server.tool_policy.tool_card("send_email", {"to_address": "a@example.com", "body": "secret text"}, "done")
        self.assertNotIn("secret text", json.dumps(card))

    def test_cards_are_taken_once(self):
        with unittest.mock.patch.object(server, "_run_tool_call", return_value="ok"):
            server.execute_tool_call("manage_tasks", json.dumps({"action": "list"}))
        self.assertEqual(len(server._take_tool_cards()), 1)
        self.assertEqual(server._take_tool_cards(), [])


class PetStatus(unittest.TestCase):
    def setUp(self):
        with server._pending_lock:
            self.saved = dict(server._pending_approvals)
            server._pending_approvals.clear()
        self.addCleanup(self.restore)

    def restore(self):
        with server._pending_lock:
            server._pending_approvals.clear()
            server._pending_approvals.update(self.saved)

    def test_shows_approvals_that_are_still_open(self):
        with server._pending_lock:
            server._pending_approvals["open"] = {"expires": time.time() + 60}
            server._pending_approvals["old"] = {"expires": time.time() - 60}
        self.assertEqual(server._pet_status()["pending"], 1)

    def test_working_only_while_a_reply_is_being_written(self):
        self.assertFalse(server._pet_status()["working"])
        reply = server._counting_reply(iter(["a", "b"]))
        self.assertFalse(server._pet_status()["working"])
        self.assertEqual(next(reply), "a")
        self.assertTrue(server._pet_status()["working"])
        list(reply)
        self.assertFalse(server._pet_status()["working"])

    def test_a_cancelled_reply_does_not_leave_it_working(self):
        reply = server._counting_reply(iter(["a", "b"]))
        next(reply)
        reply.close()
        self.assertFalse(server._pet_status()["working"])

    def test_a_failed_reply_does_not_leave_it_working(self):
        def broken():
            yield "a"
            raise RuntimeError("the AI service failed")

        with self.assertRaises(RuntimeError):
            list(server._counting_reply(broken()))
        self.assertFalse(server._pet_status()["working"])

    def test_music_status_is_read_whatever_its_capitals(self):
        original = server.STATE.get("cached_now_playing")
        self.addCleanup(server.STATE.__setitem__, "cached_now_playing", original)
        for text in ("Playing", "playing"):
            server.STATE["cached_now_playing"] = {"status": text}
            self.assertTrue(server._pet_status()["music"], text)
        server.STATE["cached_now_playing"] = "not a dict"
        self.assertFalse(server._pet_status()["music"])

    def test_the_route_needs_a_login(self):
        self.assertFalse(server.Handler._is_public_path(server.Handler, "/api/pet/status"))


class Website(unittest.TestCase):
    def test_the_website_shows_the_same_characters_as_the_app(self):
        app_copy = (UI / "pet_sprites.js").read_bytes()
        site_copy = (ROOT / "marketing" / "assets" / "pet_sprites.js").read_bytes()
        crlf, lf = bytes([13, 10]), bytes([10])
        self.assertEqual(site_copy.replace(crlf, lf), app_copy.replace(crlf, lf))


class PetOverlay(unittest.TestCase):
    def setUp(self):
        self.page = (UI / "pet_overlay.html").read_text(encoding="utf-8")

    def test_shares_the_characters(self):
        self.assertIn('src="pet_sprites.js"', self.page)
        self.assertNotIn("assets/pets", self.page)

    def test_does_not_ask_the_system_about_music_every_second(self):
        self.assertNotIn("get_music_state", self.page)
        self.assertNotIn("/api/media/now", self.page)
        self.assertRegex(self.page, r"POLL_MS = 1500")

    def test_frames_go_to_the_see_through_window(self):
        self.assertIn("native().show_frame(frame)", self.page)
        self.assertIn("player.onFrame(sendFrame)", self.page)
        source = (ROOT / "app" / "desktop_pet.py").read_text(encoding="utf-8")
        self.assertIn("pet_window.PetWindow(", source)
        self.assertNotIn("transparent=True", source)


class PetWindowDrawing(unittest.TestCase):
    def test_empty_pixels_are_fully_see_through(self):
        out = pet_window.frame_to_bgra(bytes([10, 20, 30, 0]), 1, 2)
        self.assertEqual(out, bytes(16))

    def test_colours_are_in_the_order_windows_wants(self):
        self.assertEqual(pet_window.frame_to_bgra(bytes([10, 20, 30, 255]), 1, 1), bytes([30, 20, 10, 255]))

    def test_pixels_stay_sharp_when_enlarged(self):
        frame = bytes([255, 0, 0, 255, 0, 0, 0, 0] + [0, 0, 0, 0, 0, 255, 0, 255])
        out = pet_window.frame_to_bgra(frame, 2, 2)
        red, empty, green = bytes([0, 0, 255, 255]), bytes(4), bytes([0, 255, 0, 255])
        expected = (red * 2 + empty * 2) * 2 + (empty * 2 + green * 2) * 2
        self.assertEqual(out, expected)

    def test_a_wrong_sized_frame_is_refused(self):
        with self.assertRaises(ValueError):
            pet_window.frame_to_bgra(b"1234", 2, 1)

    def test_scale_is_a_whole_number(self):
        self.assertEqual(pet_window.scale_for_dpi(96), 3)
        self.assertEqual(pet_window.scale_for_dpi(144), 4)
        self.assertEqual(pet_window.scale_for_dpi(192), 6)

    def test_card_sits_above_the_pet(self):
        self.assertEqual(pet_window.card_position((900, 700, 1000, 800), (280, 200), (0, 0, 1920, 1040)), (720, 494))

    def test_card_goes_below_when_the_pet_is_at_the_top(self):
        self.assertEqual(pet_window.card_position((900, 10, 1000, 110), (280, 200), (0, 0, 1920, 1040)), (720, 116))

    def test_card_stays_on_screen_at_the_left_edge(self):
        self.assertEqual(pet_window.card_position((0, 700, 100, 800), (280, 200), (0, 0, 1920, 1040))[0], 0)


if __name__ == "__main__":
    unittest.main()
