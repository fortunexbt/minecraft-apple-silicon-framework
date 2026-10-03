"""The public CLI. JSON on stdout; actionable errors on stderr."""

import argparse
import json
from pathlib import Path
import sys
from .common import read, write
from .discover import discover, java_requirement, inspect_runtime
from .instances import (
    isolate,
    daily,
    apply_profile,
    rollback,
    current_profile,
    managed,
    closed,
)
from . import capture, loop, challenge, community, catalog
from .doctor import doctor


def emit(value):
    print(json.dumps(value, indent=2, allow_nan=False, default=str))


def setup(destination, mc, fabric):
    import re

    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", mc) or not re.fullmatch(
        r"[0-9.]{1,32}", fabric
    ):
        raise ValueError("Invalid version identifier")
    p = Path(destination).expanduser().absolute()
    if p.exists() or p.is_symlink():
        raise ValueError("Destination must not exist")
    if not p.parent.is_dir():
        raise ValueError("Destination parent must exist")
    java = java_requirement(mc)
    if java is None:
        raise ValueError(
            "Unknown Minecraft Java requirement; create through Prism and use isolate"
        )
    p.mkdir()
    write(
        p / "mmc-pack.json",
        {
            "formatVersion": 1,
            "components": [
                {"uid": "net.minecraft", "version": mc, "important": True},
                {"uid": "net.fabricmc.fabric-loader", "version": fabric},
            ],
        },
    )
    (p / "instance.cfg").write_text(
        f"[General]\nname={p.name}\nInstanceType=OneSix\nOverrideMemory=true\nMinMemAlloc=512\nMaxMemAlloc=4096\nOverrideCommands=true\nPreLaunchCommand=\nPostExitCommand=\nWrapperCommand=\nOverrideJavaArgs=true\nJvmArgs=\n"
    )
    (p / ".minecraft").mkdir()
    write(
        p / ".silicon-shader/instance.json",
        {
            "format": 1,
            "root": str(p.resolve()),
            "source": None,
            "game_dir": ".minecraft",
            "kind": "lab",
            "save_copied": None,
        },
    )
    return {
        "instance": str(p),
        "java_required": java,
        "next": [
            "In Prism, refresh/restart the instance list and select ARM64 Java "
            + str(java),
            "Install compatible Sodium, Iris and a shader through Prism; open their license pages",
            "Launch normally once; choose your own world and settings, then close before configuration changes",
        ],
        "performance": "Not launched or measured; these are instance metadata only",
    }


