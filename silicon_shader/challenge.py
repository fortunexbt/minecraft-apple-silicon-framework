"""Bounded, self-reported A/B evidence. No execution or submission transport."""

import copy
import hashlib
import json
import math
import re
from pathlib import Path

from .measure import CONTEXT, analyze, read_csv, validate

MAX_BYTES = 8_000_000
MAX_INTERVALS = 30_000
SETTINGS = {
    "resolution",
    "scale",
    "render_distance",
    "simulation_distance",
    "cap",
    "filter",
    "visual_properties",
}
INTERVENTIONS = (SETTINGS - {"resolution"}) | {"shader", "mods"}
SAFE_CONTROLS = {
    "game_state",
    "player_alive",
    "game_mode",
    "dimension",
    "weather",
    "time",
    "power",
    "background",
    "vsync",
    "fullscreen",
    "focused",
    "throttled",
}


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("Unexpected or missing fields: " + label)


def _label(value):
    # Deliberately restrictive public labels, not an anonymization operation.
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+ -]{0,47}", value)
        or ".." in value
        or re.search(
            r"(token|secret|password|bearer|sk-|ghp_|github_pat_)", value, re.IGNORECASE
        )
        or re.search(r"[A-Za-z0-9_-]{32,}", value)
    ):
        raise ValueError(
            "Unsafe public label; use a short generic product/version label"
        )


def _number(value, low, high, integer=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
        or (integer and type(value) is not int)
    ):
        raise ValueError("Number outside supported bounds")


def _properties(value):
    if not isinstance(value, dict) or len(value) > 100:
        raise ValueError("Invalid visual properties")
    for k, v in value.items():
        _label(k)
        if isinstance(v, str):
            _label(v)
        elif type(v) is bool:
            pass
        else:
            _number(v, -100000, 100000)


def _metadata(meta):
    _keys(
        meta,
        {
            "hardware",
            "minecraft",
            "loader",
            "launcher",
            "harness",
            "runtime",
            "workload",
            "interventions",
            "baseline",
            "candidate",
            "quality_review",
        },
        "metadata",
    )
    _keys(
        meta["hardware"],
        {"family", "tier", "cpu_cores", "gpu_cores", "memory_gib"},
        "hardware",
    )
    hw = meta["hardware"]
    if hw["family"] not in ["M1", "M2", "M3", "M4", "M5"] or hw["tier"] not in [
        "base",
        "pro",
        "max",
        "ultra",
    ]:
        raise ValueError("Unsupported chip family/tier")
    for key in ("cpu_cores", "gpu_cores", "memory_gib"):
        _number(hw[key], 1, 512, True)
    _keys(meta["workload"], {"scene", "route", "terrain"}, "workload")
    for value in meta["workload"].values():
        _label(value)
    for key in ("minecraft", "launcher", "harness", "runtime"):
        _label(meta[key])
    _keys(meta["loader"], {"name", "version"}, "loader")
    for v in meta["loader"].values():
        _label(v)
    interventions = meta["interventions"]
    if (
        not isinstance(interventions, list)
        or not interventions
        or len(interventions) > len(INTERVENTIONS)
        or any(type(v) is not str or v not in INTERVENTIONS for v in interventions)
        or len(set(interventions)) != len(interventions)
    ):
        raise ValueError("Invalid interventions")
    for name in ("baseline", "candidate"):
        run = meta[name]
        _keys(run, {"mods", "shader", "settings"}, name)
        if not isinstance(run["mods"], dict) or not 1 <= len(run["mods"]) <= 200:
            raise ValueError("List explicit mod versions")
        for k, v in run["mods"].items():
            _label(k)
            _label(v)
        _keys(run["shader"], {"name", "version"}, "shader")
        for v in run["shader"].values():
            _label(v)
        s = run["settings"]
        _keys(s, SETTINGS, "settings")
        if not isinstance(s["resolution"], list) or len(s["resolution"]) != 2:
            raise ValueError("Invalid resolution")
        for v in s["resolution"]:
            _number(v, 320, 16384, True)
        _number(s["scale"], 0.5, 1)
        for key in ("render_distance", "simulation_distance"):
            _number(s[key], 2, 64, True)
        _number(s["cap"], 0, 1000, True)
        if s["filter"] not in ("nearest", "linear", "off", "fsr"):
            raise ValueError("Unknown filter")
        _properties(s["visual_properties"])
    a, b = meta["baseline"], meta["candidate"]
    changed = {k for k in SETTINGS if a["settings"][k] != b["settings"][k]}
    changed |= {k for k in ("mods", "shader") if a[k] != b[k]}
    if changed != set(interventions):
        raise ValueError(
            "Declare exactly the changed interventions; all other controls must match"
        )
    q = meta["quality_review"]
    _keys(
        q,
        {
            "reviewed",
            "baseline_acceptable",
            "candidate_acceptable",
            "artifacts",
            "outcome",
        },
        "quality_review",
    )
    if (
        q["reviewed"] is not True
        or q["baseline_acceptable"] is not True
        or q["candidate_acceptable"] is not True
        or q["artifacts"] is not False
        or q["outcome"] not in ("improved", "equivalent", "tradeoff")
    ):
        raise ValueError("Explicit acceptable visual quality review required")


