import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_workflow import fixture, capture
from silicon_shader.capture import request, status, import_capture
from silicon_shader.common import write
from silicon_shader.discover import java_requirement


class Commands(unittest.TestCase):
    def cli(self, *args, ok=True):
        p = subprocess.run(
            [sys.executable, "-m", "silicon_shader", *map(str, args)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p.returncode, 0 if ok else 2, p.stderr)
        return json.loads(p.stdout if ok else p.stderr)

    def test_end_to_end_baseline_stop_and_daily(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            lab = root / "lab"
            state = root / "session.json"
            self.cli("isolate", src, lab, "--closed")
            self.cli(
                "loop", "start", state, lab, "--scenes", "loaded", "--target-fps", "80"
            )
            proof = capture(95)
            file = root / "baseline.json"
            write(file, proof)
            stopped = self.cli("loop", "submit", state, file)
            self.assertTrue(stopped["stopped"])
            self.cli("loop", "sync", state, lab, "--closed")
            result = self.cli(
                "daily", lab, root / "daily", "--closed", "--session", state
            )
            self.assertIn("unverified", result["status"])
            self.cli("loop", "propose", state, lab, "--closed", ok=False)
            self.assertEqual(
                (src / ".minecraft/options.txt").read_text(),
                (root / "daily/.minecraft/options.txt").read_text(),
            )

    def test_capture_request_timeout_and_import(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            request(root, "one")
            self.assertEqual(status(root, "one")["state"], "starting")
            with self.assertRaises(ValueError):
                request(root, "two")
            # Synthetic clock data exercises the full parser/importer; not gameplay.
            count = 2001
            with (root / "one-frames.csv").open("w") as f:
                f.write("frame,nanotime,interval_ns\n")
                for i in range(count):
                    f.write(f"{i},{1000000000 + i * 10000000},{10000000 if i else 0}\n")
            write(
                root / "one-status.json",
                dict(
                    id="one",
                    state="done",
                    frames=count,
                    unfocused_frames=0,
                    buffer_full=False,
                    error="",
                    metric="cpu_frame_production",
                    hook="synthetic",
                ),
            )
            c = capture()
            manifest = {k: c[k] for k in ("expected", "observed", "visual")}
            result = import_capture(root, "one", manifest)
            self.assertAlmostEqual(result["metrics"]["average_fps"], 100)
            request(root, "two")
            with self.assertRaises(ValueError):
                request(root, "one")

    def test_rollback_refuses_new_edits(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            lab = root / "lab"
            self.cli("isolate", src, lab, "--closed")
            file = root / "profile.json"
            write(file, {"options": {"renderDistance": 16}})
            receipt = self.cli("profile", "apply", lab, file, "--closed")
            (lab / ".minecraft/options.txt").write_text("renderDistance:24\n")
            result = self.cli(
                "profile", "rollback", lab, receipt["id"], "--closed", ok=False
            )
            self.assertIn("changed since", result["error"])

    def test_setup_and_version_requirements(self):
        with tempfile.TemporaryDirectory() as t:
            result = self.cli(
                "setup", Path(t) / "new", "--minecraft", "26.3", "--fabric", "0.19.5"
            )
            self.assertEqual(result["java_required"], 25)
            self.cli(
                "setup",
                Path(t) / "unknown",
                "--minecraft",
                "future-snapshot",
                "--fabric",
                "0.19.5",
                ok=False,
            )
        self.assertEqual(
            [
                java_requirement(x)
                for x in ("1.16.5", "1.17", "1.18", "1.20.4", "1.20.5", "26.3", "27.1")
            ],
            [8, 16, 17, 17, 21, 25, None],
        )


if __name__ == "__main__":
    unittest.main()
