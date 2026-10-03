"""Read-only configuration triage. Disk state never substitutes for observation."""

from pathlib import Path
import zipfile
from .common import contained, digest, no_links, properties
from .discover import instance_info
from .instances import current_profile
from .measure import CONTEXT


def doctor(instance, game_directory=False):
    path = Path(instance).expanduser().resolve()
    info = {"id": path.name, "path": str(path)}
    issues = []

    def issue(code, action):
        issues.append({"code": code, "action": action})

    profile = None
    shader = None
    try:
        # Refuse config/mod/world symlinks rather than reading beyond this instance.
        no_links(path)
        if game_directory:
            info.update(
                game_dir=".", versions={}, java_required=None, launcher="external"
            )
        else:
            info = instance_info(path)
        game = path / info["game_dir"]
        profile = current_profile(path, game_directory=game_directory)
        options = profile["options"]
        if options.get("fullscreen") is not True:
            issue(
                "fullscreen_disabled",
                "Enable native fullscreen in the lab and verify actual output pixels.",
            )
        if profile.get("scale") is None:
            issue(
                "scale_unknown",
                "No supported scaling adapter found. Use your own settings/harness; do not replace your mod stack blindly.",
            )
        controls = profile.get("scale_options", {})
        if controls.get("targetFrameRate") not in (None, 0):
            issue(
                "dynamic_scaling", "Choose static scaling before matched comparisons."
            )
        if controls.get("irisScale", profile.get("scale")) != profile.get("scale"):
            issue(
                "mixed_scaling", "Set matching game and Iris scales before measurement."
            )
        if options.get("renderDistance", 0) < 12:
            issue(
                "view_distance",
                "Choose a render distance of at least 12 for this workflow.",
            )
        iris_path = game / "config/iris.properties"
        iris = properties(
            iris_path if iris_path.exists() else game / "optionsshaders.txt"
        )
        info["shader_adapter"] = "iris" if iris_path.exists() else "external-config"
        name = iris.get("shaderPack", "")
        if not name or Path(name).name != name or name in (".", ".."):
            issue(
                "shader_missing",
                "Select a shader pack through Iris in the isolated lab.",
            )
        else:
            pack = contained(game / "shaderpacks", name)
            exists = (pack.is_file() and zipfile.is_zipfile(pack)) or (
                pack.is_dir() and (pack / "shaders").is_dir()
            )
            if not exists:
                issue(
                    "shader_missing",
                    "The selected shader archive/folder is absent or unreadable.",
                )
            else:
                shader = {
                    "name": name,
                    "archive_sha256": digest(pack) if pack.is_file() else None,
                }
                settings = game / "shaderpacks" / (name + ".txt")
                shader["settings_sha256"] = (
                    digest(settings) if settings.is_file() else None
                )
            if iris_path.exists() and iris.get("enableShaders") != "true":
                issue(
                    "shader_disabled",
                    "Enable the selected shader in Iris before checking its appearance.",
                )
    except (ValueError, OSError, KeyError, TypeError) as error:
        issue(
            "unsafe_path"
            if "Symlink" in str(error) or "escapes" in str(error)
            else "configuration_error",
            str(error),
        )
    expected = {key: None for key in CONTEXT}
    expected.update(instance=path.name, game_state="playing", player_alive=True)
    if profile:
        opts = profile["options"]
        controls = profile.get("scale_options", {})
        expected.update(
            scale=profile.get("scale"),
            render_distance=opts.get("renderDistance"),
            simulation_distance=opts.get("simulationDistance"),
            cap=opts.get("maxFps"),
            vsync=opts.get("enableVsync"),
            fullscreen=opts.get("fullscreen"),
        )
        if controls.get("fsr") is True:
            expected["filter"] = "fsr"
        elif type(controls.get("forceLinear")) is bool:
            expected["filter"] = "linear" if controls["forceLinear"] else "nearest"
    if shader:
        # Archive identity is a separate diagnostic field. Public capture labels
        # must also be usable by the challenge metadata vocabulary.
        expected["shader"] = Path(shader["name"]).stem

    return {
        "instance": info,
        "profile": profile,
        "shader": shader,
        "issues": issues,
        "configuration_ready": not issues,
        "gameplay_verified": False,
        "runtime_verified": False,
        "next": [
            "Verify explicitly selected ARM64 Java with the runtime command.",
            "Fill unknown expectations, then independently observe the game; never copy expected into observed.",
            "Use a disposable safe test save; pause/exit before stepping away for backend work.",
        ],
        "manifest_template": {
            "expected": expected,
            "observed": {key: None for key in CONTEXT},
            "visual": {
                "valid": False,
                "artifacts": None,
                "acceptable_quality": False,
                "reviewer": None,
            },
        },
    }