def _load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        if Path(path).stat().st_size > MAX_BYTES:
            raise ValueError("Input file too large")
        return json.loads(
            Path(path).read_text(),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("Nonfinite JSON number")
            ),
        )
    except (OSError, UnicodeError, RecursionError, json.JSONDecodeError) as e:
        raise ValueError("Unreadable or malformed JSON") from e


def _trace(values):
    if not isinstance(values, list) or not 2 <= len(values) <= MAX_INTERVALS:
        raise ValueError("Invalid interval count")
    metrics = analyze(values)
    if not 20 <= metrics["duration_s"] <= 31:
        raise ValueError(
            "Use 20–30 second runs (up to one second completion tolerance)"
        )
    return metrics


def _cohort(bundle):
    meta = copy.deepcopy(bundle["metadata"])
    interventions = meta.pop("interventions")
    meta.pop("quality_review")
    baseline = meta.pop("baseline")
    meta.pop("candidate")
    for key in interventions:
        if key in SETTINGS:
            baseline["settings"].pop(key)
        else:
            baseline.pop(key)
    return _hash(
        {
            "metadata": meta,
            "controls": bundle["controls"],
            "fixed_configuration": baseline,
        }
    )


def _check_bundle(bundle):
    _keys(
        bundle,
        {
            "schema_version",
            "status",
            "metric",
            "metadata",
            "controls",
            "runs",
            "cohort_hash",
            "content_digest",
        },
        "bundle",
    )
    if (
        type(bundle["schema_version"]) is not int
        or bundle["schema_version"] != 1
        or bundle["status"] != "self_reported"
        or bundle["metric"] != "cpu_frame_production"
    ):
        raise ValueError("Unsupported schema, status or metric")
    _metadata(bundle["metadata"])
    _keys(bundle["controls"], SAFE_CONTROLS, "controls")
    c = bundle["controls"]
    for k in ("player_alive", "fullscreen", "focused"):
        if c[k] is not True:
            raise ValueError("Invalid gameplay controls")
    if (
        c["throttled"] is not False
        or type(c["vsync"]) is not bool
        or c["game_state"] != "playing"
        or c["game_mode"] not in ("creative", "survival", "adventure", "spectator")
    ):
        raise ValueError("Invalid gameplay controls")
    if c["dimension"] not in ("overworld", "nether", "end"):
        raise ValueError("Use a standard public dimension label")
    for k in ("dimension", "weather", "time", "power", "background"):
        _label(c[k])
    _keys(bundle["runs"], {"baseline", "candidate"}, "runs")
    durations = []
    for run in bundle["runs"].values():
        _keys(run, {"intervals_ms", "metrics", "csv_sha256"}, "run")
        if not isinstance(run["csv_sha256"], str) or not re.fullmatch(
            "[0-9a-f]{64}", run["csv_sha256"]
        ):
            raise ValueError("Missing CSV provenance")
        metrics = _trace(run["intervals_ms"])
        if _canonical(metrics) != _canonical(run["metrics"]):
            raise ValueError("Metrics differ from recomputed trace")
        durations.append(metrics["duration_s"])
    if abs(durations[0] - durations[1]) > 1:
        raise ValueError("Run durations differ by more than one second")
    if bundle["cohort_hash"] != _cohort(bundle):
        raise ValueError("Cohort hash mismatch")
    unsigned = {k: v for k, v in bundle.items() if k != "content_digest"}
    if bundle["content_digest"] != _hash(unsigned):
        raise ValueError("Content digest mismatch")


