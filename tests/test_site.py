"""Static consistency checks for the public page: no browser needed."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


class SiteConsistency(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "index.html").read_text()
        self.script = (SITE / "app.js").read_text()

    def test_every_element_the_script_looks_up_exists(self):
        ids = set(re.findall(r"byId\('([^']+)'\)", self.script))
        ids |= set(re.findall(r"\['(filter-[a-z-]+|sort-by)'", self.script))
        ids |= set(re.findall(r"'((?:filter|sort)-[a-z-]+)':", self.script))
        present = set(re.findall(r'id="([^"]+)"', self.html))
        self.assertEqual(sorted(i for i in ids if i not in present), [])

    def test_no_dynamic_html_injection(self):
        for forbidden in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "document.write",
            "eval(",
        ):
            self.assertNotIn(forbidden, self.script, forbidden)

    def test_results_grid_is_not_a_live_region(self):
        # A live region over the whole grid re-reads every card on each filter change.
        self.assertNotRegex(self.html, r'id="results"[^>]*aria-live')

    def test_noscript_fallback_points_at_the_data(self):
        self.assertIn("<noscript>", self.html)
        self.assertIn("data.json", self.html)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_script_parses(self):
        result = subprocess.run(
            ["node", "--check", str(SITE / "app.js")], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()


class Thumbnails(unittest.TestCase):
    def setUp(self):
        import importlib.util
        import sys

        if importlib.util.find_spec("PIL") is None:
            self.skipTest("Pillow is not installed")
        sys.path.insert(0, str(SITE.parent / "scripts"))
        import make_thumbs

        self.module = make_thumbs

    def png(self, width, height):
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (width, height), (40, 90, 160)).save(buffer, "PNG")
        return buffer.getvalue()

    def test_writes_each_width_that_fits_and_keeps_the_aspect_ratio(self):
        import tempfile

        from PIL import Image

        with tempfile.TemporaryDirectory() as folder:
            made = self.module.make_thumbnails(self.png(1920, 1080), "a" * 64, folder)
            self.assertEqual(made, [640, 1280])
            small = Image.open(Path(folder) / ("a" * 64 + "-640.webp"))
            self.assertEqual(small.size, (640, 360))

    def test_small_sources_are_not_upscaled(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                self.module.make_thumbnails(self.png(800, 450), "b" * 64, folder), [640]
            )
            self.assertEqual(
                self.module.make_thumbnails(self.png(300, 200), "c" * 64, folder), []
            )

    def test_only_commit_pinned_raw_github_screenshots_are_fetched(self):
        pinned = "https://raw.githubusercontent.com/o/r/" + "a" * 40 + "/x/shot.png"
        self.assertTrue(self.module.PINNED.fullmatch(pinned))
        for bad in (
            "https://raw.githubusercontent.com/o/r/main/shot.png",
            "https://example.com/" + "a" * 40 + "/shot.png",
            pinned + "?x=1",
            "http://raw.githubusercontent.com/o/r/" + "a" * 40 + "/shot.png",
        ):
            self.assertFalse(self.module.PINNED.fullmatch(bad), bad)

    def test_a_failed_download_is_skipped_not_fatal(self):
        import json
        import tempfile
        from unittest.mock import patch

        data = {
            "entries": [
                {
                    "digest": "d" * 64,
                    "presentation": {
                        "screenshot_url": "https://raw.githubusercontent.com/o/r/"
                        + "a" * 40
                        + "/s.png"
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "data.json"
            source.write_text(json.dumps(data))
            with patch.object(self.module, "fetch", side_effect=OSError("offline")):
                self.assertEqual(self.module.build(source, Path(folder) / "t"), {})
            self.assertEqual(
                json.loads((Path(folder) / "t" / "index.json").read_text()), {}
            )
