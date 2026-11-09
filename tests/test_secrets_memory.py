"""Encryption, both vaults, and semantic memory. These protect the user's data, so
the main thing tested is failure: a bad read must never destroy anything."""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import db  # noqa: E402
import secure_store  # noqa: E402
import semantic_memory  # noqa: E402
import vault  # noqa: E402
from core import api_vault  # noqa: E402


class TempCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="kalki_secrets_")
        self.addCleanup(shutil.rmtree, self.dir, True)


class SecureStore(TempCase):
    def test_round_trip_never_shows_plain_text(self):
        blob = secure_store.protect("my secret value")
        self.assertNotIn("my secret value", blob)
        self.assertEqual(secure_store.unprotect(blob), "my secret value")

    def test_bad_data_raises_instead_of_returning_empty(self):
        for blob in ("DPAPI:bm90IHJlYWw=", "LOCAL:garbage", "no-prefix-at-all", ""):
            with self.assertRaises(secure_store.UnprotectError, msg=blob):
                secure_store.unprotect(blob)

    def test_old_formats_can_still_be_read(self):
        import base64
        old = "B64:" + base64.b64encode("old value".encode()).decode()
        self.assertEqual(secure_store.unprotect(old), "old value")

    def test_new_data_is_never_base64_only(self):
        with mock.patch.object(secure_store, "HAS_DPAPI", False), \
                mock.patch.object(secure_store, "_key_path", return_value=os.path.join(self.dir, "store.key")), \
                mock.patch.object(secure_store, "_keyring_key", return_value=None):
            blob = secure_store.protect("value")
            self.assertTrue(blob.startswith("LOCAL:"))
            self.assertEqual(secure_store.unprotect(blob), "value")
            self.assertTrue(os.path.exists(os.path.join(self.dir, "store.key")))

    def test_local_key_is_random_not_derived_from_the_machine(self):
        paths = [os.path.join(self.dir, "a.key"), os.path.join(self.dir, "b.key")]
        keys = []
        for path in paths:
            with mock.patch.object(secure_store, "_key_path", return_value=path), \
                    mock.patch.object(secure_store, "_keyring_key", return_value=None):
                keys.append(secure_store._local_key())
        self.assertNotEqual(keys[0], keys[1])


