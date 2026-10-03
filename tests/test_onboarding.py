import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from silicon_shader.catalog import select
from silicon_shader.discover import hardware_info, parse_chip
from silicon_shader.doctor import doctor
import test_challenge


class OnboardingTests(unittest.TestCase):
    def test_new_chips_and_machine_privacy(self):
        self.assertEqual(parse_chip("Apple M6"), ("M6", "base"))
        self.assertEqual(parse_chip("Apple A18 Pro"), ("A18", "pro"))
        self.assertEqual(parse_chip("Apple M7 Max"), ("M7", "max"))
        self.assertEqual(parse_chip("Intel Core i7"), (None, None))
        report = {
            "SPHardwareDataType": [
                {
                    "machine_name": "Mac mini",
                    "machine_model": "Mac99,1",
                    "serial_number": "PRIVATE-SERIAL",
                }
            ],
            "SPDisplaysDataType": [{"sppci_model": "Apple M6", "sppci_cores": "12"}],
        }

        def command(args):
            return {
                "machdep.cpu.brand_string": "Apple M6",
                "hw.memsize": str(24 * 2**30),
                "hw.ncpu": "12",
            }.get(args[-1], json.dumps(report))

        with (
            patch("silicon_shader.discover.platform.system", return_value="Darwin"),
            patch("silicon_shader.discover.command", side_effect=command),
        ):
            result = hardware_info()
        self.assertEqual(result["gpu_cores"], 12)
        self.assertNotIn("PRIVATE-SERIAL", json.dumps(result))

    def test_matching_prefers_fit_before_fps_and_labels_fallback(self):
        def entry(digest, memory, gpu, fps):
            return {
                "digest": digest,
                "metadata": {
                    "hardware": {
                        "family": "M4",
                        "tier": "base",
                        "memory_gib": memory,
                        "gpu_cores": gpu,
                    },
                    "minecraft": "26.3",
                    "loader": {"name": "fabric"},
                    "candidate": {"settings": {"render_distance": 20}},
                },
                "runs": {"candidate": {"average_fps": fps, "worst_5s_fps": fps}},
            }

        entries = [entry("a", 24, 10, 90), entry("b", 32, 16, 160)]
        result = select(
            entries,
            target={
                "family": "M4",
                "tier": "base",
                "memory_gib": 24.0,
                "gpu_cores": 10,
            },
        )
        self.assertEqual(result["setups"][0]["digest"], "a")
        self.assertFalse(result["broadened_search"])
        result = select(
            entries,
            target={"family": "M4", "tier": "base", "memory_gib": 16, "gpu_cores": 10},
        )
        self.assertEqual(result["setups"][0]["digest"], "a")
        self.assertTrue(result["broadened_search"])
        self.assertEqual(result["setups"][0]["hardware_differences"], ["memory_gib"])
        self.assertFalse(select(entries, minecraft="1.21.1")["setups"])

    def test_future_hardware_can_be_submitted_without_editing_whitelist(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.meta["hardware"].update(
            family="M6",
            model="Mac mini",
            model_identifier="Mac99,1",
            cpu_cores=12,
            gpu_cores=12,
        )
        fixture.save()
        self.assertEqual(fixture.prepare()["metadata"]["hardware"]["family"], "M6")

    def test_generic_doctor_reads_mods_without_assuming_prism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mods").mkdir()
            (root / ".silicon-shader").mkdir()
            (root / "options.txt").write_text("renderDistance:16\nfullscreen:true\n")
            (root / ".silicon-shader/instance.json").write_text(
                json.dumps({"layout": "game-directory", "game_dir": "."})
            )
            with zipfile.ZipFile(root / "mods/example.jar", "w") as archive:
                archive.writestr(
                    "fabric.mod.json", json.dumps({"id": "sodium", "version": "0.6.13"})
                )
            with zipfile.ZipFile(root / "mods/broken.jar", "w") as archive:
                archive.writestr("fabric.mod.json", "[]")
            result = doctor(root)
            self.assertEqual(result["instance"]["launcher"], "external")
            self.assertEqual(
                next(m for m in result["mods"] if m["id"] == "sodium")["version"],
                "0.6.13",
            )
            self.assertIsNone(
                next(m for m in result["mods"] if m["file"] == "broken.jar")["version"]
            )
