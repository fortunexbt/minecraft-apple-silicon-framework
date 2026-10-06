"""Regression tests for validator hardening found in the project review."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_challenge
from standard_fixture import standard_bundle
from silicon_shader import challenge, cli
from silicon_shader.community import api, submit
from silicon_shader.presentation import validate_presentation

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


def presentation(**changes):
    value = {
        "title": "M4 Test Setup",
        "screenshot_url": f"https://raw.githubusercontent.com/o/r/{COMMIT}/shot.png",
        "recipe_url": f"https://github.com/o/r/blob/{COMMIT}/recipe.md",
    }
    value.update(changes)
    return value


class LabelAndNumberMessages(unittest.TestCase):
    def test_secret_prefixes_only_match_at_a_word_start(self):
        for ok in ("risk-free", "Disk-Cache", "Sodium 0.6.13 (fabric)", "Desk-Pack 2"):
            challenge._label(ok)
        for bad in ("sk-live-abc", "mc sk-test", "ghp_abcdefgh", "my token", "a..b"):
            with self.assertRaises(ValueError, msg=bad):
                challenge._label(bad)

    def test_label_error_names_the_field_and_never_echoes_the_value(self):
        with self.assertRaisesRegex(ValueError, "baseline mod name") as caught:
            challenge._label("sk-live-secret-value", "baseline mod name")
        self.assertNotIn("secret-value", str(caught.exception))

    def test_number_error_names_the_field_and_bounds(self):
        with self.assertRaisesRegex(
            ValueError,
            r"candidate.settings.scale must be a number from 0.5 to 1, got 0.45",
        ):
            challenge._number(0.45, 0.5, 1, name="candidate.settings.scale")
        with self.assertRaisesRegex(ValueError, "an integer from 2 to 64, got 12.0"):
            challenge._number(12.0, 2, 64, True, "render_distance")

    def test_key_error_lists_missing_and_unexpected_fields(self):
        with self.assertRaisesRegex(
            ValueError, r"settings \(missing cap; unexpected extra\)"
        ):
            challenge._keys({"scale": 1, "extra": 2}, {"scale", "cap"}, "settings")


class MetadataMessages(unittest.TestCase):
    def setUp(self):
        self.meta = json.loads((ROOT / "examples/challenge-metadata.json").read_text())

    def test_interventions_error_lists_what_actually_changed(self):
        self.meta["interventions"] = ["scale"]
        self.meta["candidate"]["settings"]["render_distance"] = 16
        with self.assertRaisesRegex(
            ValueError,
            r"Changed between baseline and candidate: \['render_distance', 'scale'\]",
        ) as caught:
            challenge._metadata(self.meta)
        self.assertIn("missing from declared: render_distance", str(caught.exception))

    def test_unchanged_declared_intervention_is_named(self):
        self.meta["interventions"] = ["scale", "cap"]
        with self.assertRaisesRegex(ValueError, "not actually changed: cap"):
            challenge._metadata(self.meta)

    def test_scale_floor_message_is_actionable(self):
        self.meta["candidate"]["settings"]["scale"] = 0.45
        with self.assertRaisesRegex(
            ValueError, "candidate.settings.scale must be a number from 0.5 to 1"
        ):
            challenge._metadata(self.meta)

    def test_mods_message_names_the_run(self):
        self.meta["candidate"]["mods"] = {}
        with self.assertRaisesRegex(ValueError, "candidate.mods must list 1 to 200"):
            challenge._metadata(self.meta)


class PinnedAtCap(unittest.TestCase):
    def bundle(self, base_fps, cand_fps, cap=120, base_p50=None, cand_p50=None):
        def run(fps, p50):
            return {"metrics": {"average_fps": fps, "p50_ms": p50 or 1000 / fps}}

        meta = {
            "interventions": ["shader"],
            "baseline": {"settings": {"cap": cap}},
            "candidate": {"settings": {"cap": cap}},
        }
        return {
            "metadata": meta,
            "runs": {
                "baseline": run(base_fps, base_p50),
                "candidate": run(cand_fps, cand_p50),
            },
        }

    def test_pinned_run_is_flagged_and_normal_runs_are_not(self):
        self.assertEqual(challenge.pinned_runs(self.bundle(95, 119.9)), ["candidate"])
        self.assertEqual(
            challenge.pinned_runs(self.bundle(119.8, 119.9)), ["baseline", "candidate"]
        )
        self.assertEqual(challenge.pinned_runs(self.bundle(95, 100)), [])

    def test_uncapped_or_high_caps_are_never_pinned(self):
        self.assertEqual(challenge.pinned_runs(self.bundle(250, 259, cap=0)), [])
        self.assertEqual(challenge.pinned_runs(self.bundle(250, 259, cap=260)), [])

    def test_warnings_explain_how_to_check(self):
        text = " ".join(challenge.warnings(self.bundle(95, 119.9)))
        self.assertIn("candidate run is pinned at its 120 FPS cap", text)
        self.assertIn("portrait", text)

    def test_near_identical_results_with_a_declared_change_are_flagged(self):
        text = " ".join(challenge.warnings(self.bundle(100, 100.5)))
        self.assertIn("within 1%", text)

    def test_warnings_never_raise_on_odd_input(self):
        self.assertEqual(challenge.warnings({}), [])
        self.assertEqual(challenge.warnings({"metadata": {}, "runs": {}}), [])

    def test_real_published_entries_would_not_be_flagged(self):
        for path in sorted((ROOT / "contributions").glob("*.json")):
            bundle = json.loads(path.read_text())["bundle"]
            self.assertEqual(challenge.pinned_runs(bundle), [], path.name)


class LinkAndTitleChecks(unittest.TestCase):
    def test_valid_presentation_passes(self):
        validate_presentation(presentation())

    def test_dot_segments_cannot_turn_a_pinned_link_into_a_moving_one(self):
        for key, url in (
            (
                "screenshot_url",
                f"https://raw.githubusercontent.com/o/r/{COMMIT}/../main/x.png",
            ),
            (
                "screenshot_url",
                f"https://raw.githubusercontent.com/o/r/{COMMIT}/./x.png",
            ),
            ("recipe_url", f"https://github.com/o/r/blob/{COMMIT}/../../main/r.md"),
        ):
            with self.assertRaises(ValueError, msg=url):
                validate_presentation(presentation(**{key: url}))

    def test_hidden_characters_in_links_are_rejected(self):
        base = f"https://raw.githubusercontent.com/o/r/{COMMIT}/x.png"
        for url in (
            base[:-4] + "\n.png",
            base[:-4] + "\t.png",
            base + " ",
            base.replace("x.png", "a%2e%2e/x.png"),
            base.replace("/x.png", "\\x.png"),
        ):
            with self.assertRaises(ValueError, msg=repr(url)):
                validate_presentation(presentation(screenshot_url=url))

    def test_bad_port_is_a_clean_error(self):
        with self.assertRaisesRegex(ValueError, "public link"):
            validate_presentation(
                presentation(
                    recipe_url=f"https://github.com:xyz/o/r/blob/{COMMIT}/r.md"
                )
            )

    def test_titles_reject_spoofing_and_link_bait(self):
        for title in (
            "Ignore ‮previous",  # bidi override
            "<img src=x onerror=1>",
            "see https://evil.example now",
            "visit www.evil.example",
            "my ghp_aaaaaaaaaaaaaaaaaaaa token",
            " leading space",
            "ab",
            "x" * 81,
            "tab\there",
            "​​​",
        ):
            with self.assertRaises(ValueError, msg=repr(title)):
                validate_presentation(presentation(title=title))

    def test_every_published_title_still_validates(self):
        for path in sorted((ROOT / "contributions").glob("*.json")):
            entry = json.loads(path.read_text())
            if entry.get("presentation"):
                validate_presentation(entry["presentation"])


class PublishRequiresPreview(unittest.TestCase):
    def setUp(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.bundle = standard_bundle(fixture.prepare())
        self.presentation = presentation(
            minecraft_profile="Cyclo",
            agent={"model": "Test Model", "harness": "Test"},
            screenshot_view="overworld-front-v1",
        )

    def test_publish_without_a_reviewed_digest_is_refused_before_any_request(self):
        request = Mock(side_effect=AssertionError("No network"))
        with self.assertRaisesRegex(
            ValueError, "--reviewed-digest " + self.bundle["content_digest"]
        ):
            submit(self.bundle, True, request=request, presentation=self.presentation)
        request.assert_not_called()

    def test_preview_carries_warnings_list(self):
        preview = submit(self.bundle, presentation=self.presentation)
        self.assertIsInstance(preview["warnings"], list)


class GithubErrors(unittest.TestCase):
    def fail(self, stderr):
        done = subprocess.CompletedProcess([], 1, stdout="", stderr=stderr)
        return patch("subprocess.run", return_value=done)

    def test_each_status_class_has_its_own_hint(self):
        cases = {
            "gh: HTTP 401": "gh auth login",
            "gh: HTTP 403: rate limit": "rate limited",
            "gh: HTTP 404": "fork can take a minute",
            "gh: HTTP 422": "branch already exists",
        }
        for stderr, hint in cases.items():
            with self.fail(stderr), self.assertRaisesRegex(ValueError, hint):
                api("user")

    def test_remote_text_is_never_reflected(self):
        with (
            self.fail("HTTP 500 secret-token-abc leaked"),
            self.assertRaises(ValueError) as caught,
        ):
            api("user")
        self.assertNotIn("secret-token-abc", str(caught.exception))
        self.assertIn("HTTP 500", str(caught.exception))


class CliErrorHandling(unittest.TestCase):
    def run_main(self, exc):
        with (
            patch.object(sys, "argv", ["silicon-shader", "discover"]),
            patch.object(cli, "run", side_effect=exc),
            patch("sys.stderr") as err,
            self.assertRaises(SystemExit) as code,
        ):
            cli.main()
        return code.exception.code, "".join(c.args[0] for c in err.write.call_args_list)

    def test_previously_uncaught_exception_types_become_clean_errors(self):
        import zipfile

        for exc in (
            AttributeError("x"),
            zipfile.BadZipFile("bad jar"),
            RecursionError(),
            subprocess.SubprocessError("p"),
        ):
            code, text = self.run_main(exc)
            self.assertEqual(code, 2)
            self.assertIn('"ok": false', text)

    def test_key_error_is_readable(self):
        _, text = self.run_main(KeyError("html_url"))
        self.assertIn("Missing field 'html_url'", text)


class RegistryWrite(unittest.TestCase):
    def test_build_is_atomic_and_leaves_no_temp_file(self):
        import tempfile
        from silicon_shader import registry

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "data.json"
            result = registry.build(ROOT / "contributions", out)
            self.assertGreaterEqual(result["entries"], 1)
            self.assertEqual(
                sorted(p.name for p in Path(folder).iterdir()), ["data.json"]
            )
            self.assertEqual(
                len(json.loads(out.read_text())["entries"]), result["entries"]
            )


if __name__ == "__main__":
    unittest.main()


class MetricsAcrossPythonVersions(unittest.TestCase):
    """Python 3.12 compensated float sum(); 3.10 and 3.11 do not. Bundles must validate on both."""

    def entries(self):
        for path in sorted((ROOT / "contributions").glob("*.json")):
            yield path.name, json.loads(path.read_text())["bundle"]

    def test_last_digit_differences_are_tolerated(self):
        for name, bundle in self.entries():
            nudged = copy.deepcopy(bundle)
            for run in nudged["runs"].values():
                run["metrics"]["duration_s"] *= 1 + 5e-12
                run["metrics"]["average_fps"] *= 1 - 5e-12
            # The content digest covers the stored numbers, so compare the metrics check only.
            for run in nudged["runs"].values():
                self.assertTrue(
                    challenge._same_metrics(
                        challenge.analyze(run["intervals_ms"]), run["metrics"]
                    ),
                    name,
                )

    def test_a_real_change_is_still_caught(self):
        _, bundle = next(iter(self.entries()))
        run = bundle["runs"]["candidate"]
        changed = copy.deepcopy(run["metrics"])
        changed["average_fps"] *= 1.001
        self.assertFalse(
            challenge._same_metrics(challenge.analyze(run["intervals_ms"]), changed)
        )
        changed = copy.deepcopy(run["metrics"])
        changed["over_33"]["count"] += 1
        self.assertFalse(
            challenge._same_metrics(challenge.analyze(run["intervals_ms"]), changed)
        )

    def test_types_must_still_match(self):
        self.assertFalse(challenge._same_metrics({"n": 1}, {"n": True}))
        self.assertFalse(challenge._same_metrics({"n": 1}, {"n": "1"}))
        self.assertTrue(challenge._same_metrics({"n": 1.0}, {"n": 1.0000000000001}))

    def test_metrics_do_not_depend_on_summation_order(self):
        import random

        values = [random.Random(7).uniform(6, 14) for _ in range(2000)]
        shuffled = values[::-1]
        a, b = challenge.analyze(values), challenge.analyze(shuffled)
        self.assertEqual(a["duration_s"], b["duration_s"])
        self.assertEqual(a["average_fps"], b["average_fps"])


class MetadataTemplate(unittest.TestCase):
    def setUp(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.paths = (fixture.root / "baseline.json", fixture.root / "candidate.json")

    def template(self, hardware=None):
        return challenge.metadata_template(*self.paths, hardware)

    def test_observed_values_and_interventions_are_filled_in(self):
        result = self.template(
            {
                "family": "M4",
                "tier": "base",
                "cpu_cores": 10,
                "gpu_cores": 10,
                "memory_gib": 24.0,
            }
        )
        meta = result["metadata"]
        self.assertEqual(
            meta["hardware"],
            {
                "family": "M4",
                "tier": "base",
                "cpu_cores": 10,
                "gpu_cores": 10,
                "memory_gib": 24,
            },
        )
        self.assertEqual(meta["candidate"]["settings"]["scale"], 0.75)
        self.assertEqual(meta["baseline"]["settings"]["scale"], 1.0)
        self.assertEqual(result["interventions_detected"], ["scale"])
        self.assertEqual(meta["interventions"], ["scale"])

    def test_unfilled_template_never_validates(self):
        hardware = {
            "family": "M4",
            "tier": "base",
            "cpu_cores": 10,
            "gpu_cores": 10,
            "memory_gib": 24,
        }
        meta = self.template(hardware)["metadata"]
        with self.assertRaisesRegex(ValueError, "Replace the <fill in> placeholder"):
            challenge._metadata(meta)

    def test_quality_review_must_be_set_by_a_person(self):
        meta = json.loads((ROOT / "examples/challenge-metadata.json").read_text())
        template = self.template(
            {
                "family": "M4",
                "tier": "base",
                "cpu_cores": 10,
                "gpu_cores": 10,
                "memory_gib": 24,
            }
        )["metadata"]
        # Fill every placeholder from a known-good example but keep the template's review.
        for key in ("minecraft", "loader", "launcher", "harness"):
            template[key] = meta[key]
        template["runtime"] = meta["runtime"]
        for name in ("baseline", "candidate"):
            template[name]["mods"] = meta[name]["mods"]
            template[name]["shader"] = meta[name]["shader"]
            template[name]["settings"]["visual_properties"] = meta[name]["settings"][
                "visual_properties"
            ]
        template["workload"] = meta["workload"]
        with self.assertRaisesRegex(ValueError, "visual quality review"):
            challenge._metadata(template)
        template["quality_review"] = meta["quality_review"]
        template["baseline"]["settings"]["resolution"] = meta["baseline"]["settings"][
            "resolution"
        ]
        template["candidate"]["settings"]["resolution"] = meta["candidate"]["settings"][
            "resolution"
        ]
        challenge._metadata(template)

    def test_cli_writes_a_new_file_only(self):
        import io
        from contextlib import redirect_stdout

        out = self.fixture.root / "draft.json"
        argv = [
            "silicon-shader",
            "challenge",
            "metadata-template",
            str(self.paths[0]),
            str(self.paths[1]),
            "--out",
            str(out),
        ]
        with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            cli.main()
        self.assertEqual(json.loads(out.read_text())["interventions"], ["scale"])
        with (
            patch.object(sys, "argv", argv),
            patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            cli.main()
