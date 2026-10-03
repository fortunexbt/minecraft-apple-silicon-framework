import json
from pathlib import Path
import tempfile
import unittest
from silicon_shader.instances import isolate, apply_profile, rollback, daily
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
