"""The PNG check protects against renderer/window dimension mismatches."""

import struct
import tempfile
import unittest
from pathlib import Path

from silicon_shader.presentation import inspect_screenshot


class PortraitTests(unittest.TestCase):
    def test_dimensions_do_not_claim_visual_validity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "portrait.png"
            header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            path.write_bytes(header + struct.pack(">II", 1920, 1080))
            result = inspect_screenshot(path)
            self.assertTrue(result["visual_review_required"])
            self.assertEqual(result["dimensions"], [1920, 1080])
            path.write_bytes(header + struct.pack(">II", 3200, 1800))
            with self.assertRaisesRegex(ValueError, "3200x1800"):
                inspect_screenshot(path)
            path.write_bytes(b"not a PNG")
            with self.assertRaisesRegex(ValueError, "original Minecraft PNG"):
                inspect_screenshot(path)
