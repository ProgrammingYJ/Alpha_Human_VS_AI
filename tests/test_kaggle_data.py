"""Mock-network checks for bounded downloads; never contact Kaggle."""

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from alpha_captcha.kaggle_data import dataset_metadata, fetch_kaggle_file


class MockResponse(io.BytesIO):
    def __init__(self, body, content_type="image/png", *, length=None, status=200, extra_headers=None):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": content_type}
        if length is not None:
            self.headers["Content-Length"] = str(length)
        self.headers.update(extra_headers or {})

    def getcode(self):
        return self.status


class KaggleDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.destination = self.root / "data/raw/kaggle/fixture/picture.png"
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
        self.png = buffer.getvalue()

    def fetch(self, destination=None, **changes):
        kwargs = dict(workspace_root=self.root, max_bytes=1024, expected_kind="image")
        kwargs.update(changes)
        return fetch_kaggle_file("fixture/scenes", "images/picture.png",
                                 destination or self.destination, **kwargs)

    def assert_no_partial_files(self):
        self.assertEqual(list(self.root.rglob("*.part")), [])

    def test_success_and_existing_original_is_reused_without_network(self):
        with patch("urllib.request.urlopen", return_value=MockResponse(self.png, length=len(self.png))) as opened:
            result = self.fetch()
            self.assertTrue(result["downloaded"])
            self.assertEqual(result["sha256"], hashlib.sha256(self.png).hexdigest())
            self.assertEqual(self.destination.read_bytes(), self.png)
            opened.assert_called_once()
        with patch("urllib.request.urlopen") as opened:
            reused = self.fetch()
            self.assertFalse(reused["downloaded"])
            self.assertEqual(self.destination.read_bytes(), self.png)
            opened.assert_not_called()
        self.assert_no_partial_files()

    def test_html_zip_and_forged_image_mime_are_not_saved(self):
        cases = [(b"<html>Sign in</html>", "text/html"),
                 (b"PKarchive", "application/zip"),
                 (b"<html>Sign in</html>", "image/png")]
        for body, content_type in cases:
            with self.subTest(content_type=content_type):
                with patch("urllib.request.urlopen", return_value=MockResponse(body, content_type)):
                    with self.assertRaises((ValueError, OSError)):
                        self.fetch()
                self.assertFalse(self.destination.exists())
                self.assert_no_partial_files()

    def test_declared_and_streamed_oversize_are_rejected_and_cleaned(self):
        for length in (10_000, None):
            with self.subTest(length=length):
                with patch("urllib.request.urlopen", return_value=MockResponse(self.png, length=length)):
                    with self.assertRaisesRegex(ValueError, "max_bytes"):
                        self.fetch(max_bytes=10)
                self.assertFalse(self.destination.exists())
                self.assert_no_partial_files()

    def test_incomplete_content_length_is_rejected_and_cleaned(self):
        with patch("urllib.request.urlopen", return_value=MockResponse(self.png, length=len(self.png) + 10)):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                self.fetch()
        self.assertFalse(self.destination.exists())
        self.assert_no_partial_files()

    def test_unsolicited_partial_http_response_is_rejected(self):
        response = MockResponse(self.png, length=len(self.png), status=206,
                                extra_headers={"Content-Range": f"bytes 0-{len(self.png)-1}/10000"})
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaises(ValueError):
                self.fetch()
        self.assertFalse(self.destination.exists())
        self.assert_no_partial_files()

    def test_outside_paths_and_remote_traversal_are_rejected_before_network(self):
        paths = [self.root / "data/raw/school/picture.png", self.root / "picture.png",
                 self.root / "data/raw/kaggle/../school/picture.png"]
        with patch("urllib.request.urlopen") as opened:
            for destination in paths:
                with self.subTest(destination=str(destination)), self.assertRaises(ValueError):
                    self.fetch(destination)
            for remote in ("../picture.png", "/picture.png", "folder\\picture.png"):
                with self.subTest(remote=remote), self.assertRaises(ValueError):
                    fetch_kaggle_file("fixture/scenes", remote, self.destination,
                                      workspace_root=self.root, max_bytes=1024, expected_kind="image")
            opened.assert_not_called()

    def test_symlinked_kaggle_root_cannot_point_to_school(self):
        school = self.root / "data/raw/school"
        school.mkdir(parents=True)
        try:
            (school.parent / "kaggle").symlink_to(school, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink unavailable: {error}")
        with patch("urllib.request.urlopen", return_value=MockResponse(self.png)) as opened:
            with self.assertRaises(ValueError):
                self.fetch()
            opened.assert_not_called()
        self.assertEqual(list(school.rglob("*")), [])

    def test_full_json_must_parse_before_becoming_a_cached_original(self):
        destination = self.destination.with_suffix(".json")
        for body in (b'{"broken":', b'{"ok":true} trailing junk'):
            with self.subTest(body=body):
                with patch("urllib.request.urlopen", return_value=MockResponse(body, "application/json")):
                    with self.assertRaises(ValueError):
                        self.fetch(destination, expected_kind="json")
                self.assertFalse(destination.exists())
                self.assert_no_partial_files()

    def test_valid_json_and_existing_broken_json_not_overwritten(self):
        destination = self.destination.with_suffix(".json")
        body = b'{"images":[]}'
        with patch("urllib.request.urlopen", return_value=MockResponse(body, "application/json", length=len(body))):
            self.assertTrue(self.fetch(destination, expected_kind="json")["downloaded"])
        destination.write_bytes(b'{"broken":')
        with patch("urllib.request.urlopen") as opened:
            with self.assertRaises(ValueError):
                self.fetch(destination, expected_kind="json")
            opened.assert_not_called()
        self.assertEqual(destination.read_bytes(), b'{"broken":')

    def test_metadata_ref_and_positive_integer_version_are_checked(self):
        invalid = [dict(ref="other/data", currentVersionNumber=2),
                   dict(ref="fixture/scenes", currentVersionNumber=True),
                   dict(ref="fixture/scenes", currentVersionNumber=0), []]
        for value in invalid:
            with self.subTest(value=value):
                body = json.dumps(value).encode()
                with patch("urllib.request.urlopen", return_value=MockResponse(body, "application/json")):
                    with self.assertRaises(ValueError):
                        dataset_metadata("fixture/scenes")


if __name__ == "__main__":
    unittest.main()
