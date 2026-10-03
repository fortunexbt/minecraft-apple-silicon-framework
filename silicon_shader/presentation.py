"""Public screenshot and reproduction links for a shared setup."""

import re
import struct
from pathlib import Path
from urllib.parse import urlsplit


SHOWCASE_VIEW = "overworld-front-v1"


def inspect_screenshot(path):
    """Check the saved PNG's dimensions; pixels still need visual inspection."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_000_000:
        raise ValueError("Choose a saved PNG under 16 MB, not a symlink")
    with path.open("rb") as stream:
        header = stream.read(24)
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[8:16] != b"\x00\x00\x00\rIHDR"
    ):
        raise ValueError("Expected an original Minecraft PNG screenshot")
    width, height = struct.unpack(">II", header[16:24])
    if (width, height) != (1920, 1080):
        raise ValueError(
            f"Screenshot is {width}x{height}; capture 1920x1080 without resizing the PNG"
        )
    return {
        "screenshot_view": SHOWCASE_VIEW,
        "dimensions": [width, height],
        "visual_review_required": True,
        "next": "Inspect the full image for the fixed front-facing view, visible skin and correct shaders; dimensions alone do not verify content.",
    }


def validate_presentation(value, *, for_submission=False, require_showcase=False):
    required = {"title", "screenshot_url", "recipe_url"}
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) - required - {"minecraft_profile", "agent", "screenshot_view"}
    ):
        raise ValueError("Setup details need title, screenshot_url and recipe_url")
    if for_submission and not value.get("minecraft_profile"):
        raise ValueError("Add minecraft_profile to setup.json before publishing")
    if for_submission and "agent" not in value:
        raise ValueError(
            "Add agent.model and agent.harness to setup.json before publishing"
        )
    if (require_showcase or "screenshot_view" in value) and value.get(
        "screenshot_view"
    ) != SHOWCASE_VIEW:
        raise ValueError(
            "Capture the standard front-facing showcase and add "
            "screenshot_view: overworld-front-v1 before publishing"
        )
    if "agent" in value:
        agent = value["agent"]
        if not isinstance(agent, dict) or set(agent) != {"model", "harness"}:
            raise ValueError("Agent attribution needs model and harness")
        for label in agent.values():
            if (
                not isinstance(label, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._+()-]{0,79}", label)
                or label != label.strip()
            ):
                raise ValueError(
                    "Use a short public model/harness label (1–80 characters), without paths or URLs"
                )
    profile = value.get("minecraft_profile")
    if "minecraft_profile" in value and (
        not isinstance(profile, str)
        or not re.fullmatch(
            r"(?:[A-Za-z0-9_]{3,16}|[a-fA-F0-9]{32}|[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            profile,
        )
    ):
        raise ValueError("Minecraft profile must be a Java username or UUID")
    title = value["title"]
    if (
        not isinstance(title, str)
        or not 3 <= len(title) <= 80
        or any(ord(c) < 32 for c in title)
    ):
        raise ValueError("Use a short public setup title (3–80 characters)")
    for key in ("screenshot_url", "recipe_url"):
        value_url = value[key]
        if not isinstance(value_url, str) or len(value_url) > 1000:
            raise ValueError("Invalid public link")
        url = urlsplit(value_url)
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.port
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "Use a public HTTPS link without credentials or query parameters"
            )
        if key == "screenshot_url":
            raw = url.netloc == "raw.githubusercontent.com" and re.fullmatch(
                r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[a-f0-9]{40}/[^?#]+\.(?:png|jpg|jpeg|webp)",
                url.path,
                re.I,
            )
            attachment = url.netloc == "github.com" and re.fullmatch(
                r"/user-attachments/assets/[a-f0-9-]{36}", url.path
            )
            if not (raw or attachment):
                raise ValueError(
                    "Screenshot must be a GitHub attachment or PNG/JPEG/WebP at a pinned raw GitHub commit"
                )
        elif not (
            url.netloc == "github.com"
            and re.fullmatch(
                r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/blob/[a-f0-9]{40}/[^?#]+\.md",
                url.path,
                re.I,
            )
        ):
            raise ValueError(
                "Recipe must link to a Markdown file at an exact GitHub commit"
            )
    return value
