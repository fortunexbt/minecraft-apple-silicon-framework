import base64
import json
import unittest
from unittest.mock import Mock

import test_challenge
from silicon_shader.community import submit, REPOSITORY
from silicon_shader.registry import build, validate_entry
from standard_fixture import standard_bundle


class CommunityTests(unittest.TestCase):
    def setUp(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.bundle = standard_bundle(fixture.prepare())
        self.root = fixture.root
        self.presentation = {
            "title": "Example setup",
            "minecraft_profile": "ExamplePlayer",
            "screenshot_view": "overworld-front-v1",
            "agent": {"model": "Example Model 1", "harness": "Example Agent"},
            "screenshot_url": "https://raw.githubusercontent.com/tester/recipe/"
            + "a" * 40
            + "/shot.png",
            "recipe_url": "https://github.com/tester/recipe/blob/"
            + "a" * 40
            + "/setup.md",
        }

    def test_preview_and_wrong_digest_never_contact_github(self):
        request = Mock(side_effect=AssertionError("No network"))
        preview = submit(self.bundle, request=request)
        self.assertEqual(preview["metadata"], self.bundle["metadata"])
        self.assertNotIn("intervals_ms", json.dumps(preview))
        with self.assertRaises(ValueError):
            submit(self.bundle, True, "wrong", request)
        with self.assertRaisesRegex(ValueError, "minecraft_profile"):
            submit(
                self.bundle,
                True,
                request=request,
                presentation={
                    k: v
                    for k, v in self.presentation.items()
                    if k != "minecraft_profile"
                },
            )
        with self.assertRaisesRegex(ValueError, "agent.model"):
            submit(
                self.bundle,
                True,
                request=request,
                presentation={
                    k: v for k, v in self.presentation.items() if k != "agent"
                },
            )
        request.assert_not_called()

    def test_standard_showcase_required_before_publication(self):
        from silicon_shader.presentation import validate_presentation

        legacy = {k: v for k, v in self.presentation.items() if k != "screenshot_view"}
        self.assertEqual(validate_presentation(legacy), legacy)
        request = Mock(side_effect=AssertionError("No network"))
        for shot in (legacy, {**legacy, "screenshot_view": "another-spot"}):
            with self.assertRaisesRegex(ValueError, "standard front-facing"):
                submit(self.bundle, True, request=request, presentation=shot)
        request.assert_not_called()

    def test_agent_labels_preserve_legacy_and_reject_invalid_attribution(self):
        from silicon_shader.presentation import validate_presentation

        legacy = {k: v for k, v in self.presentation.items() if k != "agent"}
        validate_presentation(legacy)
        for agent in (
            {"model": ""},
            {"model": "\nsecret", "harness": "Codex"},
            {"model": "https://example.com", "harness": "Codex"},
            {"model": "x" * 81, "harness": "Codex"},
        ):
            with self.assertRaises(ValueError):
                validate_presentation({**self.presentation, "agent": agent})
        manual = {**self.presentation, "agent": {"model": "None", "harness": "Manual"}}
        self.assertEqual(validate_presentation(manual, for_submission=True), manual)

    def test_existing_pr_does_not_publish_again(self):
        request = Mock(
            side_effect=[
                {"login": "tester"},
                [{"html_url": "https://github.com/example/pull/1", "state": "open"}],
            ]
        )
        result = submit(
            self.bundle,
            True,
            self.bundle["content_digest"],
            request,
            presentation=self.presentation,
        )
        self.assertTrue(result["resumed"])
        self.assertEqual(request.call_count, 2)

    def test_publish_owner_and_resume_after_file_write(self):
        digest = self.bundle["content_digest"]
        path = "contributions/" + digest + ".json"
        branch = "challenge/" + digest
        entry = {
            "author": "fortunexbt",
            "bundle": self.bundle,
            "presentation": self.presentation,
        }
        for resumed in [False, True]:
            calls = []

            def request(endpoint, method="GET", payload=None):
                calls.append((endpoint, method, payload))
                if endpoint == "user":
                    return {"login": "fortunexbt"}
                if "/pulls?" in endpoint:
                    return []
                if endpoint == "repos/" + REPOSITORY:
                    return {"default_branch": "main"}
                if "/matching-refs/" in endpoint:
                    return [{"ref": "refs/heads/" + branch}] if resumed else []
                if "/git/ref/" in endpoint:
                    return {"object": {"sha": "a" * 40}}
                if endpoint.endswith("/git/refs"):
                    return {}
                if "/git/trees/" in endpoint:
                    return {
                        "tree": [{"path": path, "sha": "b" * 40}] if resumed else []
                    }
                if "/git/blobs/" in endpoint:
                    return {
                        "content": base64.b64encode(json.dumps(entry).encode()).decode()
                    }
                if "/contents/" in endpoint:
                    self.assertEqual(
                        json.loads(base64.b64decode(payload["content"])), entry
                    )
                    return {}
                if "/compare/" in endpoint:
                    return {
                        "total_commits": 1,
                        "files": [{"filename": path, "status": "added"}],
                    }
                if endpoint.endswith("/pulls"):
                    return {
                        "html_url": "https://github.com/test/pull/1",
                        "state": "open",
                    }
                raise AssertionError(endpoint)

            result = submit(
                self.bundle, True, request=request, presentation=self.presentation
            )
            self.assertEqual(result["state"], "open")
            writes = [c for c in calls if "/contents/" in c[0]]
            self.assertEqual(len(writes), 0 if resumed else 1)

    def test_registry_rejects_tampering_and_omits_raw_trace_in_index(self):
        digest = self.bundle["content_digest"]
        entry = {"author": "tester", "bundle": self.bundle}
        (self.root / (digest + ".json")).write_text(json.dumps(entry))
        # Only the registry directory, not the preparation fixtures.
        source = self.root / "entries"
        source.mkdir()
        (source / (digest + ".json")).write_text(json.dumps(entry))
        target = self.root / "data.json"
        self.assertEqual(build(source, target)["entries"], 1)
        self.assertNotIn("intervals_ms", target.read_text())
        entry["bundle"]["status"] = "verified"
        with self.assertRaises(ValueError):
            validate_entry(entry, digest + ".json")

    def test_fork_destination_identity_is_checked(self):
        request = Mock(
            side_effect=[
                {"login": "tester"},
                [],
                {"default_branch": "main"},
                {"full_name": "tester/challenge"},
                {"parent": {"full_name": "unrelated/repo"}},
            ]
        )
        with self.assertRaisesRegex(ValueError, "not a fork"):
            submit(
                self.bundle,
                True,
                self.bundle["content_digest"],
                request,
                presentation=self.presentation,
            )

    def test_skill_install_is_explicit_and_preserves_existing(self):
        from silicon_shader.cli import parser, run

        target = self.root.resolve() / "skill"
        args = parser().parse_args(["install-skill", "--destination", str(target)])
        self.assertEqual(run(args)["status"], "installed")
        self.assertEqual(run(args)["status"], "already installed")
        (target / "SKILL.md").write_text("custom instructions")
        with self.assertRaises(ValueError):
            run(args)
        self.assertEqual((target / "SKILL.md").read_text(), "custom instructions")

    def test_pr_gate_accepts_only_data_from_the_actual_author(self):
        import os
        import subprocess
        import sys
        from pathlib import Path
        import test_challenge

        digest = self.bundle["content_digest"]
        path = "contributions/" + digest + ".json"
        base_sha = "b" * 40
        head_sha = "d" * 40
        compare_key = f"repos/owner/repo/compare/{base_sha}...{head_sha}"
        responses = {
            "repos/owner/repo/pulls/1": {
                "changed_files": 1,
                "user": {"login": "tester"},
                "base": {"sha": base_sha},
                "head": {"sha": head_sha},
            },
            compare_key: {
                "base_commit": {"sha": base_sha},
                "files": [{"filename": path, "status": "added", "sha": "a" * 40}],
            },
            "repos/owner/repo/git/blobs/" + "a" * 40: {
                "size": 1000,
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps(
                        {
                            "author": "tester",
                            "bundle": self.bundle,
                            "presentation": {
                                "title": "Example setup",
                                "minecraft_profile": "ExamplePlayer",
                                "screenshot_view": "overworld-front-v1",
                                "agent": {
                                    "model": "Example Model 1",
                                    "harness": "Example Agent",
                                },
                                "screenshot_url": "https://raw.githubusercontent.com/tester/recipe/"
                                + "a" * 40
                                + "/shot.png",
                                "recipe_url": "https://github.com/tester/recipe/blob/"
                                + "a" * 40
                                + "/setup.md",
                            },
                        }
                    ).encode()
                ).decode(),
            },
        }
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(
            "#!"
            + sys.executable
            + '\nimport json, os, sys\nprint(json.dumps(json.load(open(os.environ["FIXTURE_RESPONSES"]))[sys.argv[2]]))\n'
        )
        gh.chmod(0o700)
        fixture = self.root / "responses.json"
        env = {
            **os.environ,
            "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
            "GH_REPO": "owner/repo",
            "PR_NUMBER": "1",
            "FIXTURE_RESPONSES": str(fixture),
            "GITHUB_OUTPUT": str(self.root / "gate-output"),
        }
        script = Path(test_challenge.ROOT) / "scripts/check_contribution.py"
        output_file = Path(env["GITHUB_OUTPUT"])

        def check():
            fixture.write_text(json.dumps(responses))
            output_file.write_text("")
            return subprocess.run(
                [sys.executable, str(script)], env=env, capture_output=True, text=True
            )

        self.assertEqual(check().returncode, 0)
        self.assertEqual(
            output_file.read_text(), f"eligible=true\nhead_sha={head_sha}\n"
        )
        responses[compare_key]["files"][0]["status"] = "modified"
        previous_key = "repos/owner/repo/contents/" + path + "?ref=" + base_sha
        responses[previous_key] = dict(
            responses["repos/owner/repo/git/blobs/" + "a" * 40]
        )
        self.assertEqual(check().returncode, 0)
        original_previous = responses[previous_key]
        responses[previous_key] = {
            "encoding": "none",
            "size": 1_100_000,
            "sha": "c" * 40,
        }
        responses["repos/owner/repo/git/blobs/" + "c" * 40] = original_previous
        self.assertEqual(check().returncode, 0)
        responses[previous_key] = original_previous
        previous = json.loads(base64.b64decode(responses[previous_key]["content"]))
        previous["author"] = "someone-else"
        responses[previous_key]["content"] = base64.b64encode(
            json.dumps(previous).encode()
        ).decode()
        self.assertNotEqual(check().returncode, 0)
        responses[compare_key]["files"][0]["status"] = "added"
        responses["repos/owner/repo/pulls/1"]["user"]["login"] = "someone-else"
        self.assertNotEqual(check().returncode, 0)
        responses["repos/owner/repo/pulls/1"]["user"]["login"] = "tester"
        responses[compare_key]["files"].append(
            {"filename": "silicon_shader/measure.py"}
        )
        responses["repos/owner/repo/pulls/1"]["changed_files"] = 2
        self.assertNotEqual(check().returncode, 0)
        responses[compare_key]["files"] = []
        self.assertNotEqual(check().returncode, 0)
        self.assertEqual(output_file.read_text(), "")

        responses[compare_key]["files"] = [{"filename": "README.md"}]
        responses["repos/owner/repo/pulls/1"]["changed_files"] = 1
        self.assertEqual(check().returncode, 0)
        self.assertEqual(output_file.read_text(), "")
