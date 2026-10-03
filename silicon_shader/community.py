"""Optional data-only GitHub submission. No credentials, game or submitted code execution."""

import base64
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode

from .challenge import MAX_BYTES, validate_bundle
from .presentation import validate_presentation

REPOSITORY = "fortunexbt/minecraft-apple-silicon-framework"


def contract():
    from . import workload

    return {
        "id": "silicon-shader-ab-v2",
        "schema_version": 2,
        "metric": "cpu_frame_production",
        "workload_id": workload.WORKLOAD_ID,
        "standard_workload": workload.contract(),
        "workload_guide": "https://github.com/"
        + REPOSITORY
        + "/blob/main/docs/WORKLOAD.md",
        "repository": REPOSITORY,
        "leaderboard": "https://fortunexbt.github.io/minecraft-apple-silicon-framework/",
        "submission": "Optional data-only pull request; maintainer review before publication on the board",
        "eligibility": "New evidence uses the pinned standard route with matching baseline and candidate receipts, same-machine captures, and a visual review",
        "comparison": "Compare route-matched captures; browse screenshots and setups by hardware, resolution, shader and view distance",
        "verification": "Trace consistency is self-reported evidence, not independent reproduction",
        "legacy_evidence": "Schema v1 entries remain visible as earlier-route historical evidence; new submissions require v2",
        "rules": "https://github.com/" + REPOSITORY + "/blob/main/docs/CHALLENGE.md",
        "editable_submission_paths": ["contributions/<content_digest>.json"],
        "executes_contributor_code": False,
        "telemetry": False,
    }


def load_bundle(path):
    p = Path(path)
    if p.is_symlink() or p.stat().st_size > MAX_BYTES:
        raise ValueError("Bundle must be a regular JSON file under 8 MB")
    bundle = json.loads(p.read_text())
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError("; ".join(errors))
    return bundle


