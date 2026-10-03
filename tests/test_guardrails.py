import json
from pathlib import Path
import tempfile
import unittest
from test_workflow import fixture, capture
from silicon_shader.loop import start, submit, propose
from silicon_shader.measure import validate, read_csv
from silicon_shader.doctor import doctor


class Guardrails(unittest.TestCase):
    def test_constraints_preserve_the_users_quality_floor(self):
        state = start(
            ["loaded"], target_fps=120, min_scale=0.75, min_render_distance=22
        )
        row = capture(80)
        row["expected"]["render_distance"] = row["observed"]["render_distance"] = 22
        row["expected"]["simulation_distance"] = row["observed"][
            "simulation_distance"
        ] = 6
        submit(state, row)
        result = propose(
            state,
            {"options": {"renderDistance": 22, "simulationDistance": 6}, "scale": 0.75},
        )
        self.assertIsNone(result)
        self.assertTrue(state["stopped"])
        self.assertEqual(state["winner"], "baseline")

    def test_configured_floor_cannot_be_bypassed_by_baseline(self):
        state = start(["loaded"], min_scale=0.8, min_render_distance=20)
        with self.assertRaises(ValueError):
            submit(state, capture())
        self.assertEqual(state["captures"], {})

    def test_death_and_menu_readings_never_become_gameplay_evidence(self):
        for field, value in [
            ("game_state", "death_screen"),
            ("game_state", "menu"),
            ("player_alive", False),
        ]:
            row = capture()
            row["expected"][field] = row["observed"][field] = value
            self.assertTrue(validate(row))
        row = capture()
        row["expected"].pop("game_state")
        row["observed"].pop("game_state")
        self.assertTrue(validate(row))

    def test_good_average_does_not_accept_abrupt_outliers(self):
        row = capture(100)
        row["metrics"]["local_outliers"]["count"] = 1
        state = start(["loaded"], target_fps=85)
        submit(state, row)
        self.assertFalse(state["stopped"])

    def test_doctor_is_read_only_and_never_claims_gameplay_qualification(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            before = {
                str(p.relative_to(src)): p.read_bytes()
                for p in src.rglob("*")
                if p.is_file()
            }
            report = doctor(src)
            self.assertFalse(report["configuration_ready"])
            self.assertFalse(report["gameplay_verified"])
            self.assertIn("shader_missing", [i["code"] for i in report["issues"]])
            game = src / ".minecraft"
            (game / "shaderpacks").mkdir()
            import zipfile

            with zipfile.ZipFile(game / "shaderpacks/test.zip", "w") as archive:
                archive.writestr("shaders/shaders.properties", "fixture")
            (game / "config/iris.properties").write_text(
                "shaderPack=test.zip\nenableShaders=true\n"
            )
            report = doctor(src)
            self.assertTrue(report["configuration_ready"])
            self.assertIsNone(report["manifest_template"]["observed"]["game_state"])
            self.assertEqual(report["manifest_template"]["expected"]["scale"], 0.75)
            for rel, data in before.items():
                self.assertEqual((src / rel).read_bytes(), data)

    def test_csv_rejects_wrong_order_and_time_deltas(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "frames.csv"
            for rows in (
                "0,100,0\n2,110,10\n",
                "0,100,0\n1,100,0\n",
                "0,100,0\n1,110,11\n",
            ):
                p.write_text("frame,nanotime,interval_ns\n" + rows)
                with self.assertRaises(ValueError):
                    read_csv(p)

    def test_fractional_floor_is_not_rounded_down(self):
        state = start(["loaded"], target_fps=120, min_scale=0.751)
        row = capture(80)
        row["expected"]["scale"] = row["observed"]["scale"] = 0.8
        row["expected"]["simulation_distance"] = row["observed"][
            "simulation_distance"
        ] = 6
        submit(state, row)
        plan = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 6}, "scale": 0.8},
        )
        self.assertEqual(plan["profile"]["scale"], 0.751)

    def test_quality_mode_can_spend_headroom_on_resolution(self):
        state = start(
            ["loaded"],
            target_fps=85,
            objective="quality",
            max_scale=0.8,
            max_render_distance=12,
        )
        submit(state, capture(110))
        self.assertFalse(state["stopped"])
        plan = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 8}, "scale": 0.75},
        )
        self.assertEqual(plan["profile"]["scale"], 0.8)
        row = capture(95, profile=plan["id"])
        row["id"] = "quality-win"
        row["expected"]["scale"] = row["observed"]["scale"] = 0.8
        submit(state, row)
        self.assertEqual(state["winner"], plan["id"])
        self.assertIsNone(propose(state, plan["profile"]))
        self.assertTrue(state["stopped"])

    def test_quality_mode_rejects_a_prettier_but_too_slow_candidate(self):
        state = start(["loaded"], target_fps=85, objective="quality")
        submit(state, capture(110))
        plan = propose(
            state,
            {"options": {"renderDistance": 12, "simulationDistance": 8}, "scale": 0.75},
        )
        row = capture(75, profile=plan["id"])
        row["id"] = "too-slow"
        row["expected"]["scale"] = row["observed"]["scale"] = 0.8
        submit(state, row)
        self.assertEqual(state["winner"], "baseline")
        self.assertEqual(state["decisions"][-1]["decision"], "reject")

    def test_wrong_shader_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = fixture(root)
            game = src / ".minecraft"
            (game / "shaderpacks").mkdir()
            (root / "external.zip").write_bytes(b"private")
            (game / "shaderpacks/test.zip").symlink_to(root / "external.zip")
            (game / "config/iris.properties").write_text(
                "shaderPack=test.zip\nenableShaders=true\n"
            )
            report = doctor(src)
            self.assertIn("unsafe_path", [i["code"] for i in report["issues"]])


if __name__ == "__main__":
    unittest.main()


class GenericLauncherTests(unittest.TestCase):
    def test_generic_copy_preserves_source_and_requires_external_launcher_review(self):
        from silicon_shader.instances import isolate, daily, MARKER
        from silicon_shader.doctor import doctor
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "custom-game"
            source.mkdir()
            options = (
                "renderDistance:16\nsimulationDistance:8\nmaxFps:120\nfullscreen:true\n"
            )
            (source / "options.txt").write_text(options)
            (source / "accounts.json").write_text("private")
            (source / "mods").mkdir()
            with patch("silicon_shader.instances.closed"):
                lab = isolate(source, root / "lab", True, game_directory=True)
                output = daily(lab, root / "daily", True)
            self.assertEqual((source / "options.txt").read_text(), options)
            self.assertFalse((lab / "accounts.json").exists())
            self.assertTrue(
                json.loads((output / MARKER).read_text())["launcher_cleanup_required"]
            )
            self.assertFalse((output / "instance.cfg").exists())
            self.assertIsInstance(doctor(source, game_directory=True), dict)
