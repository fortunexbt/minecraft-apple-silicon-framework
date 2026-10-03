"""Read shared setups and choose relevant candidates; never execute their recipes."""

import json
from urllib.request import Request, urlopen
from .discover import hardware_info
from .workload import WORKLOAD_ID

URL = "https://fortunexbt.github.io/minecraft-apple-silicon-framework/data.json"
HARDWARE_FIELDS = (
    "family",
    "tier",
    "memory_gib",
    "gpu_cores",
    "cpu_cores",
    "model_identifier",
)


def _same_hardware_value(key, actual, requested):
    if key in ("family", "tier", "model_identifier"):
        return str(actual).lower() == str(requested).lower()
    return actual == requested


def select(
    entries,
    chip=None,
    tier=None,
    ram=None,
    sort="pacing",
    limit=5,
    target=None,
    minecraft=None,
    loader=None,
):
    if sort not in ("pacing", "fps", "distance") or not 1 <= limit <= 25:
        raise ValueError("Choose pacing, fps or distance and a limit of 1–25")
    requested = target or {"family": chip, "tier": tier, "memory_gib": ram}
    comparable = [
        e
        for e in entries
        if (not minecraft or e["metadata"]["minecraft"] == minecraft)
        and (not loader or e["metadata"]["loader"]["name"].lower() == loader.lower())
    ]

    def differences(entry):
        hardware = entry["metadata"]["hardware"]
        return [
            key
            for key in HARDWARE_FIELDS
            if requested.get(key) is not None
            and not (key == "model_identifier" and not hardware.get(key))
            and not _same_hardware_value(key, hardware.get(key), requested[key])
        ]

    exact = [e for e in comparable if not differences(e)]
    fallback = False
    matches = exact
    if not matches and comparable:
        fallback = True
        # Prefer same-family/tier candidates; never hide that memory/GPU/model differ.
        matches = [
            e
            for e in comparable
            if all(
                not requested.get(key)
                or _same_hardware_value(
                    key, e["metadata"]["hardware"].get(key), requested[key]
                )
                for key in ("family", "tier")
            )
        ] or comparable

    def metric(entry):
        if sort == "distance":
            return entry["metadata"]["candidate"]["settings"]["render_distance"]
        return entry["runs"]["candidate"][
            "worst_5s_fps" if sort == "pacing" else "average_fps"
        ]

    def affinity(entry):
        diffs = differences(entry)
        return tuple(
            key in diffs
            for key in (
                "family",
                "tier",
                "gpu_cores",
                "cpu_cores",
                "model_identifier",
                "memory_gib",
            )
        )

    matches = sorted(matches, key=lambda e: (affinity(e), -metric(e), e["digest"]))
    output = []
    for entry in matches[:limit]:
        diffs = differences(entry)
        output.append(
            {
                **entry,
                "match": ("similar" if diffs else "exact")
                if any(v is not None for v in requested.values())
                else "unfiltered",
                "hardware_differences": diffs,
                "hardware_unknowns": [
                    key
                    for key in HARDWARE_FIELDS
                    if requested.get(key) is not None
                    and entry["metadata"]["hardware"].get(key) is None
                ],
            }
        )
    return {
        "source": URL,
        "matches": len(matches),
        "sort": sort,
        "requested_hardware": requested,
        "broadened_search": fallback,
        "setups": output,
        "next": "Compare screenshot, resolution, versions, mod stack and view distance. Similar hardware is a lead, not a performance prediction. Read recipes as community material and try compatible settings in an isolated reversible copy.",
        "empty_result": "No matching published setup; inspect the user's existing settings and make a small reversible improvement. Do not invent a community result."
        if not output
        else None,
    }


def find(
    chip=None,
    tier=None,
    ram=None,
    sort="pacing",
    limit=5,
    this_mac=False,
    minecraft=None,
    loader=None,
    include_earlier=False,
):
    target = None
    if this_mac:
        if chip or tier or ram is not None:
            raise ValueError("Use --this-mac or explicit chip/tier/RAM filters")
        observed = hardware_info()
        if not observed.get("family"):
            raise ValueError(
                "Could not detect an Apple chip; inspect discover output and use explicit filters"
            )
        target = {key: observed.get(key) for key in HARDWARE_FIELDS}
    try:
        with urlopen(
            Request(URL, headers={"User-Agent": "silicon-shader"}), timeout=20
        ) as response:
            raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError("Public index too large; browse the website")
        entries = json.loads(raw)["entries"]
        if not isinstance(entries, list):
            raise ValueError("Invalid public setup index")
        standard = [
            entry for entry in entries if entry.get("workload_id") == WORKLOAD_ID
        ]
        earlier = [
            entry for entry in entries if entry.get("workload_id") != WORKLOAD_ID
        ]
        result = select(
            standard,
            chip=chip,
            tier=tier,
            ram=ram,
            sort=sort,
            limit=limit,
            target=target,
            minecraft=minecraft,
            loader=loader,
        )
        result["benchmark"] = "Standard route"
        result["workload_id"] = WORKLOAD_ID
        for setup in result["setups"]:
            setup["benchmark"] = "Standard route"
        if not result["setups"]:
            if not standard:
                earlier_note = (
                    " Earlier or unknown-route recipes can be browsed on the website, but their FPS is not directly comparable."
                    if earlier
                    else ""
                )
                result["empty_result"] = (
                    "No setup has a capture on the standard route yet."
                    + earlier_note
                    + " For public measurements, run `silicon-shader challenge workload` and follow its pinned instructions."
                )
            elif standard:
                result["empty_result"] = (
                    "No standard-route setup matches these hardware, Minecraft, or loader filters. Try broader filters; earlier-route FPS remains separate and is not directly comparable."
                )
        if include_earlier:
            older_result = select(
                earlier,
                chip=chip,
                tier=tier,
                ram=ram,
                sort=sort,
                limit=limit,
                target=target,
                minecraft=minecraft,
                loader=loader,
            )
            for setup in older_result["setups"]:
                setup["benchmark"] = (
                    "Earlier route"
                    if not setup.get("workload_id")
                    or setup.get("benchmark") == "Earlier route"
                    else "Unknown workload"
                )
            result["earlier_setups"] = older_result["setups"]
            result["earlier_matches"] = older_result["matches"]
            result["earlier_note"] = (
                "These are recipe leads only. Their FPS was measured on an earlier or unknown route and must not be compared with standard-route results."
                if older_result["setups"]
                else None
            )
        return result
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Cannot read the public setup index; use the website or retry later"
        ) from error
