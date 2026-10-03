"""Public screenshot and reproduction links for a shared setup."""

import re
from urllib.parse import urlsplit


def validate_presentation(value):
    if not isinstance(value, dict) or set(value) != {
        "title",
        "screenshot_url",
        "recipe_url",
    }:
        raise ValueError("Setup details need title, screenshot_url and recipe_url")
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
