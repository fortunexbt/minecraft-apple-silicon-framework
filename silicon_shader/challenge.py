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


def _same_metrics(a, b):
    """Equal up to float rounding, so a bundle prepared on one Python validates on another.

    Python 3.12 made float sum() compensated, so the same trace gives metrics that
    differ in the last digits between 3.10/3.11 and 3.12+. The tolerance (relative
    1e-9) is far below anything that could hide a real change, and the content
    digest still covers the exact stored numbers.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_metrics(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_metrics(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return (
            isinstance(a, (int, float))
            and isinstance(b, (int, float))
            and not isinstance(a, bool)
            and not isinstance(b, bool)
            and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        )
    return type(a) is type(b) and a == b


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _keys(value, keys, label):
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected or missing fields: {label} must be an object")
    missing = sorted(set(keys) - set(value))
    extra = sorted(set(value) - set(keys))
    if missing or extra:
        detail = []
        if missing:
            detail.append("missing " + ", ".join(map(str, missing)))
        if extra:
            detail.append("unexpected " + ", ".join(map(str, extra)))
        raise ValueError(f"Unexpected or missing fields: {label} ({'; '.join(detail)})")


PLACEHOLDER = "<fill in>"
_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+() -]{0,47}")
# Secret-looking prefixes match only at a word start, so "Disk-Cache" and
# "risk-free" are fine while "sk-live-..." and "ghp_..." are not.
_SECRET = re.compile(
    r"(token|secret|password|bearer|\bsk-|\bgh[pousr]_|github_pat_)", re.IGNORECASE
)


def _label(value, name="label"):
    # Deliberately restrictive public labels, not an anonymization operation.
    # The message names the field but never echoes the value.
    if isinstance(value, str) and PLACEHOLDER in value:
        raise ValueError(f"Replace the {PLACEHOLDER} placeholder in {name}")
    if (
        not isinstance(value, str)
        or not _LABEL.fullmatch(value)
        or ".." in value
        or _SECRET.search(value)
        or re.search(r"[A-Za-z0-9_-]{32,}", value)
    ):
        raise ValueError(
            f"Unsafe public {name}; use a short generic product/version label "
            "of 1-48 characters (letters, digits, spaces and . _ + - ( ))"
        )


def _number(value, low, high, integer=False, name="number"):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
        or (integer and type(value) is not int)
    ):
        shown = ""
        if isinstance(value, (int, float)) and math.isfinite(value):
            shown = f", got {value!r}"
        kind = "an integer" if integer else "a number"
        raise ValueError(f"{name} must be {kind} from {low} to {high}{shown}")


def _properties(value):
    if not isinstance(value, dict) or len(value) > 100:
        raise ValueError("Invalid visual properties")
    for k, v in value.items():
        _label(k, "visual property name")
        if isinstance(v, str):
            _label(v, f"value of visual property {k}")
        elif type(v) is bool:
            pass
        else:
            _number(v, -100000, 100000, name=f"visual property {k}")


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
    hw = meta["hardware"]
    required_hardware = {"family", "tier", "cpu_cores", "gpu_cores", "memory_gib"}
    if (
        not isinstance(hw, dict)
        or not required_hardware <= set(hw)
        or set(hw) - required_hardware - {"model", "model_identifier"}
    ):
        raise ValueError("Unexpected or missing hardware fields")
    if (
        not isinstance(hw["family"], str)
        or not re.fullmatch(r"[MA][1-9][0-9]{0,2}", hw["family"])
        or hw["tier"] not in ("base", "pro", "max", "ultra")
    ):
        raise ValueError("Use the observed Apple chip family and tier")
    for key in ("cpu_cores", "gpu_cores", "memory_gib"):
        _number(hw[key], 1, 2048, True, f"hardware.{key}")
    if "model" in hw:
        _label(hw["model"], "hardware.model")
    if "model_identifier" in hw and (
        not isinstance(hw["model_identifier"], str)
        or not re.fullmatch(r"[A-Za-z]+[0-9]+,[0-9]+", hw["model_identifier"])
    ):
        raise ValueError("Invalid generic Mac model identifier")
    _keys(meta["workload"], {"scene", "route", "terrain"}, "workload")
    for key, value in meta["workload"].items():
        _label(value, f"workload.{key}")
    for key in ("minecraft", "launcher", "harness", "runtime"):
        _label(meta[key], key)
    _keys(meta["loader"], {"name", "version"}, "loader")
    for key, v in meta["loader"].items():
        _label(v, f"loader.{key}")
    interventions = meta["interventions"]
    if (
        not isinstance(interventions, list)
        or not interventions
        or len(interventions) > len(INTERVENTIONS)
        or any(type(v) is not str or v not in INTERVENTIONS for v in interventions)
        or len(set(interventions)) != len(interventions)
    ):
        raise ValueError(
            "interventions must be a non-empty list of unique names from: "
            + ", ".join(sorted(INTERVENTIONS))
        )
    for name in ("baseline", "candidate"):
        run = meta[name]
        _keys(run, {"mods", "shader", "settings"}, name)
        if not isinstance(run["mods"], dict) or not 1 <= len(run["mods"]) <= 200:
            raise ValueError(
                f"{name}.mods must list 1 to 200 mod-name to version entries"
            )
        for k, v in run["mods"].items():
            _label(k, f"{name} mod name")
            _label(v, f"{name} version of mod {k}")
        _keys(run["shader"], {"name", "version"}, f"{name}.shader")
        for key, v in run["shader"].items():
            _label(v, f"{name}.shader.{key}")
        s = run["settings"]
        _keys(s, SETTINGS, f"{name}.settings")
        if not isinstance(s["resolution"], list) or len(s["resolution"]) != 2:
            raise ValueError(f"{name}.settings.resolution must be [width, height]")
        for v in s["resolution"]:
            _number(v, 320, 16384, True, f"{name}.settings.resolution")
        _number(s["scale"], 0.5, 1, name=f"{name}.settings.scale")
        for key in ("render_distance", "simulation_distance"):
            _number(s[key], 2, 64, True, f"{name}.settings.{key}")
        _number(s["cap"], 0, 1000, True, f"{name}.settings.cap (0 means uncapped)")
        if s["filter"] not in ("nearest", "linear", "off", "fsr"):
            raise ValueError(
                f"{name}.settings.filter must be one of nearest, linear, off, fsr"
            )
        _properties(s["visual_properties"])
    a, b = meta["baseline"], meta["candidate"]
    changed = {k for k in SETTINGS if a["settings"][k] != b["settings"][k]}
    changed |= {k for k in ("mods", "shader") if a[k] != b[k]}
    if changed != set(interventions):
        raise ValueError(
            "Declare exactly the changed interventions; all other controls must match. "
            f"Changed between baseline and candidate: {sorted(changed)}; "
            f"declared: {sorted(interventions)}"
            + (
                "; missing from declared: "
                + ", ".join(sorted(changed - set(interventions)))
                if changed - set(interventions)
                else ""
            )
            + (
                "; not actually changed: "
                + ", ".join(sorted(set(interventions) - changed))
                if set(interventions) - changed
                else ""
            )
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


def metadata_template(baseline_capture_path, candidate_capture_path, hardware=None):
    """Draft metadata from two captures.

    Observed values are filled in and the interventions list is derived from what
    differs. Anything only a person can know stays a placeholder that fails
    validation until replaced, including the visual quality review.
    """
    observed = {}
    for name, path in (
        ("baseline", baseline_capture_path),
        ("candidate", candidate_capture_path),
    ):
        capture = _load(path)
        if not isinstance(capture, dict) or not isinstance(
            capture.get("observed"), dict
        ):
            raise ValueError(f"{name} capture has no observed context")
        observed[name] = capture["observed"]
    base, cand = observed["baseline"], observed["candidate"]
    hw = hardware or {}

    def run(o):
        return {
            "mods": {PLACEHOLDER: PLACEHOLDER},
            "shader": {"name": o.get("shader"), "version": PLACEHOLDER},
            "settings": {
                "resolution": o.get("framebuffer"),
                "scale": o.get("scale"),
                "render_distance": o.get("render_distance"),
                "simulation_distance": o.get("simulation_distance"),
                "cap": o.get("cap"),
                "filter": o.get("filter"),
                "visual_properties": {"profile": PLACEHOLDER},
            },
        }

    detected = [
        key
        for key in ("scale", "render_distance", "simulation_distance", "cap", "filter")
        if base.get(key) != cand.get(key)
    ]
    if base.get("shader") != cand.get("shader"):
        detected.append("shader")
    if base.get("versions") != cand.get("versions"):
        detected.append("mods")
    notes = [
        "Interventions are detected from the two captures. Shader options, mod "
        "versions, window mode and graphics backend are not recorded in them: add "
        "visual_properties (and list the changed mods in candidate.mods) when those "
        "differ, and name window mode and backend in the recipe.",
        "Replace every <fill in> placeholder. quality_review stays unreviewed until "
        "someone has looked at both pictures and sets it.",
    ]
    template = {
        "hardware": {
            "family": hw.get("family") or PLACEHOLDER,
            "tier": hw.get("tier") or PLACEHOLDER,
            "cpu_cores": hw.get("cpu_cores"),
            "gpu_cores": hw.get("gpu_cores"),
            "memory_gib": int(hw["memory_gib"]) if hw.get("memory_gib") else None,
        },
        "minecraft": PLACEHOLDER,
        "loader": {"name": PLACEHOLDER, "version": PLACEHOLDER},
        "launcher": PLACEHOLDER,
        "harness": PLACEHOLDER,
        "runtime": base.get("runtime") or PLACEHOLDER,
        "workload": {
            "scene": base.get("scene"),
            "route": base.get("route"),
            "terrain": base.get("terrain"),
        },
        "interventions": detected,
        "baseline": run(base),
        "candidate": run(cand),
        "quality_review": {
            "reviewed": False,
            "baseline_acceptable": False,
            "candidate_acceptable": False,
            "artifacts": True,
            "outcome": PLACEHOLDER,
        },
    }
    return {"metadata": template, "interventions_detected": detected, "notes": notes}


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
    cohort = {
        "metadata": meta,
        "controls": bundle["controls"],
        "fixed_configuration": baseline,
    }
    # Preserve the exact v1 cohort calculation. The versioned route is part of
    # the identity only for v2 bundles that carry standardized route receipts.
    if bundle.get("schema_version") == 2:
        cohort["workload_id"] = bundle["workload_id"]
    return _hash(cohort)


def _check_bundle(bundle):
    legacy_keys = {
        "schema_version",
        "status",
        "metric",
        "metadata",
        "controls",
        "runs",
        "cohort_hash",
        "content_digest",
    }
    schema = bundle.get("schema_version") if isinstance(bundle, dict) else None
    if schema == 1:
        _keys(bundle, legacy_keys, "bundle")
    elif schema == 2:
        _keys(bundle, legacy_keys | {"workload_id"}, "bundle")
    else:
        raise ValueError("Unsupported schema, status or metric")
    if (
        type(bundle["schema_version"]) is not int
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
        run_keys = {"intervals_ms", "metrics", "csv_sha256"}
        if schema == 2:
            run_keys.add("route_receipt")
        _keys(run, run_keys, "run")
        if not isinstance(run["csv_sha256"], str) or not re.fullmatch(
            "[0-9a-f]{64}", run["csv_sha256"]
        ):
            raise ValueError("Missing CSV provenance")
        metrics = _trace(run["intervals_ms"])
        if not _same_metrics(metrics, run["metrics"]):
            raise ValueError("Metrics differ from recomputed trace")
        durations.append(metrics["duration_s"])
    if schema == 1 and abs(durations[0] - durations[1]) > 1:
        raise ValueError("Run durations differ by more than one second")
    if schema == 2:
        from .workload import validate_workload

        validate_workload(bundle)
    if bundle["cohort_hash"] != _cohort(bundle):
        raise ValueError("Cohort hash mismatch")
    unsigned = {k: v for k, v in bundle.items() if k != "content_digest"}
    if bundle["content_digest"] != _hash(unsigned):
        raise ValueError("Content digest mismatch")


def _is_pinned(metrics, cap):
    """True when the run sits at its frame limiter, so its FPS is a ceiling."""
    if not isinstance(cap, int) or not 0 < cap < 260:
        return False
    return (
        metrics["average_fps"] >= 0.97 * cap
        and metrics["p50_ms"] >= 0.97 * 1000.0 / cap
    )


def pinned_runs(bundle):
    meta = bundle["metadata"]
    return [
        name
        for name in ("baseline", "candidate")
        if _is_pinned(bundle["runs"][name]["metrics"], meta[name]["settings"]["cap"])
    ]


def warnings(bundle):
    """Advisory checks for results that look fine to the validators but may not be.

    Never raises and never affects validation, so historical entries stay valid.
    """
    out = []
    try:
        meta = bundle["metadata"]
        for name in pinned_runs(bundle):
            out.append(
                f"The {name} run is pinned at its {meta[name]['settings']['cap']} FPS cap: "
                "its FPS is a ceiling, not a measurement. Confirm the portrait shows the "
                "shader (a pack that failed to load, or Vulkan with Iris, renders the "
                "vanilla image at the cap) and consider capturing again with a higher cap."
            )
        base = bundle["runs"]["baseline"]["metrics"]["average_fps"]
        cand = bundle["runs"]["candidate"]["metrics"]["average_fps"]
        if (
            base > 0
            and abs(cand / base - 1) < 0.01
            and {"shader", "scale", "render_distance", "mods"}
            & set(meta["interventions"])
        ):
            out.append(
                "Candidate FPS is within 1% of the baseline although a shader, scale, "
                "render distance or mod was declared as changed. Confirm the change was "
                "actually applied in the candidate capture."
            )
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return out


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
    baseline_route_path=None,
    candidate_route_path=None,
):
    """Prepare a privacy-minimized dict, raising ValueError on invalid evidence."""
    try:
        if (baseline_route_path is None) != (candidate_route_path is None):
            raise ValueError("Provide both baseline and candidate route receipts")
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
            if not _same_metrics(capture["metrics"], metrics):
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
        if baseline_route_path is not None:
            runs["baseline"]["route_receipt"] = _load(baseline_route_path)
            runs["candidate"]["route_receipt"] = _load(candidate_route_path)
        allowed = set(meta["interventions"]) - {"visual_properties", "mods"}
        if "mods" in meta["interventions"]:
            allowed.add("versions")
        for key in CONTEXT:
            if (
                key not in allowed
                and captures["baseline"]["observed"][key]
                != captures["candidate"]["observed"][key]
            ):
                hint = (
                    " (the installed mod set differs; add mods to interventions and "
                    "list the added, removed or changed mods in the candidate)"
                    if key == "versions"
                    else " (baseline and candidate must match here unless it is a declared intervention)"
                )
                raise ValueError("Unmatched capture context: " + key + hint)
        bundle = {
            "schema_version": 2 if baseline_route_path is not None else 1,
            "status": "self_reported",
            "metric": "cpu_frame_production",
            "metadata": meta,
            "controls": {k: captures["baseline"]["observed"][k] for k in SAFE_CONTROLS},
            "runs": runs,
        }
        if baseline_route_path is not None:
            from .workload import WORKLOAD_ID

            bundle["workload_id"] = WORKLOAD_ID
        bundle["cohort_hash"] = _cohort(bundle)
        bundle["content_digest"] = _hash(bundle)
        errors = validate_bundle(bundle)
        if errors:
            raise ValueError("; ".join(errors))
        pinned = pinned_runs(bundle)
        if len(pinned) == 2:
            raise ValueError(
                "Both runs are pinned at their frame cap, so this comparison carries no "
                "information (a pack that failed to load, or the wrong graphics backend, "
                "also renders the vanilla image at the cap). Check the portrait shows the "
                "shader, then lift the cap (for example 260) or lower the settings and "
                "capture again."
            )
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