def validate_bundle(bundle):
    """Return errors, or [] for structurally valid self-reported evidence."""
    try:
        if len(_canonical(bundle)) > MAX_BYTES:
            raise ValueError("Bundle too large")
        _check_bundle(bundle)
        return []
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        RecursionError,
    ) as e:
        return [str(e) or "Malformed bundle"]


def prepare(
    baseline_capture_path,
    candidate_capture_path,
    baseline_csv_path,
    candidate_csv_path,
    metadata_path,
):
    """Prepare a privacy-minimized dict, raising ValueError on invalid evidence."""
    try:
        meta = _load(metadata_path)
        _metadata(meta)
        captures, runs = {}, {}
        for name, cp, csv_path in (
            ("baseline", baseline_capture_path, baseline_csv_path),
            ("candidate", candidate_capture_path, candidate_csv_path),
        ):
            capture = _load(cp)
            errors = validate(capture)
            if errors:
                raise ValueError("; ".join(errors))
            if Path(csv_path).stat().st_size > MAX_BYTES:
                raise ValueError("CSV too large")
            csv_digest = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()
            if capture.get("provenance", {}).get("csv_sha256") != csv_digest:
                raise ValueError("Missing or mismatched CSV provenance")
            values, _ = read_csv(csv_path)
            metrics = _trace(values)
            if _canonical(capture["metrics"]) != _canonical(metrics):
                raise ValueError("Capture metrics differ from raw CSV")
            observed = capture["observed"]
            if observed["runtime"] != meta["runtime"] or any(
                observed[k] != v for k, v in meta["workload"].items()
            ):
                raise ValueError("Public workload/runtime differs from capture")
            settings = meta[name]["settings"]
            for key in SETTINGS - {"visual_properties"}:
                context_key = "framebuffer" if key == "resolution" else key
                if settings[key] != observed[context_key]:
                    raise ValueError("Metadata differs from capture: " + key)
            if meta[name]["shader"]["name"] != observed["shader"]:
                raise ValueError("Shader name differs from capture")
            captures[name] = capture
            runs[name] = {
                "intervals_ms": values,
                "metrics": metrics,
                "csv_sha256": csv_digest,
            }
        allowed = set(meta["interventions"]) - {"visual_properties", "mods"}
        if "mods" in meta["interventions"]:
            allowed.add("versions")
        for key in CONTEXT:
            if (
                key not in allowed
                and captures["baseline"]["observed"][key]
                != captures["candidate"]["observed"][key]
            ):
                raise ValueError("Unmatched capture context: " + key)
        bundle = {
            "schema_version": 1,
            "status": "self_reported",
            "metric": "cpu_frame_production",
            "metadata": meta,
            "controls": {k: captures["baseline"]["observed"][k] for k in SAFE_CONTROLS},
            "runs": runs,
        }
        bundle["cohort_hash"] = _cohort(bundle)
        bundle["content_digest"] = _hash(bundle)
        errors = validate_bundle(bundle)
        if errors:
            raise ValueError("; ".join(errors))
        return bundle
    except (
        OSError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        RecursionError,
    ) as e:
        raise ValueError("Malformed challenge input") from e
