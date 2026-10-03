import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from silicon_shader.challenge import prepare, validate_bundle
from silicon_shader.measure import analyze

ROOT = Path(__file__).resolve().parents[1]


class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meta = json.loads((ROOT / "examples/challenge-metadata.json").read_text())
        context = json.loads((ROOT / "examples/capture-manifest.json").read_text())[
            "expected"
        ]
        context["game_mode"] = "creative"
        self.captures = {}
        for name in ("baseline", "candidate"):
            csv = "frame,nanotime,interval_ns\n0,900000000000,0\n"
            csv += "".join(
                f"{i},{900000000000 + i * 10000000},10000000\n" for i in range(1, 2001)
            )
            (self.root / (name + ".csv")).write_text(csv)
            observed = copy.deepcopy(context)
            observed["scale"] = self.meta[name]["settings"]["scale"]
            capture = {
                "id": name,
                "status": "done",
                "metric": "cpu_frame_production",
                "expected": observed,
                "observed": copy.deepcopy(observed),
                "visual": {
                    "valid": True,
                    "artifacts": False,
                    "acceptable_quality": True,
                    "reviewer": "private-person",
                },
                "completion": {
                    "unfocused_frames": 0,
                    "buffer_full": False,
                    "error": "",
                },
                "metrics": analyze([10.0] * 2000),
                "provenance": {"csv_sha256": hashlib.sha256(csv.encode()).hexdigest()},
            }
            self.captures[name] = capture
        self.save()

    def save(self):
        for name, capture in self.captures.items():
            (self.root / (name + ".json")).write_text(json.dumps(capture))
        (self.root / "metadata.json").write_text(json.dumps(self.meta))

    def prepare(self):
        return prepare(
            *(
                self.root / p
                for p in (
                    "baseline.json",
                    "candidate.json",
                    "baseline.csv",
                    "candidate.csv",
                    "metadata.json",
                )
            )
        )

    def test_roundtrip_and_privacy(self):
        bundle = self.prepare()
        self.assertEqual([], validate_bundle(bundle))
        self.assertEqual(bundle, self.prepare())
        serialized = json.dumps(bundle)
        for private in (
            "private-person",
            "nanotime",
            "900000000000",
            '"save"',
            '"instance"',
        ):
            self.assertNotIn(private, serialized)

    def test_metric_and_digest_tampering(self):
        bundle = self.prepare()
        bundle["runs"]["candidate"]["metrics"]["average_fps"] = 999
        self.assertTrue(validate_bundle(bundle))
        bundle = self.prepare()
        bundle["metadata"]["launcher"] = "OtherLauncher"
        self.assertTrue(validate_bundle(bundle))

    def test_raw_csv_and_missing_provenance(self):
        path = self.root / "candidate.csv"
        path.write_text(path.read_text().replace("900010000000", "900010000001"))
        with self.assertRaises(ValueError):
            self.prepare()
        self.captures["candidate"].pop("provenance")
        self.save()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_inconsistent_csv_with_matching_provenance(self):
        path = self.root / "candidate.csv"
        path.write_text(path.read_text().replace("900010000000", "900010000001"))
        self.captures["candidate"]["provenance"]["csv_sha256"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        self.save()
        with self.assertRaisesRegex(ValueError, "timestamps"):
            self.prepare()

    def test_private_save_mismatch_and_gameplay_gate(self):
        for part in ("expected", "observed"):
            self.captures["candidate"][part]["save"] = "another-private-save"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unmatched capture context: save"):
            self.prepare()
        for part in ("expected", "observed"):
            self.captures["candidate"][part]["save"] = self.captures["baseline"][part][
                "save"
            ]
            self.captures["candidate"][part]["player_alive"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "living-player"):
            self.prepare()

    def test_duration_bounds_and_cohort_identity(self):
        from silicon_shader.challenge import _cohort

        bundle = self.prepare()
        changed = copy.deepcopy(bundle)
        changed["metadata"]["workload"]["scene"] = "new-scene"
        self.assertNotEqual(_cohort(bundle), _cohort(changed))
        changed["runs"]["candidate"]["intervals_ms"] = [10.0] * 1000
        self.assertTrue(validate_bundle(changed))

    def test_mismatched_context(self):
        for part in ("expected", "observed"):
            self.captures["candidate"][part]["route"] = "different-route"
        self.save()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_private_metadata_and_unreviewed_quality(self):
        for value in (
            "/Users/private",
            "https://example.com",
            "a@example.com",
            "ghp_secret",
            "a" * 40,
        ):
            self.meta["launcher"] = value
            self.save()
            with self.assertRaises(ValueError):
                self.prepare()
        self.meta["launcher"] = "Prism"
        self.meta["quality_review"]["reviewed"] = False
        self.save()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_invalid_trace_and_untrusted_shapes(self):
        bundle = self.prepare()
        for values in ([float("nan")], [-1] * 2000, [True] * 2000, [10] * 30001):
            broken = copy.deepcopy(bundle)
            broken["runs"]["candidate"]["intervals_ms"] = values
            self.assertTrue(validate_bundle(broken))
        for value in (None, [], {}, {"schema_version": []}):
            self.assertTrue(validate_bundle(value))
        (self.root / "metadata.json").write_text('{"x":1,"x":2}')
        with self.assertRaises(ValueError):
            self.prepare()

    def test_undeclared_change_and_self_verified(self):
        self.meta["candidate"]["mods"]["iris"] = "2.0"
        self.save()
        with self.assertRaises(ValueError):
            self.prepare()
        self.meta["interventions"].append("mods")
        self.save()
        bundle = self.prepare()
        self.assertEqual([], validate_bundle(bundle))
        bundle["status"] = "verified"
        self.assertTrue(validate_bundle(bundle))


if __name__ == "__main__":
    unittest.main()
