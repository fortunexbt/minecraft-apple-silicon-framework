"""Small local storage primitives; no network or process execution from documents."""

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError(
            "ID must be 1–100 ASCII letters, digits, underscores or hyphens"
        )
    return value


def contained(root, relative):
    root = Path(root).resolve()
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Expected a relative path without parent traversal")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escapes instance")
    return path


def no_links(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Symlink refused: {path.name}")
    if path.is_dir():
        for p in path.rglob("*"):
            if p.is_symlink():
                raise ValueError(f"Symlink refused: {p.name}")


def properties(path, separator="="):
    result = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if separator in line and not line.lstrip().startswith(("#", "!", "[")):
                k, v = line.split(separator, 1)
                result[k.strip()] = v.strip()
    return result


def update_properties(path, values, separator="="):
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    remaining = dict(values)
    out = []
    for line in lines:
        key = line.split(separator, 1)[0].strip()
        if key in values and separator in line:
            if key in remaining:
                out.append(key + separator + str(remaining.pop(key)))
        else:
            out.append(line)
    out.extend(k + separator + str(v) for k, v in remaining.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")
