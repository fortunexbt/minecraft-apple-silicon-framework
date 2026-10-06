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
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(forbidden, self.script, forbidden)

    def test_results_grid_is_not_a_live_region(self):
        # A live region over the whole grid re-reads every card on each filter change.
        self.assertNotRegex(self.html, r'id="results"[^>]*aria-live')

    def test_noscript_fallback_points_at_the_data(self):
        self.assertIn("<noscript>", self.html)
        self.assertIn("data.json", self.html)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_script_parses(self):
        result = subprocess.run(["node", "--check", str(SITE / "app.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
