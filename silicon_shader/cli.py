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
from . import capture, loop


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
        description="Shader quality first. Short measurements. A finite path to a daily instance.",
    )
    s = p.add_subparsers(dest="cmd", required=True)
    d = s.add_parser("discover", help="Read hardware and Prism metadata")
    d.add_argument("--prism")
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
        if action in ("propose", "sync"):
            a.add_argument("instance")
            a.add_argument("--closed", action="store_true")
        if action == "submit":
            a.add_argument("capture")
        if action == "stop":
            a.add_argument("--reason", required=True)
    return p


def run(args):
    if args.cmd == "discover":
        return discover(args.prism)
    if args.cmd == "runtime":
        return inspect_runtime(args.executable, args.minecraft)
    if args.cmd == "setup":
        return setup(args.destination, args.minecraft, args.fabric)
    if args.cmd == "isolate":
        return {
            "instance": str(
                isolate(args.source, args.destination, args.closed, args.save)
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
        return {
            "instance": str(
                daily(args.source, args.destination, args.closed, args.save)
            ),
            "status": "clean copy; normal gameplay, controls and save/reload remain unverified",
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
            state = loop.start(args.scenes, args.target_fps, args.max_trials)
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
