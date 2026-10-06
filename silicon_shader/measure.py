"""CPU frame-production analysis. This never estimates GPU/displayed/generated FPS."""

import csv
import math
from pathlib import Path
import statistics
from .common import identifier

CONTEXT = (
    "game_state",
    "player_alive",
    "game_mode",
    "instance",
    "save",
    "dimension",
    "scene",
    "route",
    "terrain",
    "hardware",
    "runtime",
    "versions",
    "shader",
    "framebuffer",
    "native_framebuffer",
    "render_distance",
    "simulation_distance",
    "scale",
    "filter",
    "cap",
    "vsync",
    "fullscreen",
    "focused",
    "throttled",
    "weather",
    "time",
    "power",
    "background",
)


def analyze(intervals):
    ms = list(intervals)
    if len(ms) < 2 or any(
        isinstance(x, bool)
        or not isinstance(x, (float, int))
        or not math.isfinite(x)
        or x <= 0
        for x in ms
    ):
        raise ValueError("Need positive finite frame intervals")
    # math.fsum is exact, so the metrics are identical on every supported Python.
    total = math.fsum(ms)
    ordered = sorted(ms)

    def percentile(p):
        return ordered[max(0, math.ceil(p * len(ms)) - 1)]

    # Whole measured intervals crossing a threshold, NOT excess over the threshold.
    over = {
        f"over_{t}": {
            "count": sum(x > t for x in ms),
            "time_ms": math.fsum(x for x in ms if x > t),
        }
        for t in (33, 50, 100)
    }
    abrupt = []
    abrupt_count = 0
    for i, x in enumerate(ms):
        neighbors = ms[max(0, i - 30) : i] + ms[i + 1 : i + 31]
        local = statistics.median(neighbors)
        if x > 2 * local and x - local > 8:
            abrupt_count += 1
            if len(abrupt) < 100:
                abrupt.append(
                    {
                        "frame": i + 1,
                        "interval_ms": x,
                        "local_median_ms": round(local, 3),
                    }
                )
    left = 0
    duration = 0.0
    worst = None
    for right, x in enumerate(ms):
        duration += x
        while left < right and duration - ms[left] >= 5000:
            duration -= ms[left]
            left += 1
        if duration >= 5000:
            fps = (right - left + 1) * 1000 / duration
            worst = fps if worst is None else min(worst, fps)
    return dict(
        metric="cpu_frame_production",
        intervals=len(ms),
        duration_s=total / 1000,
        average_fps=len(ms) * 1000 / total,
        p50_ms=percentile(0.5),
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99),
        max_ms=max(ms),
        worst_5s_fps=worst,
        local_outliers={
            "count": abrupt_count,
            "definition": "interval > 2× neighboring 60-frame median AND > 8 ms above it",
            "events": abrupt[:100],
            "truncated": abrupt_count > 100,
        },
        **over,
    )


def read_csv(path):
    values = []
    last = None
    count = 0
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["frame", "nanotime", "interval_ns"]:
            raise ValueError("Unexpected frame CSV header")
        for row in reader:
            count += 1
            if count > 100000:
                raise ValueError("Capture exceeds 100,000 frames; use short segments")
            if int(row["frame"]) != count - 1:
                raise ValueError("Frame indexes must be consecutive from zero")
            stamp = int(row["nanotime"])
            interval = int(row["interval_ns"])
            if last is None:
                if interval != 0:
                    raise ValueError("First interval must be zero")
            else:
                if stamp <= last or interval != stamp - last:
                    raise ValueError("Non-monotonic or inconsistent timestamps")
                values.append(interval / 1e6)
            last = stamp
    return values, count


def validate(capture):
    errors = []
    if not isinstance(capture, dict):
        return ["capture must be an object"]
    for section in ("expected", "observed", "visual", "completion", "metrics"):
        if not isinstance(capture.get(section), dict):
            return ["missing or invalid section: " + section]
    try:
        identifier(capture.get("id", ""))
    except (ValueError, TypeError):
        errors.append("invalid ID")
    if capture.get("status") != "done":
        errors.append("capture not done; timeout is not completion")
    if capture.get("metric") != "cpu_frame_production":
        errors.append("unsupported measurement source")
    expected = capture.get("expected", {})
    observed = capture.get("observed", {})
    for key in CONTEXT:
        if key not in expected or key not in observed:
            errors.append("missing context: " + key)
        elif expected[key] != observed[key]:
            errors.append("context mismatch: " + key)
        elif expected[key] is None or expected[key] == "":
            errors.append("empty context: " + key)
    if (
        observed.get("game_state") != "playing"
        or observed.get("player_alive") is not True
    ):
        errors.append(
            "capture is not living-player gameplay (menu, pause or death state)"
        )
    if observed.get("game_mode") not in (
        "creative",
        "survival",
        "adventure",
        "spectator",
    ):
        errors.append("unknown game mode")
    if observed.get("focused") is not True or observed.get("throttled") is not False:
        errors.append("focus/throttle gate failed")
    if observed.get("fullscreen") is not True:
        errors.append("native fullscreen gate failed")
    fb = observed.get("framebuffer")
    if (
        not isinstance(fb, list)
        or len(fb) != 2
        or any(type(v) is not int or v <= 0 for v in fb)
    ):
        errors.append("invalid framebuffer")
    if observed.get("native_framebuffer") != fb:
        errors.append("Output differs from verified native framebuffer")
    scale = observed.get("scale")
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not math.isfinite(scale)
        or not 0.5 <= scale <= 1
    ):
        errors.append("invalid scale")
    visual = capture.get("visual", {})
    if (
        visual.get("valid") is not True
        or visual.get("artifacts") is not False
        or visual.get("acceptable_quality") is not True
        or not visual.get("reviewer")
    ):
        errors.append("visual review missing or failed")
    completion = capture.get("completion", {})
    if (
        completion.get("unfocused_frames") != 0
        or completion.get("buffer_full") is not False
        or completion.get("error") != ""
    ):
        errors.append("sampler completion gate failed")
    metrics = capture.get("metrics", {})
    duration = metrics.get("duration_s", 0)
    if (
        not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or not 15 <= duration <= 35
    ):
        errors.append("capture duration outside 15–35 seconds")
    for name in ("average_fps", "p95_ms", "p99_ms", "max_ms", "worst_5s_fps"):
        v = metrics.get(name)
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or v <= 0
        ):
            errors.append("invalid metric: " + name)
    for name in ("over_33", "over_50", "over_100", "local_outliers"):
        entry = metrics.get(name, {})
        if (
            not isinstance(entry, dict)
            or type(entry.get("count")) is not int
            or entry["count"] < 0
        ):
            errors.append("invalid count: " + name)
    return errors


def comparable(a, b):
    # All non-settings controls must match. A scale change is the proposed intervention.
    allowed = {"scale", "render_distance", "simulation_distance"}
    mismatch = [
        key
        for key in CONTEXT
        if key not in allowed and a["observed"].get(key) != b["observed"].get(key)
    ]
    if abs(a["metrics"]["duration_s"] - b["metrics"]["duration_s"]) > 1:
        mismatch.append("capture duration")
    return mismatch
