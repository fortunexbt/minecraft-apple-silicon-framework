"""Synthetic route data for validator tests only; never public benchmark evidence."""

import copy
from silicon_shader import challenge, workload
from silicon_shader.measure import analyze


def seal(bundle):
    bundle["cohort_hash"] = challenge._cohort(bundle)
    bundle["content_digest"] = challenge._hash(
        {k: v for k, v in bundle.items() if k != "content_digest"}
    )
    return bundle


def standard_bundle(legacy):
    bundle = copy.deepcopy(legacy)
    bundle["schema_version"] = 2
    bundle["workload_id"] = workload.WORKLOAD_ID
    bundle["metadata"]["minecraft"] = "26.3"
    bundle["metadata"]["workload"] = {
        "scene": "overworld-flight",
        "route": workload.WORKLOAD_ID,
        "terrain": "vanilla-seed-20260929",
    }
    bundle["controls"].update(
        dimension="overworld", game_mode="creative", weather="clear", time="noon"
    )
    route = workload.REFERENCE["route"]
    world = {
        "minecraft_version": "26.3",
        "data_version": 5023,
        "seed": 20260929,
        "generator": "net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator",
        "noise_settings": "minecraft:overworld",
        "biome_source": "net.minecraft.world.level.biome.MultiNoiseBiomeSource",
        "biome_preset_overworld": True,
        "structures": True,
        "bonus_chest": False,
        "datapacks": ["vanilla"],
        "terrain": copy.deepcopy(workload.REFERENCE["terrain"]),
    }
    for name, run in bundle["runs"].items():
        run["intervals_ms"] = [10.0] * 2100
        run["metrics"] = analyze(run["intervals_ms"])
        run["route_receipt"] = {
            "workload_id": workload.WORKLOAD_ID,
            "world": copy.deepcopy(world),
            "settings": {"fov": 70, "fov_effect_scale": 0, "flying_speed": 0.05},
            "warmup": {
                "seconds": 30,
                "ticks": 600,
                "samples": [
                    {
                        "t": i,
                        "position": route["start"],
                        "flying": True,
                        "focused": True,
                        "paused": False,
                        "environment": {
                            "dimension": "minecraft:overworld",
                            "day_ticks": 6000,
                            "raining": False,
                            "thundering": False,
                        },
                    }
                    for i in range(31)
                ],
            },
            "samples": [
                {
                    "t": point["tick"] / 20,
                    "tick": point["tick"],
                    "game_tick": point["tick"],
                    "position": list(point["position"]),
                    "yaw": point.get("yaw", route["yaw"]),
                    "pitch": point.get("pitch", route["pitch"]),
                    "flying": True,
                    "focused": True,
                    "paused": False,
                    "environment": {
                        "dimension": "minecraft:overworld",
                        "day_ticks": 6000,
                        "raining": False,
                        "thundering": False,
                    },
                    "framebuffer": bundle["metadata"][name]["settings"]["resolution"],
                }
                for point in route["samples"]
            ],
            "csv_sha256": run["csv_sha256"],
        }
    return seal(bundle)