def parser():
    p = argparse.ArgumentParser(
        prog="silicon-shader",
        description="Find, try and share Minecraft shader setups for your Mac.",
        epilog="Start: discover → doctor INSTANCE → challenge find --this-mac. Use COMMAND --help for details.",
    )
    s = p.add_subparsers(dest="cmd", required=True)
    d = s.add_parser(
        "discover", help="Read Mac hardware, game instances and public player profiles"
    )
    d.add_argument("--prism")
    q = s.add_parser(
        "doctor",
        help="Inspect game settings, mods and missing measurement context",
    )
    q.add_argument("instance")
    q.add_argument(
        "--game-dir",
        action="store_true",
        help="Inspect a launcher-neutral game directory",
    )
    q = s.add_parser("setup", help="Create Prism metadata, no game downloads or launch")
    q.add_argument("destination")
    q.add_argument("--minecraft", required=True)
    q.add_argument("--fabric", required=True)
    q = s.add_parser("runtime", help="Verify an explicitly selected Java executable")
    q.add_argument("executable")
    q.add_argument("--minecraft", required=True)
    for name in ("isolate", "daily"):
        q = s.add_parser(name, help="Create a new copy without modifying the source")
        q.add_argument("source")
        q.add_argument("destination")
        q.add_argument("--closed", action="store_true")
        q.add_argument("--save", help="Exact save folder to copy, while closed")
        if name == "isolate":
            q.add_argument(
                "--game-dir",
                action="store_true",
                help="Copy a launcher-neutral game directory",
            )
        if name == "daily":
            q.add_argument(
                "--session",
                help="Stopped optimization session; winner must be applied first",
            )
    q = s.add_parser(
        "profile", help="Read, apply or roll back settings in an isolated instance"
    )
    sub = q.add_subparsers(dest="action", required=True)
    a = sub.add_parser("show")
    a.add_argument("instance")
    a = sub.add_parser("apply")
    a.add_argument("instance")
    a.add_argument("profile")
    a.add_argument("--closed", action="store_true")
    a = sub.add_parser("rollback")
    a.add_argument("instance")
    a.add_argument("receipt")
    a.add_argument("--closed", action="store_true")
    q = s.add_parser("capture", help="Request, inspect or import sampler measurements")
    sub = q.add_subparsers(dest="action", required=True)
    for action in ("request", "status", "import"):
        a = sub.add_parser(action)
        a.add_argument("root")
        a.add_argument("id")
        if action == "request":
            a.add_argument("--seconds", type=int, default=20)
            a.add_argument(
                "--delay",
                type=float,
                default=0,
                help="Wait 0–10 seconds before requesting; return focus to the game",
            )
        if action == "status":
            a.add_argument("--wait", type=int, default=0)
        if action == "import":
            a.add_argument("manifest")
            a.add_argument("--profile", default="baseline")
            a.add_argument("--out", required=True)
    q = s.add_parser(
        "loop", help="Bounded search; no automated UI, launching or unlimited retries"
    )
    sub = q.add_subparsers(dest="action", required=True)
    for action in ("start", "propose", "submit", "sync", "status", "stop"):
        a = sub.add_parser(action)
        a.add_argument("session")
        if action == "start":
            a.add_argument("instance")
            a.add_argument(
                "--scenes",
                nargs="+",
                default=["loaded", "water", "village", "nether", "end"],
            )
            a.add_argument("--target-fps", type=float, default=85)
            a.add_argument("--max-trials", type=int, default=4)
            a.add_argument(
                "--objective", choices=("performance", "quality"), default="performance"
            )
            a.add_argument("--max-scale", type=float, default=1.0)
            a.add_argument("--max-render-distance", type=int, default=24)
            a.add_argument("--min-scale", type=float, default=0.65)
            a.add_argument("--min-render-distance", type=int, default=12)
        if action in ("propose", "sync"):
            a.add_argument("instance")
            a.add_argument("--closed", action="store_true")
        if action == "submit":
            a.add_argument("capture")
        if action == "stop":
            a.add_argument("--reason", required=True)
    q = s.add_parser("challenge", help="Optional community evidence and publication")
    sub = q.add_subparsers(dest="action", required=True)
    sub.add_parser("show")
    sub.add_parser("workload", help="Print the pinned standard benchmark route")
    a = sub.add_parser(
        "route-receipt",
        help="Validate and export the standard adapter's route observations",
    )
    a.add_argument("root")
    a.add_argument("id")
    a.add_argument("--out", required=True)
    a = sub.add_parser("find", help="Find shared setups for your Mac")
    a.add_argument(
        "--this-mac",
        action="store_true",
        help="Detect this Mac and prefer matching setups",
    )
    a.add_argument(
        "--include-earlier",
        action="store_true",
        help="Return earlier-route recipes separately; their FPS is not comparable",
    )
    a.add_argument("--minecraft", help="Only this Minecraft version")
    a.add_argument("--loader", help="Only this loader, e.g. fabric")
    a.add_argument("--chip", help="Chip family, e.g. M6 or A18")
    a.add_argument("--tier", choices=("base", "pro", "max", "ultra"))
    a.add_argument("--ram", type=int, help="Memory in GiB")
    a.add_argument("--sort", choices=("pacing", "fps", "distance"), default="pacing")
    a.add_argument("--limit", type=int, default=5)
    a = sub.add_parser("prepare", help="Build standard-route v2 evidence")
    for field in (
        "baseline_capture",
        "candidate_capture",
        "baseline_csv",
        "candidate_csv",
        "metadata",
    ):
        a.add_argument(field)
    a.add_argument("--out", required=True)
    a.add_argument(
        "--baseline-route",
        required=True,
        help="JSON route receipt captured with the baseline run",
    )
    a.add_argument(
        "--candidate-route",
        required=True,
        help="JSON route receipt captured with the candidate run",
    )
    for action in ("validate", "submit"):
        a = sub.add_parser(action)
        a.add_argument("bundle")
        if action == "submit":
            a.add_argument(
                "--presentation",
                help="JSON containing title, minecraft_profile, agent (model and harness), screenshot_url and recipe_url",
            )
            a.add_argument("--publish", action="store_true")
            a.add_argument("--reviewed-digest")
    a = sub.add_parser("status")
    a.add_argument("digest", help="Bundle file or full submission digest")
    s.add_parser("skill", help="Print the bundled portable agent skill")
    q = s.add_parser(
        "install-skill", help="Install skill into an explicit agent skill directory"
    )
    q.add_argument("--destination", required=True)
    return p


