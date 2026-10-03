"""Build a public data index from reviewed, bounded, data-only contributions."""

import json
from pathlib import Path
import re

from .challenge import MAX_BYTES, validate_bundle
from .community import contract


def validate_entry(entry, filename):
    if not isinstance(entry, dict) or set(entry) != {"author", "bundle"}:
        raise ValueError("Contribution needs exactly author and bundle")
    if not isinstance(entry["author"], str) or not re.fullmatch(
        r"[A-Za-z0-9-]{1,39}", entry["author"]
    ):
        raise ValueError("Invalid public GitHub handle")
    errors = validate_bundle(entry["bundle"])
    if errors:
        raise ValueError("; ".join(errors))
    if filename != entry["bundle"]["content_digest"] + ".json":
        raise ValueError("Contribution filename does not match content digest")
    return entry


def build(source, destination):
    root = Path(source)
    entries = []
    files = sorted(root.glob("*.json"))
    if len(files) > 500:
        raise ValueError(
            "Registry exceeds initial 500-entry bound; paginate before expanding"
        )
    for path in files:
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise ValueError("Invalid contribution file")
        entry = validate_entry(json.loads(path.read_text()), path.name)
        # Relative traces remain in the linked file; keep the index small.
        bundle = entry["bundle"]
        entries.append(
            {
                "author": entry["author"],
                "digest": bundle["content_digest"],
                "cohort": bundle["cohort_hash"],
                "status": bundle["status"],
                "metadata": bundle["metadata"],
                "runs": {k: v["metrics"] for k, v in bundle["runs"].items()},
                "evidence": "https://github.com/"
                + contract()["repository"]
                + "/blob/main/contributions/"
                + path.name,
            }
        )
    Path(destination).write_text(
        json.dumps({"contract": contract(), "entries": entries}, indent=2) + "\n"
    )
    return {"entries": len(entries), "output": str(destination)}


if __name__ == "__main__":
    import sys

    print(json.dumps(build(sys.argv[1], sys.argv[2])))
