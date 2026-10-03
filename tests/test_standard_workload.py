import copy
import unittest
from unittest.mock import Mock
import test_challenge
from standard_fixture import standard_bundle, seal
from silicon_shader.challenge import validate_bundle
from silicon_shader.community import submit
from silicon_shader.measure import analyze


class StandardWorkloadTests(unittest.TestCase):
    def setUp(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.legacy = fixture.prepare()
        self.bundle = standard_bundle(self.legacy)

    def test_current_roundtrip_and_legacy_read_only(self):
        self.assertEqual(validate_bundle(self.bundle), [])
        self.assertEqual(validate_bundle(self.legacy), [])
        request = Mock(side_effect=AssertionError("No network"))
        with self.assertRaisesRegex(ValueError, "standard route"):
            submit(self.legacy, publish=True, request=request)
        request.assert_not_called()

    def test_wrong_world_rejected_even_with_recomputed_digest(self):
        for key, value in (
            ("seed", 0),
            ("generator", "net.minecraft.world.level.levelgen.FlatLevelSource"),
            ("biome_preset_overworld", False),
            ("datapacks", ["vanilla", "custom-world"]),
        ):
            bundle = copy.deepcopy(self.bundle)
            bundle["runs"]["candidate"]["route_receipt"]["world"][key] = value
            self.assertTrue(validate_bundle(seal(bundle)), key)

    def test_slow_frames_remain_in_a_complete_route(self):
        # A stall stretches the same tick-indexed path. It is evidence of poor
        # pacing, not grounds to discard the run and report only smooth runs.
        run = self.bundle["runs"]["candidate"]
        run["intervals_ms"][1000] += 1500
        run["metrics"] = analyze(run["intervals_ms"])
        for sample in run["route_receipt"]["samples"][11:]:
            sample["t"] += 1.5
            sample["game_tick"] += 30
        self.assertEqual(validate_bundle(seal(self.bundle)), [])
        self.assertEqual(run["metrics"]["max_ms"], 1510)
        # The frame that closes the route must survive even if it stalls too.
        run["intervals_ms"][-1] += 1500
        run["metrics"] = analyze(run["intervals_ms"])
        self.assertEqual(validate_bundle(seal(self.bundle)), [])

    def test_wrong_or_interrupted_trajectory_rejected(self):
        for key, value in (
            ("position", [0, 100, 0]),
            ("yaw", 45),
            ("flying", False),
            ("focused", False),
            ("paused", True),
            ("tick", 123),
            ("framebuffer", [320, 200]),
        ):
            bundle = copy.deepcopy(self.bundle)
            bundle["runs"]["candidate"]["route_receipt"]["samples"][10][key] = value
            self.assertTrue(validate_bundle(seal(bundle)), key)
        bundle = copy.deepcopy(self.bundle)
        receipt = bundle["runs"]["candidate"]["route_receipt"]
        for sample in receipt["samples"]:
            sample["position"] = receipt["samples"][0]["position"]
        self.assertTrue(validate_bundle(seal(bundle)))

    def test_receipts_require_real_capture_association_and_warmup(self):
        for field, value in (
            ("csv_sha256", "0" * 64),
            ("samples", []),
            ("warmup", {"seconds": 1, "ticks": 20, "samples": []}),
        ):
            bundle = copy.deepcopy(self.bundle)
            bundle["runs"]["candidate"]["route_receipt"][field] = value
            self.assertTrue(validate_bundle(seal(bundle)), field)
        bundle = copy.deepcopy(self.bundle)
        for sample in bundle["runs"]["candidate"]["route_receipt"]["samples"]:
            sample["t"] += 1
        self.assertTrue(validate_bundle(seal(bundle)))