def run(args):
    if args.cmd in ("skill", "install-skill"):
        from importlib.resources import files

        text = (
            files("silicon_shader")
            .joinpath("skills/silicon-shader/SKILL.md")
            .read_text()
        )
        if args.cmd == "skill":
            return {"name": "silicon-shader", "markdown": text}
        destination = Path(args.destination).expanduser().absolute()
        if any(p.is_symlink() for p in [destination, *destination.parents]):
            raise ValueError("Skill destination must not traverse a symlink")
        target = destination / "SKILL.md"
        if destination.exists():
            if (
                target.is_file()
                and not target.is_symlink()
                and target.read_text() == text
            ):
                return {"path": str(target), "status": "already installed"}
            raise ValueError("Destination exists; inspect it and choose a new path")
        destination.mkdir(parents=True)
        target.write_text(text)
        return {"path": str(target), "status": "installed"}
    if args.cmd == "challenge":
        if args.action == "show":
            return community.contract()
        if args.action == "workload":
            from .workload import contract

            return contract()
        if args.action == "route-receipt":
            from .workload import import_route

            if Path(args.out).exists():
                raise ValueError("Output exists; choose a new path")
            result = import_route(args.root, args.id)
            write(args.out, result)
            return {
                "path": args.out,
                "workload_id": result["workload_id"],
                "status": "route checked; self-reported",
            }
        if args.action == "find":
            return catalog.find(
                chip=args.chip,
                tier=args.tier,
                ram=args.ram,
                sort=args.sort,
                limit=args.limit,
                this_mac=args.this_mac,
                include_earlier=args.include_earlier,
                minecraft=args.minecraft,
                loader=args.loader,
            )
        if args.action == "prepare":
            if Path(args.out).exists():
                raise ValueError("Bundle output exists; choose a new path")
            result = challenge.prepare(
                args.baseline_capture,
                args.candidate_capture,
                args.baseline_csv,
                args.candidate_csv,
                args.metadata,
                args.baseline_route,
                args.candidate_route,
            )
            write(args.out, result)
            return {
                "path": args.out,
                "digest": result["content_digest"],
                "status": "self_reported; unpublished",
            }
        if args.action == "status":
            identifier = (
                community.load_bundle(args.digest)["content_digest"]
                if Path(args.digest).is_file()
                else args.digest
            )
            return community.status(identifier)
        bundle = community.load_bundle(args.bundle)
        if args.action == "validate":
            return {
                "valid": True,
                "status": "self_reported",
                "digest": bundle["content_digest"],
            }
        from .workload import require_standard

        # CLI submit is the new-contribution path. V1 remains readable through
        # validate and in the public registry, but cannot enter as new evidence.
        require_standard(bundle)
        if args.publish and not args.presentation:
            raise ValueError(
                "Add --presentation setup.json with a Minecraft profile, agent credits, screenshot and recipe before publishing"
            )
        presentation = read(args.presentation) if args.presentation else None
        result = community.submit(
            bundle, args.publish, args.reviewed_digest, presentation=presentation
        )
        if not args.publish:
            result["bundle_file"] = str(Path(args.bundle).expanduser())
        return result
    if args.cmd == "discover":
        return discover(args.prism)
    if args.cmd == "doctor":
        return doctor(args.instance, args.game_dir)
    if args.cmd == "runtime":
        return inspect_runtime(args.executable, args.minecraft)
    if args.cmd == "setup":
        return setup(args.destination, args.minecraft, args.fabric)
    if args.cmd == "isolate":
        return {
            "instance": str(
                isolate(
                    args.source, args.destination, args.closed, args.save, args.game_dir
                )
            ),
            "status": "isolated; unmeasured",
        }
    if args.cmd == "daily":
        if args.session:
            state = read(args.session)
            if str(Path(args.source).resolve()) != state.get("instance_path"):
                raise ValueError(
                    "Daily source differs from the measured session instance"
                )
            if not state["stopped"] or not loop.get_suite(state, state["winner"]):
                raise ValueError("Session is not finished with a validated winner")
            profile = state.get("winner_profile", state.get("baseline_profile"))
            if profile is None or current_profile(args.source) != profile:
                raise ValueError(
                    "Apply retained winner with loop sync before daily copy"
                )
        result = daily(args.source, args.destination, args.closed, args.save)
        _, meta = managed(result)
        return {
            "instance": str(result),
            "launcher_cleanup_required": meta.get("launcher_cleanup_required", False),
            "status": "copied game files; inspect external launcher JVM arguments and hooks before normal gameplay"
            if meta.get("launcher_cleanup_required")
            else "clean copy; normal gameplay, controls and save/reload remain unverified",
        }
    if args.cmd == "profile":
        if args.action == "show":
            return current_profile(args.instance)
        if args.action == "apply":
            return apply_profile(args.instance, read(args.profile), args.closed)
        return rollback(args.instance, args.receipt, args.closed)
    if args.cmd == "capture":
        if args.action == "request":
            return capture.request(args.root, args.id, args.seconds, args.delay)
        if args.action == "status":
            return capture.status(args.root, args.id, args.wait)
        if Path(args.out).exists():
            raise ValueError("Capture output exists; evidence is immutable")
        result = capture.import_capture(
            args.root, args.id, read(args.manifest), args.profile
        )
        write(args.out, result)
        return result
    if args.cmd == "loop":
        p = Path(args.session)
        if args.action == "start":
            if p.exists():
                raise ValueError("Session already exists")
            instance, _ = managed(args.instance)
            baseline = current_profile(instance)
            if baseline.get("scale_options", {}).get("targetFrameRate") != 0:
                raise ValueError(
                    "Verify static scaling (targetFrameRate=0) before starting a session"
                )
            if baseline.get("scale_options", {}).get(
                "irisScale", baseline.get("scale")
            ) != baseline.get("scale"):
                raise ValueError("Game and Iris scale must match before measurement")
            state = loop.start(
                args.scenes,
                args.target_fps,
                args.max_trials,
                args.min_scale,
                args.min_render_distance,
                args.objective,
                args.max_scale,
                args.max_render_distance,
            )
            if (
                baseline.get("scale", 0) < args.min_scale
                or baseline["options"].get("renderDistance", 0)
                < args.min_render_distance
            ):
                raise ValueError("Baseline is below your chosen quality floors")
            state.update(
                instance_id=instance.name,
                instance_path=str(instance),
                baseline_profile=baseline,
            )
            write(p, state)
            return state
        state = read(p)
        if args.action == "status":
            return state
        if args.action == "propose":
            instance, _ = managed(args.instance)
            closed(instance, args.closed)
            if state.get("instance_path") != str(instance):
                raise ValueError("Session belongs to a different isolated instance")
            original = current_profile(instance)
            if state.get("pending", {}) and state["pending"].get("receipt"):
                if original != state["pending"]["profile"]:
                    raise ValueError(
                        "Pending profile changed; inspect its receipt before proceeding"
                    )
                return state["pending"]
            # Store baseline before application, including when it already meets the goal.
            state.setdefault("baseline_profile", original)
            result = loop.propose(state, original)
            if result:
                receipt = apply_profile(instance, result["profile"], args.closed)
                result["receipt"] = receipt["id"]
            write(p, state)
            return result or state
        if args.action == "sync":
            if str(Path(args.instance).resolve()) != state.get("instance_path"):
                raise ValueError("Session instance mismatch")
            if not loop.get_suite(state, state["winner"]):
                raise ValueError("Winner suite incomplete")
            profile = state.get("winner_profile", state.get("baseline_profile"))
            if profile is None:
                raise ValueError(
                    "No recorded baseline settings; save baseline profile before measuring"
                )
            return apply_profile(args.instance, profile, args.closed)
        if args.action == "submit":
            try:
                loop.submit(state, read(args.capture))
            except ValueError as e:
                state.setdefault("invalid_attempts", []).append(str(e))
                if len(state["invalid_attempts"]) >= 2:
                    state.update(
                        stopped=True,
                        reason="Two invalid submissions; inspect capture conditions before a new session",
                    )
                write(p, state)
                raise
        if args.action == "stop":
            if not loop.get_suite(state, state["winner"]):
                raise ValueError("Cannot retain an incomplete baseline")
            state.update(stopped=True, reason=args.reason)
        write(p, state)
        return state


def main():
    try:
        emit(run(parser().parse_args()))
    except (ValueError, KeyError, TypeError, OSError) as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
