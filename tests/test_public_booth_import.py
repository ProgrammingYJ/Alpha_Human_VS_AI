"""Public import boundary tests; no network, credentials or real photographs."""

from copy import deepcopy
import importlib.util
from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from PIL import Image


def load_importer():
    path = Path(__file__).resolve().parents[1] / "scripts/import_public_booth_bank.py"
    spec = importlib.util.spec_from_file_location("public_bank_import_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicImportTests(unittest.TestCase):
    def setUp(self):
        self.cli = load_importer()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        image = BytesIO()
        Image.new("RGB", (12, 12), "blue").save(image, format="PNG")
        self.data = image.getvalue()
        (self.root / "photo.png").write_bytes(self.data)
        self.bank_path = self.root / "bank.json"
        self.bank = {"publicDeploymentCleared": True, "schoolPhotosUsed": False, "images": [{
            "id": "synthetic-id", "file": "photo.png", "groupId": "independent-synthetic-group",
            "source": "other", "usageNote": "Synthetic test only; not a real image license claim",
            "labels": {"personCount": 0, "treeCount": None, "treeAtLeast3": None,
                       "building": False, "pond": False},
            "provenance": {"sha256": hashlib.sha256(self.data).hexdigest(),
                           "license": "CC0", "sourceUrl": "https://example.invalid/synthetic"},
        }]}

    def write_bank(self, bank=None):
        self.bank_path.write_text(json.dumps(bank or self.bank), encoding="utf-8")
        return self.bank_path

    def test_public_clearance_does_not_admit_private_kaggle_school_or_uncleared_licenses(self):
        changed = []
        for name, value in (("publicDeploymentCleared", False), ("schoolPhotosUsed", True), ("demoOnly", True)):
            bank = deepcopy(self.bank); bank[name] = value; changed.append(bank)
        for source in ("school", "kaggle"):
            bank = deepcopy(self.bank); bank["images"][0]["source"] = source; changed.append(bank)
        bank = deepcopy(self.bank); bank["images"][0]["provenance"]["license"] = "CC BY-SA"; changed.append(bank)
        for bank in changed:
            with self.subTest(bank=bank), self.assertRaises(ValueError):
                self.cli.prepare_bank(self.write_bank(bank))

    def test_real_decode_hash_group_and_file_boundary_are_checked_before_upload(self):
        self.assertEqual(len(self.cli.prepare_bank(self.write_bank())), 1)
        for filename in ("../outside.png", str(self.root.parent / "outside.png")):
            bank = deepcopy(self.bank); bank["images"][0]["file"] = filename
            with self.subTest(path=filename), self.assertRaises(ValueError):
                self.cli.prepare_bank(self.write_bank(bank))
        bank = deepcopy(self.bank); bank["images"][0]["provenance"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.cli.prepare_bank(self.write_bank(bank))
        bank = deepcopy(self.bank); bank["images"].append(deepcopy(bank["images"][0]))
        with self.assertRaises(ValueError):
            self.cli.prepare_bank(self.write_bank(bank))
        bank = deepcopy(self.bank)
        (self.root / "photo.png").write_bytes(b"not a decoded photograph")
        bank["images"][0]["provenance"]["sha256"] = hashlib.sha256((self.root / "photo.png").read_bytes()).hexdigest()
        with self.assertRaises(Exception):
            self.cli.prepare_bank(self.write_bank(bank))

    def test_related_photos_may_share_a_bank_group_without_becoming_independent_tiles(self):
        other = BytesIO()
        Image.new("RGB", (12, 12), "green").save(other, format="PNG")
        (self.root / "related.png").write_bytes(other.getvalue())
        bank = deepcopy(self.bank)
        related = deepcopy(bank["images"][0])
        related.update(id="related-synthetic-id", file="related.png")
        related["provenance"]["sha256"] = hashlib.sha256(other.getvalue()).hexdigest()
        bank["images"].append(related)
        photos = self.cli.prepare_bank(self.write_bank(bank))
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0]["metadata"]["groupId"], photos[1]["metadata"]["groupId"])
        self.assertNotEqual(photos[0]["data"], photos[1]["data"])
        # The server's existing group-aware challenge builder, rather than
        # import-time rejection, keeps these out of the same 3x3 question.

    def test_origin_and_label_guards_reject_credential_redirection_and_invented_counts(self):
        for value in ("https://third-party.example", "https://human.marulee.dev.evil.invalid",
                      "http://human.marulee.dev", "https://human.marulee.dev:444",
                      "https://user:password@human.marulee.dev", "https://bot.marulee.dev/path",
                      "https://human.marulee.dev?key=anything"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.cli.controlled_origin(value)
        self.assertEqual(self.cli.controlled_origin("https://human.marulee.dev/"), "https://human.marulee.dev")
        self.assertEqual(self.cli.controlled_origin("http://localhost:5186"), "http://localhost:5186")
        for labels in ({"personCount": True}, {"treeCount": -1}, {"treeCount": 2, "treeAtLeast3": True},
                       {"treeAtLeast3": False, "treeCountMinimum": 3}):
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                self.cli.validated_labels(labels)
        self.assertEqual(self.cli.validated_labels({"treeCountMinimum": 2})["treeAtLeast3"], None)
        self.assertIsNone(self.cli.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_only_exact_duplicate_photo_response_is_idempotently_skipped(self):
        photo = self.cli.prepare_bank(self.write_bank())[0]
        class Reject:
            def __init__(self, code):
                self.code = code
                self.request = None
            def open(self, request, *, timeout):
                self.request = request
                raise HTTPError(request.full_url, 409, "synthetic", {}, BytesIO(json.dumps({"code": self.code}).encode()))
        duplicate = Reject("duplicate_photo")
        self.assertEqual(self.cli.upload_one("https://human.marulee.dev", "synthetic-not-a-secret", photo, duplicate), "already_present")
        headers = {key.lower(): value for key, value in duplicate.request.header_items()}
        self.assertEqual(headers["x-admin-key"], "synthetic-not-a-secret")
        self.assertEqual(headers["user-agent"], "AlphaCaptchaPublicBankImporter/1.0")
        self.assertNotIn(b"synthetic-not-a-secret", duplicate.request.data)
        for code in ("conflict", "invalid_metadata"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.cli.upload_one("https://human.marulee.dev", "synthetic-not-a-secret", photo, Reject(code))

    def test_dry_run_never_reads_a_key_or_calls_the_upload_network(self):
        self.write_bank()
        output = self.root / "dry-run.json"
        args = ["import_public_booth_bank.py", "--bank", str(self.bank_path),
                "--base-url", "https://human.marulee.dev", "--output", str(output)]
        with patch("sys.argv", args), patch("sys.stdin") as stdin, \
                patch.object(self.cli, "upload_one") as upload:
            self.assertEqual(self.cli.main(), 0)
        stdin.readline.assert_not_called(); upload.assert_not_called()
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["verifiedImages"], 1)
        self.assertEqual(report["uploadedImages"], 0)
        self.assertTrue(report["completed"])
        self.assertFalse(report["administratorKeyStoredOrLogged"])


if __name__ == "__main__":
    unittest.main()
