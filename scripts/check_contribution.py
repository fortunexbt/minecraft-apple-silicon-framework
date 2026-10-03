"""PR-target gate: read JSON blobs; never check out or execute the PR head."""

import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from silicon_shader.challenge import MAX_BYTES
from silicon_shader.registry import validate_entry
from silicon_shader.presentation import validate_presentation
from silicon_shader.workload import require_standard


def api(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], timeout=30))


repo = os.environ["GH_REPO"]
number = os.environ["PR_NUMBER"]
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not number.isdigit():
    raise SystemExit("Invalid event identity")
pr = api(f"repos/{repo}/pulls/{number}")
base_sha = pr.get("base", {}).get("sha", "")
head_sha = pr.get("head", {}).get("sha", "")
if not re.fullmatch(r"[a-f0-9]{40,64}", base_sha) or not re.fullmatch(
    r"[a-f0-9]{40,64}", head_sha
):
    raise SystemExit("Invalid pull request base or head SHA")
changed_files = pr.get("changed_files")
if type(changed_files) is not int or changed_files < 0:
    raise SystemExit("Invalid pull request changed-file count")
if changed_files > 100:
    raise SystemExit(
        "Large PR needs separate review; evidence gate cannot inspect all files"
    )
comparison = api(f"repos/{repo}/compare/{base_sha}...{head_sha}")
if comparison.get("base_commit", {}).get("sha") != base_sha:
    raise SystemExit("Pinned comparison returned a different base")
files = comparison.get("files")
if not isinstance(files, list) or len(files) != changed_files:
    raise SystemExit("Pinned comparison is incomplete; file count does not match PR")
submissions = [
    f
    for f in files
    if f["filename"].startswith("contributions/") and f["filename"].endswith(".json")
]
if not submissions:
    print("No evidence submissions")
    raise SystemExit(0)
if len(files) != 1 or len(submissions) != 1:
    raise SystemExit(
        "Submit exactly one evidence JSON; put code changes in a separate PR"
    )
f = submissions[0]
auto_merge_eligible = False
if f["status"] not in ("added", "modified") or not re.fullmatch(
    r"contributions/[a-f0-9]{64}\.json", f["filename"]
):
    raise SystemExit("Evidence must be one digest-named JSON file")
if not re.fullmatch(r"[a-f0-9]{40,64}", f["sha"]):
    raise SystemExit("Invalid blob SHA")
blob = api(f"repos/{repo}/git/blobs/{f['sha']}")
if blob["size"] > MAX_BYTES or blob.get("encoding") != "base64":
    raise SystemExit("Evidence exceeds size limit or has unsupported encoding")
entry = validate_entry(
    json.loads(base64.b64decode(blob["content"])), Path(f["filename"]).name
)
validate_presentation(
    entry.get("presentation"),
    for_submission=True,
    require_showcase=entry["bundle"]["schema_version"] == 2,
)
if entry["author"].lower() != pr["user"]["login"].lower():
    raise SystemExit("Public author must match the submitting GitHub account")
if f["status"] == "modified":
    previous = api(f"repos/{repo}/contents/{f['filename']}?ref={pr['base']['sha']}")
    if previous.get("encoding") == "none" and re.fullmatch(
        r"[a-f0-9]{40,64}", previous.get("sha", "")
    ):
        previous = api(f"repos/{repo}/git/blobs/{previous['sha']}")
    if (
        previous.get("size", MAX_BYTES + 1) > MAX_BYTES
        or previous.get("encoding") != "base64"
    ):
        raise SystemExit("Invalid previous submission")
    old = validate_entry(
        json.loads(base64.b64decode(previous["content"])), Path(f["filename"]).name
    )
    if old["author"] != entry["author"] or old["bundle"] != entry["bundle"]:
        raise SystemExit(
            "Existing submissions may update presentation only; preserve author and evidence"
        )
    # Old v1 entries may receive presentation-only fixes, but they remain
    # historical. Any changed or newly added evidence must meet the current
    # standard workload contract.
    if old["bundle"].get("schema_version") == 2:
        require_standard(entry["bundle"])
        auto_merge_eligible = True
else:
    require_standard(entry["bundle"])
    auto_merge_eligible = True

auto_merge_eligible = auto_merge_eligible and (
    pr.get("base", {}).get("ref") == "main"
    and pr.get("base", {}).get("repo", {}).get("full_name") == repo
)

# Only a successfully validated, data-only contribution emits merge eligibility.
# The SHA is constrained above and is checked again by GitHub's merge endpoint.
output_path = os.environ.get("GITHUB_OUTPUT")
if auto_merge_eligible and output_path:
    with open(output_path, "a", encoding="utf-8") as output:
        output.write("eligible=true\n")
        output.write(f"base_sha={base_sha}\n")
        output.write(f"head_sha={head_sha}\n")
if auto_merge_eligible:
    print("Validated data-only contribution; exact head is eligible for automatic merge.")
elif entry["bundle"].get("schema_version") == 2:
    print("Validated contribution, but automatic merge only targets this repository's main branch.")
else:
    print("Historical presentation update validated; it is not eligible for automatic merge.")
