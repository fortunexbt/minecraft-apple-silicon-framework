"""Finite, auditable settings search. A proposal is not a measured improvement."""

from .measure import validate, comparable

SETTING_CONTEXT = (
    ("renderDistance", "render_distance"),
    ("simulationDistance", "simulation_distance"),
)


def start(
    scenes,
    target_fps=85,
    max_trials=4,
    min_scale=0.65,
    min_render_distance=12,
    objective="performance",
    max_scale=1.0,
    max_render_distance=24,
):
    if not scenes or len(set(scenes)) != len(scenes):
        raise ValueError("Choose unique representative scenes")
    if not 1 <= max_trials <= 6 or not 30 <= target_fps <= 120:
        raise ValueError("Budget 1–6 trials; target 30–120 FPS")
    if type(min_scale) not in (int, float) or not 0.5 <= min_scale <= 1:
        raise ValueError("Minimum scale must be 0.5–1.0")
    if type(min_render_distance) is not int or not 12 <= min_render_distance <= 64:
        raise ValueError("Minimum view distance must be 12–64")
    if objective not in ("performance", "quality"):
        raise ValueError("Objective must be performance or quality")
    if type(max_scale) not in (int, float) or not min_scale <= max_scale <= 1:
        raise ValueError("Maximum scale must be between minimum scale and 1.0")
    if (
        type(max_render_distance) is not int
        or not min_render_distance <= max_render_distance <= 64
    ):
        raise ValueError(
            "Maximum view distance must be between minimum distance and 64"
        )
    return dict(
        format=2,
        objective=objective,
        max_scale=max_scale,
        max_render_distance=max_render_distance,
        min_scale=min_scale,
        min_render_distance=min_render_distance,
        scenes=scenes,
        target_fps=target_fps,
        max_trials=max_trials,
        trials=0,
        plateau=0,
        captures={},
        winner="baseline",
        pending=None,
        stopped=False,
        reason=None,
        decisions=[],
    )


def get_suite(state, profile):
    rows = state["captures"].get(profile, {})
    return (
        [rows[s] for s in state["scenes"]]
        if set(rows) == set(state["scenes"])
        else None
    )


def _good(state, suite):
    return all(
        c["metrics"]["worst_5s_fps"] >= state["target_fps"]
        and c["metrics"]["over_33"]["count"] == 0
        and c["metrics"]["local_outliers"]["count"] == 0
        for c in suite
    )


def submit(state, capture):
    if state["stopped"]:
        raise ValueError("Loop stopped; preserve winner and finish daily check")
    errors = validate(capture)
    if errors:
        raise ValueError("; ".join(errors))
    distance = capture["observed"].get("render_distance")
    if type(distance) is not int or distance < state.get("min_render_distance", 12):
        raise ValueError("Capture is below the session view-distance floor")
    if capture["observed"]["scale"] < state.get("min_scale", 0.65):
        raise ValueError("Capture is below the session resolution floor")
    profile = capture.get("profile", "baseline")
    scene = capture["observed"]["scene"]
    if (
        state.get("instance_id")
        and capture["observed"]["instance"] != state["instance_id"]
    ):
        raise ValueError("Capture instance differs from session")
    if scene not in state["scenes"]:
        raise ValueError("Scene not in this session")
    if any(
        c["id"] == capture["id"]
        for rows in state["captures"].values()
        for c in rows.values()
    ):
        raise ValueError("Capture ID already used")
    if profile == "baseline":
        if state["trials"]:
            raise ValueError("Baseline is frozen after trials begin")
        baseline = state.get("baseline_profile")
        if baseline:
            for setting, context in SETTING_CONTEXT:
                if (
                    setting in baseline.get("options", {})
                    and capture["observed"][context] != baseline["options"][setting]
                ):
                    raise ValueError("Baseline settings mismatch")
            if baseline.get("scale") != capture["observed"]["scale"]:
                raise ValueError("Baseline scale mismatch")
    elif not state["pending"] or state["pending"]["id"] != profile:
        raise ValueError("Capture does not match pending proposal")
    if scene in state["captures"].get(profile, {}):
        raise ValueError("Scene already recorded; do not overwrite evidence")
    if profile != "baseline":
        incumbent = state["captures"][state["winner"]][scene]
        mismatch = comparable(incumbent, capture)
        if mismatch:
            raise ValueError("Unmatched comparison: " + ", ".join(mismatch))
        planned = state["pending"]["profile"]
        if capture["observed"]["scale"] != planned["scale"]:
            raise ValueError("Capture scale differs from proposed profile")
        for setting, context in SETTING_CONTEXT:
            if (
                setting in planned.get("options", {})
                and capture["observed"].get(context) != planned["options"][setting]
            ):
                raise ValueError("Capture differs from proposed " + setting)
    state["captures"].setdefault(profile, {})[scene] = capture
    suite = get_suite(state, profile)
    if not suite:
        return state
    if profile == "baseline":
        state["decisions"].append(
            {"profile": profile, "decision": "baseline validated"}
        )
        if state.get("objective") == "quality":
            if not _good(state, suite):
                state.update(
                    stopped=True,
                    reason="Baseline has no verified headroom for quality upgrades",
                )
        elif _good(state, suite):
            state.update(stopped=True, reason="Baseline already meets chosen tradeoff")
        return state
    old = get_suite(state, state["winner"])
    gain = (
        min(c["metrics"]["worst_5s_fps"] for c in suite)
        / min(c["metrics"]["worst_5s_fps"] for c in old)
        - 1
    )
    # No scene may regress pacing materially or acquire new absolute long intervals.
    pacing = all(
        n["metrics"]["p95_ms"] <= o["metrics"]["p95_ms"] * 1.05
        and n["metrics"]["worst_5s_fps"] >= o["metrics"]["worst_5s_fps"] * 0.97
        and all(
            n["metrics"][f"over_{t}"]["count"] <= o["metrics"][f"over_{t}"]["count"]
            for t in (33, 50, 100)
        )
        and n["metrics"]["local_outliers"]["count"]
        <= o["metrics"]["local_outliers"]["count"]
        for n, o in zip(suite, old)
    )
    quality_gain = False
    if state.get("objective") == "quality":
        previous = state.get("winner_profile", state["baseline_profile"])
        candidate = state["pending"]["profile"]
        quality_gain = (
            (
                candidate["scale"] > previous["scale"]
                or candidate["options"]["renderDistance"]
                > previous["options"]["renderDistance"]
            )
            and candidate["scale"] >= previous["scale"]
            and candidate["options"]["renderDistance"]
            >= previous["options"]["renderDistance"]
        )
        pacing = _good(state, suite) and all(
            c["metrics"]["p95_ms"] <= 1000 / state["target_fps"] for c in suite
        )
        won = quality_gain and pacing
    else:
        won = gain >= 0.05 and pacing
    state["decisions"].append(
        {
            "profile": profile,
            "decision": "retain" if won else "reject",
            "worst_scene_gain": gain,
            "pacing_passed": pacing,
            "quality_gain": quality_gain,
            "visual_gate": "passed by supplied reviewer; subjective quality remains a user decision",
        }
    )
    if won:
        state.update(
            winner=profile, plateau=0, winner_profile=state["pending"]["profile"]
        )
    else:
        state["plateau"] += 1
    state["pending"] = None
    if state.get("objective", "performance") == "performance" and _good(
        state, get_suite(state, state["winner"])
    ):
        state.update(stopped=True, reason="Chosen tradeoff met")
    elif state["trials"] >= state["max_trials"]:
        state.update(stopped=True, reason="Trial budget exhausted")
    elif state["plateau"] >= 2:
        state.update(stopped=True, reason="Two material candidates failed to improve")
    return state