class ApiVault(TempCase):
    def setUp(self):
        super().setUp()
        for name, value in (("VAULT_DIR", self.dir),
                            ("VAULT_FILE", os.path.join(self.dir, "secure_api_vault.enc")),
                            ("INTEGRITY_FILE", os.path.join(self.dir, "vault_integrity.sha256"))):
            patcher = mock.patch.object(api_vault, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _config(self, data):
        path = os.path.join(self.dir, "user_config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_round_trip_and_nothing_plain_on_disk(self):
        api_vault.set_secret("groq_api_key", "gsk_value_123")
        self.assertEqual(api_vault.get_secret("GROQ_API_KEY"), "gsk_value_123")
        self.assertNotIn("gsk_value_123", open(api_vault.VAULT_FILE, encoding="utf-8").read())

    def test_failed_save_is_an_error_not_silence(self):
        with mock.patch.object(api_vault.os, "replace", side_effect=PermissionError("locked")):
            with self.assertRaises(OSError):
                api_vault.set_secret("KEY", "value")

    def test_unreadable_secret_is_kept_on_later_saves(self):
        api_vault.set_secret("GOOD", "1")
        data = json.load(open(api_vault.VAULT_FILE, encoding="utf-8"))
        data["OLD"] = "DPAPI:bm90IHJlYWw="
        with open(api_vault.VAULT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        api_vault.set_secret("NEW", "2")
        self.assertIn("OLD", json.load(open(api_vault.VAULT_FILE, encoding="utf-8")))
        self.assertEqual(api_vault.unreadable_keys(), ["OLD"])
        self.assertEqual(api_vault.list_secrets(), {"GOOD": "1", "NEW": "2"})

    def test_migration_removes_plain_text_secrets_from_config(self):
        path = self._config({"GROQ_API_KEY": "gsk_real_value", "OWNER_NAME": "Maher"})
        api_vault.migrate_settings_to_vault(path)
        self.assertEqual(api_vault.get_secret("GROQ_API_KEY"), "gsk_real_value")
        self.assertEqual(json.load(open(path, encoding="utf-8")), {"OWNER_NAME": "Maher"})

    def test_migration_ignores_placeholders(self):
        path = self._config({"GROQ_API_KEY": "PASTE_YOUR_GROQ_KEY_HERE"})
        api_vault.migrate_settings_to_vault(path)
        self.assertEqual(api_vault.get_secret("GROQ_API_KEY"), "")

    def test_migration_keeps_config_if_the_vault_write_fails(self):
        path = self._config({"GROQ_API_KEY": "gsk_real_value"})
        with mock.patch.object(api_vault, "set_secret", side_effect=OSError("disk full")):
            api_vault.migrate_settings_to_vault(path)
        self.assertEqual(json.load(open(path, encoding="utf-8"))["GROQ_API_KEY"], "gsk_real_value")

    def test_export_import_with_password(self):
        api_vault.set_secret("KEY", "value")
        path = os.path.join(self.dir, "export.json")
        self.assertTrue(api_vault.export_vault(path, "pass phrase"))
        self.assertNotIn("value", open(path, encoding="utf-8").read().replace("ciphertext", ""))
        self.assertEqual(json.load(open(path, encoding="utf-8"))["kdf"], "pbkdf2-sha256")
        api_vault.set_secret("KEY", "changed")
        self.assertFalse(api_vault.import_vault(path, "wrong"))
        self.assertTrue(api_vault.import_vault(path, "pass phrase"))
        self.assertEqual(api_vault.get_secret("KEY"), "value")


class CredentialVault(TempCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(vault, "VAULT_PATH", os.path.join(self.dir, "vault.json"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_round_trip_and_encrypted_on_disk(self):
        self.assertIs(vault.save_entry("GitHub", username="me", password="hunter2value"), True)
        self.assertEqual(vault.get_entry("github")["password"], "hunter2value")
        self.assertNotIn("hunter2value", open(vault.VAULT_PATH, encoding="utf-8").read())

    def test_partial_delete_needs_exactly_one_match(self):
        vault.save_entry("work mail", password="a")
        vault.save_entry("home mail", password="b")
        self.assertFalse(vault.delete_entry("mail"))
        self.assertEqual(len(vault.list_labels()), 2)
        self.assertTrue(vault.delete_entry("work"))
        self.assertEqual([e["label"] for e in vault.list_labels()], ["home mail"])

    def test_find_never_guesses_between_entries(self):
        vault.save_entry("work mail", password="a")
        vault.save_entry("home mail", password="b")
        self.assertIsNone(vault.find_entry("mail"))
        self.assertEqual(vault.find_entry("home")["label"], "home mail")

    def test_unreadable_entry_says_so(self):
        vault.save_entry("x", password="a")
        data = json.load(open(vault.VAULT_PATH, encoding="utf-8"))
        data["x"]["password"] = "DPAPI:bm90IHJlYWw="
        with open(vault.VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        entry = vault.get_entry("x")
        self.assertEqual(entry["password"], "")
        self.assertTrue(entry["unreadable"])


class SemanticMemory(TempCase):
    def setUp(self):
        super().setUp()
        self._previous = db.current_path()
        db.configure(os.path.join(self.dir, "kalki.db"))
        db.open_store(self.dir)
        self.legacy = os.path.join(self.dir, "semantic_memory.json")
        patcher = mock.patch.object(semantic_memory, "get_embedding", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(db.configure, self._previous)
        self.mem = semantic_memory.SemanticMemory(path=self.legacy)

    def fresh(self):
        return semantic_memory.SemanticMemory(path=self.legacy)

    def raw_rows(self):
        conn = sqlite3.connect(db.current_path())
        try:
            return conn.execute("SELECT id, payload FROM memories").fetchall()
        finally:
            conn.close()

    def test_add_update_delete_survive_restart(self):
        doc_id = self.mem.add_memory("likes tea", tags=["Personal"], importance=7)
        self.assertEqual(self.fresh().list_all()[0]["text"], "likes tea")
        self.assertTrue(self.mem.update_memory(doc_id, "likes coffee", importance=9))
        saved = self.fresh().list_all()[0]
        self.assertEqual((saved["text"], saved["importance"]), ("likes coffee", 9))
        self.assertTrue(self.mem.delete_memory(doc_id))
        self.assertEqual(self.fresh().list_all(), [])

    def test_text_is_encrypted_in_the_database(self):
        self.mem.add_memory("my private fact")
        self.assertNotIn("my private fact", self.raw_rows()[0][1])

    def test_unreadable_memory_is_never_deleted(self):
        """Regression: a failed decrypt used to overwrite everything with an empty list."""
        self.mem.add_memory("readable")
        conn = sqlite3.connect(db.current_path())
        conn.execute("INSERT INTO memories (payload) VALUES ('DPAPI:bm90IHJlYWw=')")
        conn.commit()
        conn.close()
        mem = self.fresh()
        self.assertEqual([d["text"] for d in mem.list_all()], ["readable"])
        self.assertEqual(mem.unreadable_count(), 1)
        mem.add_memory("another")
        mem.search("readable")
        mem.delete_memory(mem.list_all()[0]["id"])
        self.assertIn("DPAPI:bm90IHJlYWw=", [row[1] for row in self.raw_rows()])

    def test_keyword_search_and_pinned_results(self):
        self.mem.add_memory("the dog is called Rex", importance=5)
        self.mem.add_memory("always answer briefly", memory_type="pinned")
        self.mem.add_memory("favourite colour is blue")
        texts = [d["text"] for d in self.mem.search("dog called")]
        self.assertIn("the dog is called Rex", texts)
        self.assertIn("always answer briefly", texts)
        self.assertNotIn("favourite colour is blue", texts)

    def test_search_results_exclude_vectors_from_list(self):
        with mock.patch.object(semantic_memory, "get_embedding", return_value=[0.1, 0.2]):
            self.mem.add_memory("with a vector")
        self.assertNotIn("vector", self.mem.list_all()[0])
        self.assertEqual(self.fresh().documents[0]["vector"], [0.1, 0.2])

    def test_old_plain_file_imports_once_and_is_untouched(self):
        docs = [{"id": 12, "text": "old fact", "tags": [], "importance": 5, "type": "fact"}]
        with open(self.legacy, "w", encoding="utf-8") as f:
            json.dump(docs, f)
        before = open(self.legacy, "rb").read()
        self.assertEqual(self.mem.import_legacy(), {"imported": 1})
        self.assertEqual(self.mem.list_all()[0]["id"], 12)
        self.assertEqual(open(self.legacy, "rb").read(), before)
        self.mem.delete_memory(12)
        self.assertIsNone(self.mem.import_legacy())
        self.assertEqual(self.mem.list_all(), [])

    def test_old_encrypted_file_imports(self):
        docs = [{"id": 3, "text": "encrypted fact"}]
        with open(self.legacy, "w", encoding="utf-8") as f:
            f.write(secure_store.protect(json.dumps(docs)))
        self.assertEqual(self.mem.import_legacy(), {"imported": 1})
        self.assertEqual(self.mem.list_all()[0]["text"], "encrypted fact")

    def test_undecryptable_old_file_is_kept_and_retried(self):
        with open(self.legacy, "w", encoding="utf-8") as f:
            f.write("DPAPI:bm90IHJlYWw=")
        before = open(self.legacy, "rb").read()
        self.assertIn("failed", self.mem.import_legacy())
        self.assertEqual(open(self.legacy, "rb").read(), before)
        self.mem.add_memory("still works")
        with open(self.legacy, "w", encoding="utf-8") as f:
            json.dump([{"id": 50, "text": "recovered"}], f)
        self.assertEqual(self.mem.import_legacy(), {"imported": 1})
        self.assertEqual(sorted(d["text"] for d in self.mem.list_all()), ["recovered", "still works"])


if __name__ == "__main__":
    unittest.main()
