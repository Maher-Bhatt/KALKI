"""Settings validation. The rule: a bad settings file can never stop KALKI starting."""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _isolation  # noqa: E402,F401  Before anything from the app: a throwaway profile.

import json
import os
import shutil
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import settings_schema as schema  # noqa: E402


class Validate(unittest.TestCase):
    def test_types_are_coerced_from_form_values(self):
        self.assertIs(schema.validate("ALERTS_ENABLED", "false"), False)
        self.assertIs(schema.validate("ALERTS_ENABLED", True), True)
        self.assertEqual(schema.validate("RAM_HIGH_PCT", "85"), 85)
        self.assertEqual(schema.validate("THEME_MOTION", "0.5"), 0.5)

    def test_out_of_range_and_wrong_types_are_rejected(self):
        for key, value in (("RAM_HIGH_PCT", 500), ("PORT", 80), ("PORT", "abc"), ("MAX_HISTORY", 0),
                           ("ALERTS_ENABLED", "maybe"), ("LISTEN_MODE", "sometimes"),
                           ("TTS_RATE", "fast"), ("OWNER_NAME", ["a"]), ("WAKE_WORDS", "kalki"),
                           ("WAKE_WORDS", []), ("THEME_PRIMARY", "red")):
            with self.assertRaises(schema.SettingError, msg=f"{key}={value}"):
                schema.validate(key, value)

    def test_booleans_are_not_numbers(self):
        with self.assertRaises(schema.SettingError):
            schema.validate("RAM_HIGH_PCT", True)

    def test_urls_must_be_web_addresses(self):
        self.assertEqual(schema.validate("OLLAMA_URL", "http://localhost:11434"), "http://localhost:11434")
        for value in ("file:///etc/passwd", "javascript:alert(1)", "calc.exe"):
            with self.assertRaises(schema.SettingError, msg=value):
                schema.validate("OLLAMA_URL", value)
        with self.assertRaises(schema.SettingError):
            schema.validate("SUPPORT_URL", "http://not-https.example")

    def test_unknown_key_is_rejected(self):
        with self.assertRaises(schema.SettingError):
            schema.validate("_USER_CONFIG_PATH", "x")

    def test_keys_the_ui_saves_are_known(self):
        for key in ("MODEL_CHAT", "MODEL_CODING", "MODEL_VISION", "MODEL_VOICE", "CLOUD_SYNC_ENABLED",
                    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ENABLE_DESKTOP_PET", "TTS_VOICE"):
            self.assertIn(key, schema.SCHEMA)

    def test_every_default_is_valid(self):
        for key, spec in schema.SCHEMA.items():
            if spec.default is not None:
                schema.validate(key, spec.default)

    def test_every_template_value_passes(self):
        """A rule stricter than the shipped template would reset people's settings."""
        import ast
        with open(os.path.join(ROOT, "app", "config.example.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        checked = 0
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if key in schema.SCHEMA:
                    try:
                        value = ast.literal_eval(node.value)
                    except ValueError:
                        continue
                    schema.validate(key, value)
                    checked += 1
        self.assertGreater(checked, 40)

    def test_validate_updates_reports_each_problem(self):
        clean, errors = schema.validate_updates({"RAM_HIGH_PCT": "80", "PORT": "abc", "NOPE": 1})
        self.assertEqual(clean, {"RAM_HIGH_PCT": 80})
        self.assertEqual(sorted(errors), ["NOPE", "PORT"])


class LoadFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_settings_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "user_config.json")

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_missing_file_is_fine(self):
        self.assertEqual(schema.load_user_config(self.path), ({}, []))

    def test_corrupt_file_is_kept_aside_and_not_fatal(self):
        self.write("{broken")
        values, problems = schema.load_user_config(self.path)
        self.assertEqual(values, {})
        self.assertEqual(len(problems), 1)
        self.assertFalse(os.path.exists(self.path))
        kept = [n for n in os.listdir(self.dir) if ".corrupt." in n]
        self.assertEqual(len(kept), 1)
        with open(os.path.join(self.dir, kept[0]), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{broken")

    def test_wrong_shape_is_treated_as_corrupt(self):
        self.write("[1, 2]")
        self.assertEqual(schema.load_user_config(self.path)[0], {})
        self.assertFalse(os.path.exists(self.path))

    def test_one_bad_value_keeps_the_rest(self):
        self.write(json.dumps({"OWNER_NAME": "Maher", "PORT": "abc"}))
        values, problems = schema.load_user_config(self.path)
        self.assertEqual(values, {"OWNER_NAME": "Maher"})
        self.assertEqual(len(problems), 1)
        self.assertTrue(os.path.exists(self.path))

    def test_unknown_keys_are_not_applied_or_reported(self):
        self.write(json.dumps({"OWNER_NAME": "Maher", "WRITTEN_BY_WIZARD": "x"}))
        self.assertEqual(schema.load_user_config(self.path), ({"OWNER_NAME": "Maher"}, []))

    def test_raw_read_keeps_unknown_keys(self):
        self.write(json.dumps({"WRITTEN_BY_WIZARD": "x", "PORT": "abc"}))
        self.assertEqual(schema.read_raw_user_config(self.path)[0], {"WRITTEN_BY_WIZARD": "x", "PORT": "abc"})

    def test_bom_is_accepted(self):
        with open(self.path, "w", encoding="utf-8-sig") as f:
            f.write(json.dumps({"OWNER_NAME": "Maher"}))
        self.assertEqual(schema.load_user_config(self.path)[0], {"OWNER_NAME": "Maher"})


class RepairConfig(unittest.TestCase):
    def test_bad_values_fall_back_and_good_ones_stay(self):
        config = types.SimpleNamespace(PORT="abc", OWNER_NAME="Maher", RAM_HIGH_PCT=999)
        problems = schema.repair_config(config)
        self.assertEqual(config.PORT, schema.SCHEMA["PORT"].default)
        self.assertEqual(config.RAM_HIGH_PCT, schema.SCHEMA["RAM_HIGH_PCT"].default)
        self.assertEqual(config.OWNER_NAME, "Maher")
        self.assertEqual(len(problems), 2)

    def test_problem_text_never_contains_the_value(self):
        config = types.SimpleNamespace(GROQ_API_KEY=["gsk_secret_value"])
        problems = schema.repair_config(config)
        self.assertNotIn("gsk_secret_value", " ".join(problems))

    def test_missing_keys_are_left_alone(self):
        config = types.SimpleNamespace()
        self.assertEqual(schema.repair_config(config), [])
        self.assertFalse(hasattr(config, "PORT"))

    def test_extra_saved_settings_are_applied(self):
        """Regression: model choices saved in the UI were dropped on restart."""
        directory = tempfile.mkdtemp(prefix="kalki_settings_")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "user_config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"MODEL_CHAT": "some-model", "RAM_HIGH_PCT": 70}, f)
        config = types.SimpleNamespace(RAM_HIGH_PCT=90)
        self.assertEqual(schema.apply_user_config(config, path), [])
        self.assertEqual((config.MODEL_CHAT, config.RAM_HIGH_PCT), ("some-model", 70))


if __name__ == "__main__":
    unittest.main()
