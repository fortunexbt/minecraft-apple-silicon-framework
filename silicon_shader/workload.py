"""One shared challenge workload; route receipts are evidence, not remote attestation."""

import copy
import math
import json
from importlib.resources import files

WORKLOAD_ID = "silicon-shader-overworld-v1"
REFERENCE = json.loads(
    files("silicon_shader").joinpath("workloads/overworld-v1.json").read_text()
)


def contract():
    return copy.deepcopy(REFERENCE)


def validate_world(facts):
    expected = {
        "minecraft_version": "26.3",
        "data_version": 5023,
        "seed": 20260929,
        "generator": "net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator",
        "noise_settings": "minecraft:overworld",
        "biome_source": "net.minecraft.world.level.biome.MultiNoiseBiomeSource",
        "biome_preset_overworld": True,
        "structures": True,
        "bonus_chest": False,
    }
    if not isinstance(facts, dict) or set(facts) != set(expected) | {
        "datapacks",
        "terrain",
    }:
        raise ValueError("Missing or unexpected observed world facts")
    for key, value in expected.items():
        if type(facts[key]) is not type(value) or facts[key] != value:
            raise ValueError("Wrong reference world: " + key)
    if len(REFERENCE["terrain"]) != 3 or facts["terrain"] != REFERENCE["terrain"]:
        raise ValueError("Terrain sentinels differ from the reference landscape")
    packs = facts["datapacks"]
    if (
        not isinstance(packs, list)
        or not all(isinstance(v, str) for v in packs)
        or "vanilla" not in packs
        or not set(packs) <= {"vanilla", "fabric", "fabric-convention-tags-v2"}
        or len(packs) != len(set(packs))
    ):
        raise ValueError(
            "Custom or unobserved datapacks are not part of the reference world"
        )
    return facts


