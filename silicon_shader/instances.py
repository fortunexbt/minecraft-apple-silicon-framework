"""Explicit isolated copies and receipt-backed, reversible configuration changes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from .common import (
    contained,
    digest,
    no_links,
    properties,
    read,
    update_properties,
    write,
)
from .discover import instance_info

MARKER = ".silicon-shader/instance.json"
OPTIONS = {
    "renderDistance": (2, 64),
    "simulationDistance": (2, 32),
    "maxFps": (30, 260),
    "enableVsync": None,
    "fullscreen": None,
}


def closed(path, acknowledged):
    if not acknowledged:
        raise ValueError(
            "Close this instance and pass --closed; no live settings/world copies"
        )
    result = subprocess.run(
        ["ps", "-axo", "command="], capture_output=True, text=True, timeout=5
    )
    if result.returncode:
        raise ValueError("Cannot inspect process list; closed state is unverified")
    resolved = str(Path(path).resolve())
    for line in result.stdout.splitlines():
        if resolved in line and ("java " in line or "/java " in line):
            raise ValueError("A Java process references this instance; close it first")


def managed(path):
    p = Path(path).resolve()
    no_links(p)
    if not (p / MARKER).is_file():
        raise ValueError("Writes require an isolated managed instance")
    meta = read(p / MARKER)
    if meta.get("root") != str(p):
        raise ValueError("Managed instance moved: isolate it again at its new location")
    return p, meta


def game_dir(path):
    if (path / MARKER).is_file():
        return contained(path, read(path / MARKER)["game_dir"])
    return path / ".minecraft" if (path / ".minecraft").is_dir() else path / "minecraft"


def _clean_cfg(source, dest, name):
    values = properties(source / "instance.cfg")
    # Never inherit launch hooks, JVM agents, credentials, wrappers or global overrides.
    keys = (
        "InstanceType",
        "JavaPath",
        "OverrideJavaLocation",
        "OverrideJava",
        "MinMemAlloc",
        "MaxMemAlloc",
        "OverrideMemory",
        "PermGen",
    )
    safe = {k: v for k, v in values.items() if k in keys}
    safe.update(
        name=name,
        InstanceType=values.get("InstanceType", "OneSix"),
        OverrideCommands="true",
        PreLaunchCommand="",
        PostExitCommand="",
        WrapperCommand="",
        OverrideJavaArgs="true",
        JvmArgs="",
    )
    (dest / "instance.cfg").write_text(
        "[General]\n" + "".join(k + "=" + v + "\n" for k, v in safe.items())
    )


def isolate(source, destination, acknowledged=False, save=None, game_directory=False):
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    closed(source, acknowledged)
    no_links(source)
    info = {"game_dir": "."} if game_directory else instance_info(source)
    if game_directory and not (source / "options.txt").is_file():
        raise ValueError("Select the actual game directory containing options.txt")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination must not exist")
    if destination.resolve().is_relative_to(source):
        raise ValueError("Destination cannot be inside source")
    if not destination.parent.is_dir():
        raise ValueError("Destination parent must exist")
    prefix = "" if game_directory else info["game_dir"] + "/"
    paths = [] if game_directory else ["mmc-pack.json", "patches"]
    paths += [
        prefix + name
        for name in (
            "options.txt",
            "optionsshaders.txt",
            "optionsof.txt",
            "config",
            "mods",
            "shaderpacks",
            "resourcepacks",
        )
    ]
    if save:
        if Path(save).name != save or save in (".", ".."):
            raise ValueError("Use the exact save folder name")
        world = contained(source, prefix + "saves/" + save)
        if not (world / "level.dat").is_file():
            raise ValueError("Save folder has no level.dat")
        paths.append(prefix + "saves/" + save)
    for rel in paths:
        no_links(contained(source, rel))
    tmp = Path(tempfile.mkdtemp(prefix=".isolate-", dir=destination.parent))
    try:
        for rel in paths:
            src = contained(source, rel)
            dst = tmp / rel
            if not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        if not game_directory:
            _clean_cfg(source, tmp, destination.name)
        write(
            tmp / MARKER,
            {
                "format": 1,
                "root": str(destination.resolve()),
                "source": str(source),
                "game_dir": info["game_dir"],
                "save_copied": save,
                "kind": "lab",
                "layout": "game-directory" if game_directory else "prism",
                "launcher_cleanup_required": game_directory,
            },
        )
        # Source can be live-changed after acknowledgment: catch process appearance too.
        closed(source, acknowledged)
        os.rename(tmp, destination)
    except BaseException:
        shutil.rmtree(tmp)
        raise
    return destination


def current_profile(path, game_directory=False):
    game = Path(path) if game_directory else game_dir(Path(path))
    opts = properties(game / "options.txt", ":")
    result = {"options": {}}
    for key in OPTIONS:
        if key in opts:
            result["options"][key] = (
                opts[key] == "true" if OPTIONS[key] is None else int(opts[key])
            )
    scale = game / "config/renderscale.json5"
    if scale.exists():
        try:
            data = read(scale)
            result["scale"] = data["scale"]
            result["scale_options"] = {
                k: data[k]
                for k in ("irisScale", "forceLinear", "fsr", "targetFrameRate")
                if k in data
            }
        except (ValueError, KeyError):
            result["scale"] = None
    return result


def profile_changes(path, profile):
    if set(profile) - {"options", "scale", "scale_options", "shader_properties"}:
        raise ValueError("Unknown profile fields")
    changes = {}
    game = game_dir(path)
    opts = {}
    for key, value in profile.get("options", {}).items():
        if key not in OPTIONS:
            raise ValueError("Unsupported option " + key)
        bounds = OPTIONS[key]
        if bounds is None:
            if type(value) is not bool:
                raise ValueError(key + " must be boolean")
            opts[key] = str(value).lower()
        else:
            if type(value) is not int or not bounds[0] <= value <= bounds[1]:
                raise ValueError(key + " outside allowed range")
            opts[key] = str(value)
    if opts:
        changes[game / "options.txt"] = ("properties", opts, ":")
    if "scale_options" in profile and "scale" not in profile:
        raise ValueError("Scaler controls require an explicit scale")
    if "scale" in profile:
        scale = profile["scale"]
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not 0.5 <= scale <= 1
        ):
            raise ValueError("Static scale must be 0.5–1.0")
        f = game / "config/renderscale.json5"
        if not f.exists():
            raise ValueError(
                "No RenderScale config; install compatible mod through Prism first"
            )
        try:
            data = read(f)
        except ValueError:
            raise ValueError(
                "RenderScale JSON5 contains comments/extended syntax; normalize a copy to JSON first"
            )
        controls = profile.get("scale_options", {})
        if not isinstance(controls, dict) or set(controls) - {
            "irisScale",
            "forceLinear",
            "fsr",
            "targetFrameRate",
        }:
            raise ValueError("Unknown scaler controls")
        for key, value in controls.items():
            if key in ("forceLinear", "fsr") and type(value) is not bool:
                raise ValueError(key + " must be boolean")
            if key == "targetFrameRate" and (type(value) is not int or value != 0):
                raise ValueError(
                    "Only static scaling is supported; targetFrameRate must be zero"
                )
            if key == "irisScale" and (
                type(value) not in (int, float) or not 0.5 <= value <= 1
            ):
                raise ValueError("irisScale must be 0.5–1.0")
        data.update(scale=scale, irisScale=scale)
        data.update(controls)
        changes[f] = ("json", data, None)
    if "shader_properties" in profile:
        # Full profiles only: never reset all properties while changing one option.
        shader = properties(game / "config/iris.properties").get("shaderPack", "")
        if not shader or Path(shader).name != shader:
            raise ValueError("No safe selected Iris shader pack")
        f = game / "shaderpacks" / (shader + ".txt")
        existing = properties(f)
        supplied = profile["shader_properties"]
        if (
            not existing
            or not isinstance(supplied, dict)
            or not set(existing) <= set(supplied)
        ):
            raise ValueError("Supply the COMPLETE existing shader property set")
        if any(
            not isinstance(k, str) or "\n" in k or "=" in k or "\n" in str(v)
            for k, v in supplied.items()
        ):
            raise ValueError("Invalid shader properties")
        changes[f] = ("properties", supplied, "=")
    if not changes:
        raise ValueError("Empty profile")
    return changes


def apply_profile(path, profile, acknowledged=False):
    path, meta = managed(path)
    closed(path, acknowledged)
    changes = profile_changes(path, profile)
    rid = uuid.uuid4().hex[:12]
    backup = path / ".silicon-shader/history" / rid
    backup.mkdir(parents=True)
    receipt = {"id": rid, "profile": profile, "files": {}, "state": "preparing"}
    for f in changes:
        rel = str(f.relative_to(path))
        saved = backup / rel
        saved.parent.mkdir(parents=True, exist_ok=True)
        if f.exists():
            shutil.copy2(f, saved)
        receipt["files"][rel] = {"before": digest(f) if f.exists() else None}
    write(backup / "receipt.json", receipt)
    try:
        for f, (mode, value, sep) in changes.items():
            if mode == "json":
                write(f, value)
            else:
                update_properties(f, value, sep)
            receipt["files"][str(f.relative_to(path))]["after"] = digest(f)
        receipt["state"] = "applied"
        write(backup / "receipt.json", receipt)
    except BaseException:
        for rel, entry in receipt["files"].items():
            f = contained(path, rel)
            if entry["before"] is None:
                f.unlink(missing_ok=True)
            else:
                shutil.copy2(backup / rel, f)
        receipt["state"] = "reverted-after-error"
        write(backup / "receipt.json", receipt)
        raise
    return receipt


def _restore_file(saved, destination, expected_hash):
    fd, temporary = tempfile.mkstemp(prefix=".restore-", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        shutil.copy2(saved, temporary)
        if digest(temporary) != expected_hash:
            raise ValueError("Backup hash mismatch")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def rollback(path, rid, acknowledged=False):
    from .common import identifier

    path, _ = managed(path)
    closed(path, acknowledged)
    identifier(rid)
    backup = path / ".silicon-shader/history" / rid
    receipt = read(backup / "receipt.json")
    if receipt["state"] not in ("applied", "rolling-back"):
        raise ValueError("Receipt is not an applied or interrupted rollback")
    resuming = receipt["state"] == "rolling-back"
    for rel, entry in receipt["files"].items():
        target = contained(path, rel)
        actual = digest(target) if target.exists() else None
        allowed = {entry["after"], entry["before"]} if resuming else {entry["after"]}
        if actual not in allowed:
            raise ValueError(
                "Settings changed since application; refusing to overwrite"
            )
        if (
            entry["before"] is not None
            and digest(contained(backup, rel)) != entry["before"]
        ):
            raise ValueError("Backup hash mismatch")
    # Durable state allows a retry to recognize files already restored. Each copy is
    # atomic, so interruption never leaves a partly overwritten configuration file.
    receipt["state"] = "rolling-back"
    write(backup / "receipt.json", receipt)
    for rel, entry in receipt["files"].items():
        target = contained(path, rel)
        actual = digest(target) if target.exists() else None
        if actual == entry["before"]:
            continue
        if entry["before"] is None:
            target.unlink(missing_ok=True)
        else:
            _restore_file(contained(backup, rel), target, entry["before"])
    receipt["state"] = "rolled-back"
    write(backup / "receipt.json", receipt)
    return receipt


def daily(source, dest, acknowledged=False, save=None):
    _, source_meta = managed(source)
    result = isolate(
        source, dest, acknowledged, save, source_meta.get("layout") == "game-directory"
    )
    game = game_dir(result)
    removed = []
    for p in (game / "mods").glob("*"):
        mod_id = ""
        if p.suffix == ".jar" and zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as archive:
                if "fabric.mod.json" in archive.namelist():
                    entry = archive.getinfo("fabric.mod.json")
                    if entry.file_size > 1048576:
                        raise ValueError("Oversized mod metadata")
                    mod_id = json.loads(archive.read(entry)).get("id", "")
        if mod_id in ("minescript", "framebench", "frame_sampler") or any(
            x in p.name.lower()
            for x in ("minescript", "frame-agent", "frame-sink", "benchmark")
        ):
            removed.append(p.name)
            p.unlink()
    meta = read(result / MARKER)
    meta.update(
        kind="daily",
        removed_instrumentation=removed,
        qualification="Not launched: complete normal gameplay and save/reload checklist",
    )
    write(result / MARKER, meta)
    return result
