import json
from pathlib import Path
import tempfile
import unittest
from silicon_shader.instances import (
    isolate,
    apply_profile,
    rollback,
    daily,
    current_profile,
)
from silicon_shader.measure import analyze, validate
from silicon_shader.loop import start, submit, propose


def fixture(root):
    p = root / "source"
    (p / ".minecraft/config").mkdir(parents=True)
    (p / ".minecraft/mods").mkdir()
    (p / "mmc-pack.json").write_text(
        json.dumps({"components": [{"uid": "net.minecraft", "version": "26.3"}]})
    )
    (p / "instance.cfg").write_text(
        "[General]\nname=Original\nJvmArgs=-javaagent:/private/a.jar -Xmx4G\nOverrideCommands=true\nPreLaunchCommand=unsafe\n"
    )
    (p / ".minecraft/options.txt").write_text(
        "renderDistance:12\nsimulationDistance:8\nmaxFps:120\nenableVsync:false\nfullscreen:true\n"
    )
    (p / ".minecraft/config/renderscale.json5").write_text(
        '{"scale":0.75,"irisScale":0.75,"targetFrameRate":0}'
    )
    return p


def capture(fps=90, scene="loaded", profile="baseline"):
    ctx = dict(
        instance="lab",
        save="test",
        dimension="overworld",
        scene=scene,
        route="walk-v1",
        terrain="generated-v1",
        hardware="M4-24GB",
        runtime="25-arm64",
        versions="fixture-v1",
        shader="makeup",
        framebuffer=[3024, 1898],
        scale=0.75,
        render_distance=12,
        simulation_distance=8,
        native_framebuffer=[3024, 1898],
        filter="nearest",
        cap=120,
        vsync=False,
        fullscreen=True,
        focused=True,
        throttled=False,
        weather="clear",
        time="noon",
        power="AC",
        background="quiet",
    )
    n = int(fps * 20)
    a = analyze([1000 / fps] * n)
    return dict(
        id="test",
        status="done",
        metric="cpu_frame_production",
        expected=ctx.copy(),
        observed=ctx,
        visual={
            "valid": True,
            "artifacts": False,
            "acceptable_quality": True,
            "reviewer": "human",
        },
        completion={"unfocused_frames": 0, "buffer_full": False, "error": ""},
        profile=profile,
        metrics=a,
    )