def propose(state, base_profile):
    if state["stopped"]:
        raise ValueError("Loop stopped: " + state["reason"])
    if state["pending"]:
        return state["pending"]
    if not get_suite(state, "baseline"):
        raise ValueError("Validate every baseline scene before proposing changes")
    if state["trials"] >= state["max_trials"]:
        raise ValueError("Budget exhausted")
    # Recursion starts from the retained winner, never from a losing profile.
    import copy

    profile = copy.deepcopy(
        state.get("winner_profile", state.get("baseline_profile", base_profile))
    )
    if "baseline_profile" not in state:
        state["baseline_profile"] = copy.deepcopy(base_profile)
    opts = profile.setdefault("options", {})
    if not isinstance(profile.get("scale"), (int, float)):
        raise ValueError("Readable static scaling config required")
    min_scale = state.get("min_scale", 0.65)
    min_distance = state.get("min_render_distance", 12)
    if profile["scale"] < min_scale or opts.get("renderDistance", 0) < min_distance:
        raise ValueError("Base profile is below the session quality floors")
    candidates = []
    if state.get("objective") == "quality":
        if profile["scale"] < state["max_scale"]:
            p = copy.deepcopy(profile)
            p["scale"] = min(state["max_scale"], round(profile["scale"] + 0.05, 2))
            if "irisScale" in p.get("scale_options", {}):
                p["scale_options"]["irisScale"] = p["scale"]
            candidates.append(
                (
                    f"Increase internal scale to {p['scale']:g}; retain only with gameplay headroom",
                    p,
                )
            )
        if opts["renderDistance"] < state["max_render_distance"]:
            p = copy.deepcopy(profile)
            p["options"]["renderDistance"] = min(
                state["max_render_distance"], opts["renderDistance"] + 2
            )
            candidates.append(
                (
                    f"Extend view distance to {p['options']['renderDistance']}; retain only with gameplay headroom",
                    p,
                )
            )
    if (
        state.get("objective", "performance") == "performance"
        and opts.get("simulationDistance", 8) > 6
    ):
        p = copy.deepcopy(profile)
        p["options"]["simulationDistance"] = 6
        candidates.append(
            ("Reduce simulation distance to 6 while preserving view distance", p)
        )
    if (
        state.get("objective", "performance") == "performance"
        and opts.get("renderDistance", 12) > min_distance
    ):
        p = copy.deepcopy(profile)
        p["options"]["renderDistance"] = max(min_distance, opts["renderDistance"] - 4)
        candidates.append(
            (
                f"Reduce view distance from {opts['renderDistance']} to {p['options']['renderDistance']}",
                p,
            )
        )
    if (
        state.get("objective", "performance") == "performance"
        and profile["scale"] > min_scale
    ):
        p = copy.deepcopy(profile)
        p["scale"] = max(min_scale, round(profile["scale"] - 0.05, 2))
        if "irisScale" in p.get("scale_options", {}):
            p["scale_options"]["irisScale"] = p["scale"]
        candidates.append(
            (
                f"Try internal scale {profile['scale']:g} → {p['scale']:g}; review crispness",
                p,
            )
        )
    used = [d.get("profile_settings") for d in state["decisions"]]
    remaining = [c for c in candidates if c[1] not in used]
    if not remaining:
        state.update(
            stopped=True,
            reason="No untested material settings candidate within quality floor",
        )
        return None
    reason, profile = remaining[0]
    state["trials"] += 1
    pending = {
        "id": "trial-" + str(state["trials"]),
        "profile": profile,
        "hypothesis": reason,
    }
    state["pending"] = pending
    state["decisions"].append(
        {
            "profile": pending["id"],
            "decision": "proposed",
            "hypothesis": reason,
            "profile_settings": copy.deepcopy(profile),
        }
    )
    return pending
