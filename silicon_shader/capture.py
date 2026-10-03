"""File protocol for the optional sampler; never launches or kills Minecraft."""

import os
from pathlib import Path
import tempfile
import time
from .common import identifier, read, digest
from .measure import analyze, read_csv, validate


def _request(root, run_id, seconds=20):
    identifier(run_id)
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Create a dedicated sampler control directory first")
    if not 20 <= seconds <= 30:
        raise ValueError("Use 20–30 second gameplay captures")
    if any(root.glob(run_id + "-*")):
        raise ValueError("Capture ID already exists; never reuse IDs")
    current = root / "measure.properties"
    if current.exists():
        from .common import properties

        old = properties(current).get("id", "")
        identifier(old)
        status = root / (old + "-status.json")
        if not status.exists() or read(status).get("state") not in ("done", "error"):
            raise ValueError(
                "Previous request has no terminal status; timeout does not mean stopped"
            )
    fd, tmp = tempfile.mkstemp(dir=root, prefix=".request-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"id={run_id}\nseconds={seconds}\n")
        os.replace(tmp, current)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {
        "id": run_id,
        "state": "starting",
        "note": "Request written; poll for sampler acknowledgement",
    }


def request(root, run_id, seconds=20):
    root = Path(root)
    if not root.is_dir():
        raise ValueError("Create a dedicated sampler control directory first")
    lock = root / ".request.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Another request is being written; inspect its state first")
    try:
        os.close(fd)
        return _request(root, run_id, seconds)
    finally:
        lock.unlink()


def status(root, run_id, wait=0):
    identifier(run_id)
    if not 0 <= wait <= 40:
        raise ValueError("Wait must be 0–40 seconds")
    path = Path(root) / (run_id + "-status.json")
    deadline = time.monotonic() + wait
    while True:
        result = (
            read(path)
            if path.exists()
            else {"id": run_id, "state": "starting", "acknowledged": False}
        )
        if result.get("id") != run_id:
            raise ValueError("Status ID mismatch")
        if result.get("state") in ("done", "error") or time.monotonic() >= deadline:
            return result
        time.sleep(0.2)


def import_capture(root, run_id, manifest, profile="baseline"):
    identifier(run_id)
    root = Path(root)
    receipt = status(root, run_id)
    if receipt.get("state") != "done":
        raise ValueError("Sampler has not completed; do not import partial output")
    frames = root / (run_id + "-frames.csv")
    intervals, count = read_csv(frames)
    if receipt.get("frames") != count:
        raise ValueError("CSV and completion frame counts differ")
    if receipt.get("metric") != "cpu_frame_production":
        raise ValueError("Unknown sampler metric")
    result = {
        "id": run_id,
        "profile": profile,
        "status": "done",
        "metric": "cpu_frame_production",
        "expected": manifest["expected"],
        "observed": manifest["observed"],
        "visual": manifest["visual"],
        "completion": {
            "unfocused_frames": receipt.get("unfocused_frames"),
            "buffer_full": receipt.get("buffer_full"),
            "error": receipt.get("error"),
        },
        "metrics": analyze(intervals),
        "provenance": {
            "csv_sha256": digest(frames),
            "status_sha256": digest(root / (run_id + "-status.json")),
            "hook": receipt.get("hook"),
        },
    }
    problems = validate(result)
    if problems:
        raise ValueError("; ".join(problems))
    return result