class Workflow(unittest.TestCase):
    def test_isolation_rollback_clean_handoff(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            before = (src / ".minecraft/options.txt").read_bytes()
            lab = isolate(src, root / "lab", True)
            self.assertNotIn("unsafe", (lab / "instance.cfg").read_text())
            receipt = apply_profile(
                lab, {"options": {"renderDistance": 16}, "scale": 0.7}, True
            )
            self.assertIn(
                "renderDistance:16", (lab / ".minecraft/options.txt").read_text()
            )
            rollback(lab, receipt["id"], True)
            self.assertEqual((lab / ".minecraft/options.txt").read_bytes(), before)
            (lab / ".minecraft/mods/minescript-test.jar").write_bytes(b"fixture")
            out = daily(lab, root / "daily", True)
            self.assertFalse((out / ".minecraft/mods/minescript-test.jar").exists())
            self.assertEqual((src / ".minecraft/options.txt").read_bytes(), before)

    def test_no_symlink_escape_or_existing_target(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            (src / ".minecraft/config/escape").symlink_to(root)
            with self.assertRaises(ValueError):
                isolate(src, root / "lab", True)
            self.assertFalse((root / "lab").exists())

    def test_refuse_live_ack_missing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            with self.assertRaises(ValueError):
                isolate(fixture(root), root / "lab", False)

    def test_full_shader_profile_and_correctness_fix_preserved(self):
        import zipfile

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            game = src / ".minecraft"
            (game / "config/iris.properties").write_text("shaderPack=example.zip\n")
            (game / "shaderpacks").mkdir()
            shader = game / "shaderpacks/example.zip.txt"
            shader.write_text("CLOUD_SAMPLES=10\nBLOOM=5\n")
            (game / "mods/iris-correctness-fix.jar").write_bytes(
                b"fixture correctness fix"
            )
            with zipfile.ZipFile(game / "mods/renamed.jar", "w") as archive:
                archive.writestr("fabric.mod.json", json.dumps({"id": "minescript"}))
            lab = isolate(src, root / "lab", True)
            with self.assertRaises(ValueError):
                apply_profile(lab, {"shader_properties": {"CLOUD_SAMPLES": 7}}, True)
            apply_profile(
                lab, {"shader_properties": {"CLOUD_SAMPLES": 7, "BLOOM": 5}}, True
            )
            out = daily(lab, root / "daily", True)
            self.assertFalse((out / ".minecraft/mods/renamed.jar").exists())
            self.assertEqual(
                (out / ".minecraft/mods/iris-correctness-fix.jar").read_bytes(),
                b"fixture correctness fix",
            )
            self.assertIn(
                "BLOOM=5", (out / ".minecraft/shaderpacks/example.zip.txt").read_text()
            )
            self.assertEqual(shader.read_text(), "CLOUD_SAMPLES=10\nBLOOM=5\n")

    def test_interrupted_rollback_can_resume(self):
        from unittest.mock import patch
        import shutil

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            lab = isolate(src, root / "lab", True)
            receipt = apply_profile(
                lab, {"options": {"renderDistance": 16}, "scale": 0.7}, True
            )
            original_copy = shutil.copy2

            def fail_second(source, destination, *args, **kwargs):
                if (
                    Path(source).name == "renderscale.json5"
                    and "history" in Path(source).parts
                ):
                    raise OSError("simulated disk interruption")
                return original_copy(source, destination, *args, **kwargs)

            with patch(
                "silicon_shader.instances.shutil.copy2", side_effect=fail_second
            ):
                with self.assertRaises(OSError):
                    rollback(lab, receipt["id"], True)
            rollback(lab, receipt["id"], True)
            self.assertEqual(
                (lab / ".minecraft/options.txt").read_bytes(),
                (src / ".minecraft/options.txt").read_bytes(),
            )
            self.assertEqual(
                (lab / ".minecraft/config/renderscale.json5").read_bytes(),
                (src / ".minecraft/config/renderscale.json5").read_bytes(),
            )

    def test_profile_preserves_scaler_controls(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            config = src / ".minecraft/config/renderscale.json5"
            config.write_text(
                json.dumps(
                    {
                        "scale": 0.75,
                        "irisScale": 0.75,
                        "forceLinear": True,
                        "fsr": True,
                        "targetFrameRate": 0,
                    }
                )
            )
            lab = isolate(src, root / "lab", True)
            profile = current_profile(lab)
            profile["options"]["simulationDistance"] = 6
            apply_profile(lab, profile, True)
            actual = json.loads(
                (lab / ".minecraft/config/renderscale.json5").read_text()
            )
            self.assertTrue(actual["forceLinear"])
            self.assertTrue(actual["fsr"])

    def test_winning_scale_step_can_be_refined(self):
        state = start(["loaded"], target_fps=120, max_trials=3)
        baseline = capture(80)
        baseline["observed"]["simulation_distance"] = baseline["expected"][
            "simulation_distance"
        ] = 6
        submit(state, baseline)
        first = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 6}, "scale": 0.75},
        )
        winner = capture(95, profile=first["id"])
        winner["id"] = "win"
        winner["observed"]["simulation_distance"] = winner["expected"][
            "simulation_distance"
        ] = 6
        winner["observed"]["scale"] = winner["expected"]["scale"] = first["profile"][
            "scale"
        ]
        submit(state, winner)
        second = propose(state, first["profile"])
        self.assertIsNotNone(second)
        self.assertEqual(second["profile"]["scale"], 0.65)

    def test_faster_candidate_with_worse_pacing_is_rejected(self):
        variants = {
            "absolute": [10.0] * 2000,
            "local": [10.0] * 2000,
            "p95": ([9.0] * 9 + [16.0]) * 200,
        }
        variants["absolute"][100] = 60.0
        variants["local"][100] = 25.0
        for label, intervals in variants.items():
            with self.subTest(label=label):
                state = start(["loaded"], target_fps=120)
                submit(state, capture(80))
                plan = propose(
                    state,
                    {
                        "options": {"renderDistance": 12, "simulationDistance": 8},
                        "scale": 0.75,
                    },
                )
                candidate = capture(100, profile=plan["id"])
                candidate["id"] = "candidate"
                candidate["observed"]["simulation_distance"] = candidate["expected"][
                    "simulation_distance"
                ] = 6
                candidate["metrics"] = analyze(intervals)
                submit(state, candidate)
                self.assertGreaterEqual(
                    state["decisions"][-1]["worst_scene_gain"], 0.05
                )
                self.assertEqual(state["winner"], "baseline")
                self.assertFalse(state["decisions"][-1]["pacing_passed"])

    def test_worst_scene_gain_does_not_hide_another_scene_regression(self):
        state = start(["loaded", "water"], target_fps=120)
        for scene, fps in [("loaded", 80), ("water", 110)]:
            row = capture(fps, scene)
            row["id"] = "baseline-" + scene
            submit(state, row)
        plan = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 8}, "scale": 0.75},
        )
        for scene, fps in [("loaded", 95), ("water", 106)]:
            row = capture(fps, scene, plan["id"])
            row["id"] = "candidate-" + scene
            row["observed"]["simulation_distance"] = row["expected"][
                "simulation_distance"
            ] = 6
            submit(state, row)
        self.assertGreaterEqual(state["decisions"][-1]["worst_scene_gain"], 0.05)
        self.assertEqual(state["winner"], "baseline")

    def test_measure_interval_semantics(self):
        a = analyze([10] * 1000 + [60] + [10] * 1000)
        self.assertEqual(a["over_50"]["count"], 1)
        self.assertEqual(a["over_50"]["time_ms"], 60)
        self.assertEqual(a["local_outliers"]["count"], 1)
        self.assertAlmostEqual(a["duration_s"], 20.06)

    def test_invalid_context_and_incomplete_rejected(self):
        a = capture()
        a["observed"]["save"] = "wrong"
        self.assertTrue(validate(a))
        a = capture()
        a["status"] = "recording"
        self.assertTrue(validate(a))
        a = capture()
        a["visual"]["artifacts"] = True
        self.assertTrue(validate(a))
        self.assertEqual(validate(capture()), [])

    def test_bounded_loop_winner_and_plateau(self):
        state = start(["loaded"], target_fps=110, max_trials=2)
        submit(state, capture(80))
        plan = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 8}, "scale": 0.75},
        )
        self.assertEqual(plan["id"], "trial-1")
        a = capture(95, profile="trial-1")
        a["observed"]["scale"] = a["expected"]["scale"] = plan["profile"]["scale"]
        a["id"] = "candidate1"
        a["observed"]["simulation_distance"] = a["expected"]["simulation_distance"] = (
            plan["profile"]["options"]["simulationDistance"]
        )
        submit(state, a)
        self.assertEqual(state["winner"], "trial-1")
        propose(state, plan["profile"])
        b = capture(90, profile="trial-2")
        b["id"] = "candidate2"
        b["observed"]["scale"] = b["expected"]["scale"] = state["pending"]["profile"][
            "scale"
        ]
        b["observed"]["simulation_distance"] = b["expected"]["simulation_distance"] = (
            state["pending"]["profile"]["options"]["simulationDistance"]
        )
        submit(state, b)
        self.assertTrue(state["stopped"])
        self.assertEqual(state["winner"], "trial-1")


if __name__ == "__main__":
    unittest.main()