def api(endpoint, method="GET", payload=None):
    command = ["gh", "api", "--hostname", "github.com", "--method", method, endpoint]
    data = None
    if payload is not None:
        command += ["--input", "-"]
        data = json.dumps(payload, allow_nan=False)
    try:
        result = subprocess.run(
            command, input=data, text=True, capture_output=True, timeout=45
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(
            "GitHub request unavailable or outcome unknown; inspect status before retrying the same digest"
        ) from exc
    if result.returncode:
        # Do not reflect remote text or authentication details into public output.
        raise ValueError(
            "GitHub request failed; run gh auth status --hostname github.com, check permissions, then inspect challenge status before retrying"
        )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Expected full SHA-256 content digest")
    return value


def _identity(request):
    login = request("user")["login"]
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise ValueError("Unexpected GitHub account identifier")
    return login


def _pulls(request, login, digest):
    query = urlencode(
        {"state": "all", "head": login + ":challenge/" + digest, "per_page": 100}
    )
    return request(f"repos/{REPOSITORY}/pulls?{query}")


def status(digest, request=api):
    digest = _digest(digest)
    login = _identity(request)
    pulls = _pulls(request, login, digest)
    return {
        "digest": digest,
        "account": login,
        "pull_requests": [
            {
                "url": p["html_url"],
                "state": p["state"],
                "merged": bool(p.get("merged_at")),
            }
            for p in pulls
        ],
        "note": "No PR can mean an unpublished or interrupted submission; retry the same bundle to resume",
    }


def submit(bundle, publish=False, reviewed_digest=None, request=api, presentation=None):
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError("; ".join(errors))
    if publish:
        from .workload import require_standard

        # Enforce before any GitHub identity lookup, fork, branch, or PR request.
        require_standard(bundle)
    digest = _digest(bundle["content_digest"])
    if publish or presentation is not None:
        validate_presentation(
            presentation, for_submission=publish, require_showcase=publish
        )
    preview = {
        "digest": digest,
        "workload_id": bundle.get("workload_id"),
        "destination": "https://github.com/" + REPOSITORY,
        "path": f"contributions/{digest}.json",
        "metadata": bundle["metadata"],
        "timings": {
            name: {
                key: run["metrics"][key]
                for key in (
                    "average_fps",
                    "worst_5s_fps",
                    "p95_ms",
                    "p99_ms",
                    "over_33",
                    "over_50",
                    "over_100",
                )
            }
            for name, run in bundle["runs"].items()
        },
        "relative_intervals": {
            name: len(run["intervals_ms"]) for name, run in bundle["runs"].items()
        },
        "review": "The full relative traces remain in your bundle file and will also be published.",
        "publication": "Public evidence and authenticated GitHub handle; may create a fork, branch and pull request",
        "benchmark": "Standard route"
        if bundle.get("schema_version") == 2
        else "Earlier route",
    }
    if presentation is not None:
        preview["presentation"] = presentation
    if not publish:
        return preview
    if reviewed_digest is not None and reviewed_digest != digest:
        raise ValueError("Bundle changed: --reviewed-digest does not match this file")
    login = _identity(request)
    existing = _pulls(request, login, digest)
    if existing:
        p = existing[0]
        return {
            "digest": digest,
            "url": p["html_url"],
            "state": p["state"],
            "resumed": True,
        }
    upstream = request("repos/" + REPOSITORY)
    owner = REPOSITORY.split("/")[0]
    target = REPOSITORY
    if login != owner:
        # GitHub returns an existing fork or initiates its creation. A pending fork
        # may need a later retry; no sleeps, repeated posts or credential creation.
        fork = request(f"repos/{REPOSITORY}/forks", "POST", {})
        target = fork["full_name"]
        if target.split("/")[0] != login:
            raise ValueError("Fork does not belong to the authenticated account")
        info = request("repos/" + target)
        if info.get("parent", {}).get("full_name") != REPOSITORY:
            raise ValueError("Destination is not a fork of this challenge")
    branch = "challenge/" + digest
    refs = request(f"repos/{target}/git/matching-refs/heads/{branch}")
    exact = [r for r in refs if r["ref"] == "refs/heads/" + branch]
    if not exact:
        base = request(
            f"repos/{REPOSITORY}/git/ref/heads/{upstream['default_branch']}"
        )["object"]["sha"]
        request(
            f"repos/{target}/git/refs",
            "POST",
            {"ref": "refs/heads/" + branch, "sha": base},
        )
    # Inspect tree rather than treating an arbitrary contents API failure as absent.
    ref = request(f"repos/{target}/git/ref/heads/{branch}")["object"]["sha"]
    tree = request(f"repos/{target}/git/trees/{ref}?recursive=1")
    if tree.get("truncated"):
        raise ValueError("Cannot safely inspect a truncated destination tree")
    path = preview["path"]
    entry = {"author": login, "bundle": bundle}
    if presentation is not None:
        entry["presentation"] = presentation
    existing_file = next((x for x in tree["tree"] if x["path"] == path), None)
    if existing_file:
        blob = request(f"repos/{target}/git/blobs/{existing_file['sha']}")
        if json.loads(base64.b64decode(blob["content"])) != entry:
            raise ValueError("Existing submission differs; refusing to overwrite it")
    else:
        content = base64.b64encode(
            (json.dumps(entry, indent=2, allow_nan=False) + "\n").encode()
        ).decode()
        request(
            f"repos/{target}/contents/{path}",
            "PUT",
            {
                "message": "Submit matched shader experiment " + digest[:12],
                "branch": branch,
                "content": content,
            },
        )
    comparison = request(
        f"repos/{REPOSITORY}/compare/{upstream['default_branch']}...{login}:{branch}"
    )
    changed = comparison.get("files", [])
    if (
        comparison.get("total_commits") != 1
        or len(changed) != 1
        or changed[0].get("filename") != path
        or changed[0].get("status") != "added"
    ):
        raise ValueError(
            "Submission branch contains unexpected changes; refusing to publish"
        )
    pr = request(
        f"repos/{REPOSITORY}/pulls",
        "POST",
        {
            "title": "Challenge evidence " + digest[:12],
            "head": login + ":" + branch,
            "base": upstream["default_branch"],
            "body": "Optional, self-reported same-machine A/B evidence.\n\n"
            "Content digest: `" + digest + "`\n\n"
            "Review the declared interventions, public recipe, visual verdict and recomputed timing metrics. "
            "Passing data validation does not establish independent reproduction. "
            "This submission contains data only and must not execute contributor code.",
        },
    )
    return {
        "digest": digest,
        "url": pr["html_url"],
        "state": pr["state"],
        "resumed": False,
    }