def _number(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError("Route observations must be finite numbers")
    return value


def _vector(value, size):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("Invalid observed pose")
    return [_number(v) for v in value]


def _require_keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("Missing or unexpected " + name + " fields")


def _angle_delta(a, b):
    return abs((_number(a) - b + 180) % 360 - 180)


def _environment(observed):
    expected = {
        "dimension": "minecraft:overworld",
        "day_ticks": 6000,
        "raining": False,
        "thundering": False,
    }
    _require_keys(observed, expected, "observed environment")
    if any(
        type(observed[k]) is not type(v) or observed[k] != v
        for k, v in expected.items()
    ):
        raise ValueError(
            "Observed dimension, weather or time differs from the standard"
        )


def validate_route(receipt, run, settings):
    route = REFERENCE["route"]
    _require_keys(
        receipt,
        {"workload_id", "world", "settings", "warmup", "samples", "csv_sha256"},
        "route receipt",
    )
    if (
        receipt["workload_id"] != WORKLOAD_ID
        or receipt["csv_sha256"] != run["csv_sha256"]
    ):
        raise ValueError("Route receipt belongs to another workload or frame CSV")
    validate_world(receipt["world"])
    observed_settings = receipt["settings"]
    _require_keys(
        observed_settings, {"fov", "fov_effect_scale", "flying_speed"}, "route settings"
    )
    if (
        _number(observed_settings["fov"]) != 70
        or abs(_number(observed_settings["fov_effect_scale"])) > 1e-6
        or abs(_number(observed_settings["flying_speed"]) - 0.05) > 1e-6
    ):
        raise ValueError("Wrong FOV, FOV effects or flying speed")
    warmup = receipt["warmup"]
    _require_keys(warmup, {"seconds", "ticks", "samples"}, "warmup")
    if (
        not 30 <= _number(warmup["seconds"]) <= 30.25
        or type(warmup["ticks"]) is not int
        or abs(warmup["ticks"] - warmup["seconds"] * 20) > 3
    ):
        raise ValueError("Missing or stalled recorded 30-second warmup")
    warm = warmup["samples"]
    if not isinstance(warm, list) or not 31 <= len(warm) <= 33:
        raise ValueError("Missing stationary warmup observations")
    origin = route["start"]
    previous = None
    for sample in warm:
        _require_keys(
            sample,
            {"t", "position", "flying", "focused", "paused", "environment"},
            "warmup sample",
        )
        _environment(sample["environment"])
        now = _number(sample["t"])
        if previous is not None and not 0 < now - previous <= 1.2:
            raise ValueError("Warmup observations have a gap")
        if (
            math.dist(_vector(sample["position"], 3), origin) > 0.05
            or sample["flying"] is not True
            or sample["focused"] is not True
            or sample["paused"] is not False
        ):
            raise ValueError("Warmup did not remain stationary, flying and focused")
        previous = now
    if abs(warm[0]["t"]) > 0.1 or abs(warm[-1]["t"] - warmup["seconds"]) > 0.15:
        raise ValueError("Warmup samples do not cover the warmup")
    samples = receipt["samples"]
    reference = route["samples"]
    if not isinstance(samples, list) or len(samples) != len(reference):
        raise ValueError("Missing trajectory samples")
    first_t = None
    previous_t = None
    previous_game_tick = 0
    for sample, expected in zip(samples, reference):
        _require_keys(
            sample,
            {
                "t",
                "tick",
                "game_tick",
                "position",
                "yaw",
                "pitch",
                "flying",
                "focused",
                "paused",
                "framebuffer",
                "environment",
            },
            "route sample",
        )
        _environment(sample["environment"])
        t = _number(sample["t"])
        if first_t is None:
            first_t = t
            if not -0.05 <= t <= 0.15:
                raise ValueError("Route start is not aligned with the measured frames")
        if previous_t is not None and t <= previous_t:
            raise ValueError("Movement observation times must increase")
        previous_t = t
        if (
            type(sample["tick"]) is not int
            or sample["tick"] != expected["tick"]
            or type(sample["game_tick"]) is not int
            or sample["game_tick"] < previous_game_tick
            or (sample["tick"] == 0 and sample["game_tick"] != 0)
        ):
            raise ValueError(
                "Route did not follow the standard client/server tick sequence"
            )
        previous_game_tick = sample["game_tick"]
        if (
            math.dist(_vector(sample["position"], 3), expected["position"])
            > route["position_tolerance"]
        ):
            raise ValueError("Wrong, obstructed or divergent flight path")
        if (
            _angle_delta(sample["yaw"], expected.get("yaw", route["yaw"])) > 0.1
            or abs(_number(sample["pitch"]) - expected.get("pitch", route["pitch"]))
            > 0.1
        ):
            raise ValueError("Camera departed from the standard route")
        if (
            sample["flying"] is not True
            or sample["focused"] is not True
            or sample["paused"] is not False
        ):
            raise ValueError("Flight, focus or simulation interrupted")
        if sample["framebuffer"] != settings["resolution"]:
            raise ValueError("Observed framebuffer differs from reported settings")
    duration = run["metrics"]["duration_s"]
    last_frame_start = duration - run["intervals_ms"][-1] / 1000
    if (
        not 20.8 <= samples[-1]["t"] - first_t <= 30
        or duration < samples[-1]["t"] - 0.05
        or last_frame_start > samples[-1]["t"] + 0.05
    ):
        raise ValueError("Frame capture does not cover the standard route")
    if not 20.8 <= run["metrics"]["duration_s"] <= 30:
        raise ValueError("The complete standard route must fit within 30 seconds")


def validate_workload(bundle):
    if bundle.get("workload_id") != WORKLOAD_ID:
        raise ValueError("Submission does not use the current standard workload")
    if (
        not REFERENCE["route"]
        or not REFERENCE["route"].get("samples")
        or len(REFERENCE["terrain"]) != 3
    ):
        raise ValueError(
            "Reference route is awaiting live preflight; submissions are not yet enabled"
        )
    metadata = bundle["metadata"]
    if metadata["minecraft"] != REFERENCE["minecraft"] or metadata["workload"] != {
        "scene": "overworld-flight",
        "route": WORKLOAD_ID,
        "terrain": "vanilla-seed-20260929",
    }:
        raise ValueError("Metadata does not identify the pinned reference workload")
    for field in ("dimension", "game_mode", "weather", "time"):
        if bundle["controls"][field] != REFERENCE[field]:
            raise ValueError("Wrong standard environment: " + field)
    for name in ("baseline", "candidate"):
        settings = metadata[name]["settings"]
        if not 8 <= settings["render_distance"] <= 32:
            raise ValueError("Reference terrain supports render distances 8–32")
        run = bundle["runs"][name]
        validate_route(run["route_receipt"], run, settings)
    baseline = bundle["runs"]["baseline"]["route_receipt"]
    candidate = bundle["runs"]["candidate"]["route_receipt"]
    if baseline["world"] != candidate["world"]:
        raise ValueError("Baseline and candidate world facts differ")


def require_standard(bundle):
    if bundle.get("schema_version") != 2:
        raise ValueError(
            "New submissions require the standard route and two observed route receipts"
        )
    validate_workload(bundle)


def import_route(root, run_id):
    """Normalize the shipped adapter's real files; never manufacture completion."""
    import csv
    from pathlib import Path
    from .common import identifier, properties, digest
    from .measure import read_csv, analyze

    identifier(run_id)
    root = Path(root)

    def file(suffix):
        path = root / (run_id + suffix)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
            raise ValueError("Missing, unsafe or oversized route evidence")
        return path

    def rows(suffix):
        expected = [
            "client_tick",
            "nano_time",
            "elapsed_seconds",
            "game_tick",
            "x",
            "y",
            "z",
            "yaw",
            "pitch",
            "vx",
            "vy",
            "vz",
            "flying",
            "game_mode",
            "focused",
            "paused",
            "width",
            "height",
            "dimension",
            "day_ticks",
            "raining",
            "thundering",
        ]
        with file(suffix).open(newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != expected:
                raise ValueError("Unexpected or duplicate route CSV columns")
            data = []
            for row in reader:
                if (
                    len(data) >= 1000
                    or None in row
                    or any(v is None for v in row.values())
                ):
                    raise ValueError("Invalid route observation count or row")
                data.append(row)
        if not data:
            raise ValueError("Missing route observations")
        return data

    def boolean(value):
        if str(value).lower() not in ("true", "false"):
            raise ValueError("Missing boolean route observation")
        return str(value).lower() == "true"

    def environment(row):
        return {
            "dimension": row["dimension"],
            "day_ticks": int(row["day_ticks"]) % 24000,
            "raining": boolean(row["raining"]),
            "thundering": boolean(row["thundering"]),
        }

    try:
        raw = properties(file("-route.txt"))
        if (
            raw.get("workload") != WORKLOAD_ID
            or raw.get("run_id") != run_id
            or raw.get("status") not in ("recorded", "calibration_required")
            or raw.get("client_ticks") != "420"
        ):
            raise ValueError("Route runner did not finish the standard workload")
        completion = properties(file("-done.txt"))
        if (
            completion.get("unfocused_frames") != "0"
            or completion.get("buffer_full") != "false"
            or completion.get("frame_sink_error") != ""
        ):
            raise ValueError("Frame sampler completion is not clean")
        frame_path = file("-frames.csv")
        intervals, count = read_csv(frame_path)
        if completion.get("frames") != str(count):
            raise ValueError("Frame completion and CSV disagree")
        with frame_path.open() as stream:
            first_frame = next(csv.DictReader(stream))
        frame_zero = int(first_frame["nanotime"])
        route_rows = rows("-route.csv")
        first_game_tick = int(route_rows[0]["game_tick"])
        samples = []
        for row in route_rows:
            if row["game_mode"].lower() != "creative":
                raise ValueError("Route was not in creative mode")
            samples.append(
                {
                    "t": (int(row["nano_time"]) - frame_zero) / 1e9,
                    "tick": int(row["client_tick"]),
                    "game_tick": int(row["game_tick"]) - first_game_tick,
                    "position": [float(row[k]) for k in ("x", "y", "z")],
                    "yaw": float(row["yaw"]),
                    "pitch": float(row["pitch"]),
                    "flying": boolean(row["flying"]),
                    "focused": boolean(row["focused"]),
                    "paused": boolean(row["paused"]),
                    "framebuffer": [int(row["width"]), int(row["height"])],
                    "environment": environment(row),
                }
            )
        warmup_zero = int(raw["warmup_begin_nano"])
        warmup_end = int(raw["warmup_end_nano"])
        warmup = {
            "seconds": (warmup_end - warmup_zero) / 1e9,
            "ticks": int(raw["warmup_client_ticks"]),
            "samples": [
                {
                    "t": (int(row["nano_time"]) - warmup_zero) / 1e9,
                    "position": [float(row[k]) for k in ("x", "y", "z")],
                    "flying": boolean(row["flying"]),
                    "focused": boolean(row["focused"]),
                    "paused": boolean(row["paused"]),
                    "environment": environment(row),
                }
                for row in rows("-warmup.csv")
            ],
        }
        receipt = {
            "workload_id": WORKLOAD_ID,
            "world": {
                "minecraft_version": raw["observed_minecraft_version"],
                "data_version": int(raw["observed_data_version"]),
                "seed": int(raw["observed_seed"]),
                "structures": boolean(raw["observed_generate_structures"]),
                "bonus_chest": boolean(raw["observed_bonus_chest"]),
                "generator": raw["observed_generator_class"],
                "noise_settings": raw["observed_generator_settings"],
                "biome_source": raw["observed_biome_source_class"],
                "biome_preset_overworld": boolean(
                    raw["observed_overworld_biome_source_stable"]
                ),
                "terrain": [
                    {
                        "x": x,
                        "z": z,
                        "height": int(
                            raw[f"observed_terrain_{x}_{z}"].split(",", 1)[0]
                        ),
                        "block": raw[f"observed_terrain_{x}_{z}"].split(",", 1)[1],
                    }
                    for x, z in [(-121, 438), (-121, 320), (-240, 300)]
                ],
                "datapacks": sorted(
                    value
                    for key, value in raw.items()
                    if key.startswith("observed_enabled_pack_")
                ),
            },
            "settings": {
                "fov": int(raw["observed_fov"]),
                "fov_effect_scale": float(raw["observed_fov_effect_scale"]),
                "flying_speed": float(raw["observed_flying_speed"]),
            },
            "warmup": warmup,
            "samples": samples,
            "csv_sha256": digest(frame_path),
        }
        if (
            not REFERENCE["route"]
            or not REFERENCE["route"].get("samples")
            or len(REFERENCE["terrain"]) != 3
        ):
            raise ValueError("Reference route has not completed live preflight")
        validate_route(
            receipt,
            {
                "csv_sha256": receipt["csv_sha256"],
                "metrics": analyze(intervals),
                "intervals_ms": intervals,
            },
            {"resolution": samples[0]["framebuffer"]},
        )
        return receipt
    except (
        OSError,
        UnicodeError,
        csv.Error,
        KeyError,
        IndexError,
        StopIteration,
        TypeError,
        OverflowError,
    ) as error:
        raise ValueError("Incomplete or malformed route evidence") from error
