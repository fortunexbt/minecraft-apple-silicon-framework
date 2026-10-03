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


def api(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], timeout=30))


repo = os.environ["GH_REPO"]
number = os.environ["PR_NUMBER"]
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not number.isdigit():
    raise SystemExit("Invalid event identity")
pr = api(f"repos/{repo}/pulls/{number}")
files = api(f"repos/{repo}/pulls/{number}/files?per_page=100")
if pr["changed_files"] > 100:
    raise SystemExit(
        "Large PR needs separate review; evidence gate cannot inspect all files"
    )
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
if "presentation" not in entry or not entry["presentation"].get("minecraft_profile"):
    raise SystemExit(
        "Include setup title, Minecraft profile, gameplay screenshot and a pinned Markdown recipe in presentation"
    )
if entry["author"].lower() != pr["user"]["login"].lower():
    raise SystemExit("Public author must match the submitting GitHub account")
if f["status"] == "modified":
    previous = api(f"repos/{repo}/contents/{f['filename']}?ref={pr['base']['sha']}")
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
print("Consistent self-reported evidence. Human recipe/visual review still required.")
