"""Read-only hardware, Prism and Java discovery. Unknown versions remain unknown."""

import json
import os
from pathlib import Path
import platform
import re
import subprocess
from .common import read, properties


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return (p.stdout or p.stderr).strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def java_requirement(version):
    # Metadata wins. These release families are a fallback, never extrapolate snapshots.
    if re.fullmatch(r"26\.[123](?:\.\d+)?", version):
        return 25
    m = re.fullmatch(r"1\.(\d+)(?:\.(\d+))?", version)
    if not m:
        return None
    minor, patch = int(m[1]), int(m[2] or 0)
    if minor > 21:
        return None
    if minor >= 21 or (minor == 20 and patch >= 5):
        return 21
    if minor >= 18:
        return 17
    if minor == 17:
        return 16
    return 8


def instance_info(path):
    path = Path(path).resolve()
    pack = read(path / "mmc-pack.json")
    versions = {c["uid"]: c.get("version") for c in pack.get("components", [])}
    mc = versions.get("net.minecraft", "unknown")
    cfg = properties(path / "instance.cfg")
    required = java_requirement(mc)
    metadata = path / "patches/net.minecraft.json"
    if metadata.exists():
        required = read(metadata).get("javaVersion", {}).get("majorVersion", required)
    game = path / ".minecraft" if (path / ".minecraft").is_dir() else path / "minecraft"
    return dict(
        id=path.name,
        path=str(path),
        name=cfg.get("name", path.name),
        versions=versions,
        java_required=required,
        java_configured=cfg.get("JavaPath"),
        game_dir=game.name,
        saves=sorted(p.name for p in (game / "saves").glob("*") if p.is_dir()),
        managed=(path / ".silicon-shader/instance.json").exists(),
    )


def parse_chip(chip):
    match = re.fullmatch(
        r"(?:Apple\s+)?([MA][1-9][0-9]*)(?:\s+(Pro|Max|Ultra))?", chip.strip(), re.I
    )
    if not match:
        return None, None
    return match[1].upper(), (match[2] or "base").lower()


def hardware_info():
    """Read generic hardware fields only; never return serials or machine UUIDs."""
    mac = platform.system() == "Darwin"
    chip = (
        command(["sysctl", "-n", "machdep.cpu.brand_string"])
        if mac
        else platform.processor()
    )
    memory = command(["sysctl", "-n", "hw.memsize"]) if mac else ""
    cores = command(["sysctl", "-n", "hw.ncpu"]) if mac else str(os.cpu_count())
    raw = (
        command(
            ["system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "-json"]
        )
        if mac
        else ""
    )
    gpu = []
    model = None
    model_id = None
    try:
        report = json.loads(raw)
        hardware = report.get("SPHardwareDataType", [{}])[0]
        model = hardware.get("machine_name")
        model_id = hardware.get("machine_model")
        for item in report.get("SPDisplaysDataType", []):
            gpu.append(
                {
                    key: item[key]
                    for key in ("sppci_model", "sppci_cores", "spdisplays_metal")
                    if key in item
                }
            )
    except (ValueError, IndexError, TypeError):
        pass
    family, tier = parse_chip(chip)
    apple_gpu = next(
        (item for item in gpu if str(item.get("sppci_model", "")).startswith("Apple")),
        {},
    )
    gpu_count = str(apple_gpu.get("sppci_cores", ""))
    gpu_match = re.fullmatch(r"\s*(\d+)(?:\s+.*)?", gpu_count)
    return {
        "chip": chip,
        "family": family,
        "tier": tier,
        "model": model,
        "model_identifier": model_id,
        "architecture": platform.machine(),
        "cpu_cores": int(cores) if cores.isdigit() else None,
        "gpu_cores": int(gpu_match[1]) if gpu_match else None,
        "memory_gib": round(int(memory) / 2**30, 1) if memory.isdigit() else None,
        "gpu": gpu,
        "os": platform.platform(),
    }


def public_profiles(root):
    """Return only public Minecraft identity fields, never account credentials."""
    try:
        accounts = json.loads((root / "accounts.json").read_text()).get("accounts", [])
        result = []
        for account in accounts:
            profile = account.get("profile", {})
            name, uuid = profile.get("name", ""), profile.get("id", "")
            if (
                isinstance(name, str)
                and isinstance(uuid, str)
                and re.fullmatch(r"[A-Za-z0-9_]{3,16}", name)
                and re.fullmatch(r"[a-fA-F0-9]{32}", uuid.replace("-", ""))
            ):
                result.append(
                    {
                        "name": name,
                        "uuid": uuid,
                        "active": account.get("active") is True,
                    }
                )
        return result
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def discover(prism=None):
    candidates = (
        [Path(prism).expanduser()]
        if prism
        else [
            Path.home() / "Library/Application Support/PrismLauncher",
            Path.home() / ".local/share/PrismLauncher",
            Path(os.environ.get("APPDATA", "~")) / "PrismLauncher",
        ]
    )
    roots = [p.resolve() for p in candidates if (p / "instances").is_dir()]
    hardware = hardware_info()
    instances = []
    for root in roots:
        for p in sorted((root / "instances").iterdir()):
            if (p / "mmc-pack.json").is_file():
                try:
                    instances.append(instance_info(p))
                except (ValueError, KeyError, OSError):
                    instances.append(
                        {"id": p.name, "error": "unreadable instance metadata"}
                    )
    return dict(
        hardware=hardware,
        minecraft_profiles=[
            profile for root in roots for profile in public_profiles(root)
        ],
        prism_roots=[str(p) for p in roots],
        instances=instances,
        game_directories=[
            str(p)
            for p in (
                Path.home() / "Library/Application Support/minecraft",
                Path.home() / ".minecraft",
                Path(os.environ.get("APPDATA", "~")).expanduser() / ".minecraft",
            )
            if (p / "options.txt").is_file()
        ],
        java_homes=command(["/usr/libexec/java_home", "-V"]),
        performance="Unmeasured on this machine; do not infer FPS from chip family",
    )


def inspect_runtime(executable, minecraft):
    """Invoke only the Java executable explicitly selected by the operator."""
    executable = Path(executable).expanduser().resolve()
    if not executable.is_file():
        raise ValueError("Java executable does not exist")
    try:
        p = subprocess.run(
            [str(executable), "-XshowSettings:properties", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("Java version probe timed out; runtime remains unverified")
    data = {}
    for line in (p.stdout + "\n" + p.stderr).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key.strip() in ("java.version", "java.home", "os.arch"):
                data[key.strip()] = value.strip()
    version = data.get("java.version", "")
    match = re.match(r"(?:1\.)?(\d+)", version)
    major = int(match[1]) if match else None
    required = java_requirement(minecraft)
    arm64 = data.get("os.arch") in ("aarch64", "arm64")
    return {
        "executable": str(executable),
        "minecraft": minecraft,
        "required_major": required,
        "observed": data,
        "compatible": p.returncode == 0
        and required is not None
        and major == required
        and arm64,
        "note": "Exact required Java major and ARM64 checked; no game launch or JVM performance claim",
    }
