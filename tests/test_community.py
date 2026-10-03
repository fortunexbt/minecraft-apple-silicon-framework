import base64
import json
import unittest
from unittest.mock import Mock

import test_challenge
from silicon_shader.community import submit, REPOSITORY
from silicon_shader.registry import build, validate_entry


class CommunityTests(unittest.TestCase):
    def setUp(self):
        fixture = test_challenge.ChallengeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.bundle = fixture.prepare()
        self.root = fixture.root

    def test_preview_and_wrong_digest_never_contact_github(self):
        request = Mock(side_effect=AssertionError("No network"))
        self.assertEqual(submit(self.bundle, request=request)["bundle"], self.bundle)
        with self.assertRaises(ValueError):
            submit(self.bundle, True, "wrong", request)
        request.assert_not_called()

    def test_existing_pr_does_not_publish_again(self):
        request = Mock(
            side_effect=[
                {"login": "tester"},
                [{"html_url": "https://github.com/example/pull/1", "state": "open"}],
            ]
        )
        result = submit(self.bundle, True, self.bundle["content_digest"], request)
        self.assertTrue(result["resumed"])
        self.assertEqual(request.call_count, 2)

    def test_publish_owner_and_resume_after_file_write(self):
        digest = self.bundle["content_digest"]
        path = "contributions/" + digest + ".json"
        branch = "challenge/" + digest
        entry = {"author": "fortunexbt", "bundle": self.bundle}
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

            result = submit(self.bundle, True, digest, request)
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
            submit(self.bundle, True, self.bundle["content_digest"], request)

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
        responses = {
            "repos/owner/repo/pulls/1": {
                "changed_files": 1,
                "user": {"login": "tester"},
            },
            "repos/owner/repo/pulls/1/files?per_page=100": [
                {"filename": path, "status": "added", "sha": "a" * 40}
            ],
            "repos/owner/repo/git/blobs/" + "a" * 40: {
                "size": 1000,
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps({"author": "tester", "bundle": self.bundle}).encode()
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
        }
        script = Path(test_challenge.ROOT) / "scripts/check_contribution.py"

        def check():
            fixture.write_text(json.dumps(responses))
            return subprocess.run(
                [sys.executable, str(script)], env=env, capture_output=True, text=True
            )

        self.assertEqual(check().returncode, 0)
        responses["repos/owner/repo/pulls/1"]["user"]["login"] = "someone-else"
        self.assertNotEqual(check().returncode, 0)
        responses["repos/owner/repo/pulls/1"]["user"]["login"] = "tester"
        responses["repos/owner/repo/pulls/1/files?per_page=100"].append(
            {"filename": "silicon_shader/measure.py"}
        )
        self.assertNotEqual(check().returncode, 0)
