#!/usr/bin/env python3
"""Apply the campaign's one-line MakeUp 9.5f exposure-history guard to a local ZIP copy."""
# SPDX-License-Identifier: LGPL-3.0-only
# Based on MakeUp Ultra Fast 9.5f by KDXavier; see patches/makeup/LICENSE-LGPL-3.0.txt.
from __future__ import annotations
import hashlib
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

INPUT_SHA256 = "afbf622b983d29ffa5fe5f15197f321d3921915bd44584d85f14bc11b5e0e5e8"
REFERENCE_OUTPUT_SHA256 = "3ff5d3b3a8b47e4743f3d90e77faf6ca8d89e97f2f5989694f28bc9ad753b922"
MEMBER = "shaders/common/composite_vertex.glsl"
OLD = re.compile(rb"^(?P<indent>[ \t]*)exposure = mix\(exposure, prev_exposure, exp\(-frameTime \* 1\.25\)\);[ \t]*$", re.M)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: apply-makeup-exposure-init.py <original-9.5f.zip> <new-patched-copy.zip>", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).expanduser().resolve()
    destination = Path(sys.argv[2]).expanduser().absolute()
    if source == destination.resolve() or destination.exists() or destination.is_symlink():
        print("refusing to overwrite the source or an existing output", file=sys.stderr)
        return 2
    actual = digest(source)
    if actual != INPUT_SHA256:
        print(f"input SHA-256 {actual} is not the tested MakeUp 9.5f archive; refusing to patch", file=sys.stderr)
        return 2
    if not destination.parent.is_dir():
        print("output directory must already exist", file=sys.stderr)
        return 2
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(source, "r") as original:
            names = [entry.filename for entry in original.infolist()]
            if names.count(MEMBER) != 1:
                raise ValueError(f"expected one {MEMBER} archive member")
            source_text = original.read(MEMBER)
            matches = list(OLD.finditer(source_text))
            if len(matches) != 1:
                raise ValueError(f"expected one exposure smoothing line; found {len(matches)}")
            match = matches[0]
            indent = match.group("indent")
            replacement = (b"if (prev_exposure > 0.0) {\n" + indent + b"    exposure = mix(exposure, prev_exposure, exp(-frameTime * 1.25));\n" + indent + b"}")
            patched_text = source_text[:match.start()] + replacement + source_text[match.end():]
            with zipfile.ZipFile(temporary, "w") as output:
                for info in original.infolist():
                    data = patched_text if info.filename == MEMBER else original.read(info.filename)
                    output.writestr(info, data)
        with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(temporary, "r") as result:
            if result.testzip() is not None:
                raise ValueError("output ZIP failed CRC validation")
            before_entries = original.infolist()
            after_entries = result.infolist()
            if len(before_entries) != len(after_entries):
                raise ValueError("archive member count changed")
            for before, after in zip(before_entries, after_entries):
                if before.filename != after.filename:
                    raise ValueError("archive member order or names changed")
                after_data = result.read(after)
                expected_data = patched_text if before.filename == MEMBER else original.read(before)
                if after_data != expected_data:
                    raise ValueError(f"unexpected content change in {before.filename}")
            if result.read(MEMBER).count(b"if (prev_exposure > 0.0)") != 1:
                raise ValueError("patched exposure guard did not validate")
        # A hard link publishes the finished file atomically and fails if a
        # destination appeared after the initial existence check.
        os.link(temporary, destination)
        temporary.unlink()
    except Exception as error:
        temporary.unlink(missing_ok=True)
        print(f"patch failed: {error}", file=sys.stderr)
        return 1
    output_hash = digest(destination)
    print(f"Wrote separate patched copy: {destination}")
    print(f"Output SHA-256: {output_hash}")
    print(f"Campaign reference ZIP SHA-256: {REFERENCE_OUTPUT_SHA256}")
    print(f"Reference archive match: {output_hash == REFERENCE_OUTPUT_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
