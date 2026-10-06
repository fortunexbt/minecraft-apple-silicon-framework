"""Build small WebP thumbnails of the pinned screenshots for the static site.

Runs only in the Pages build (needs Pillow, which is not a runtime dependency).
It reads the generated site/data.json, downloads only the validated, commit-pinned
raw.githubusercontent.com screenshots, and writes two widths per entry plus an
index the page uses to pick them. Any failure skips that entry, and the page falls
back to the original screenshot.
"""

import io
import json
import re
import sys
import urllib.request
from pathlib import Path

WIDTHS = (640, 1280)
MAX_BYTES = 16_000_000
MAX_PIXELS = 40_000_000
PINNED = re.compile(
    r"https://raw\.githubusercontent\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[a-f0-9]{40}/[^?#\s]+\.(?:png|jpe?g|webp)",
    re.IGNORECASE,
)


def fetch(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "silicon-shader-pages"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        blob = response.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("screenshot larger than 16 MB")
    return blob


def make_thumbnails(blob, digest, out):
    """Write <digest>-<width>.webp for each width not larger than the source."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    image = Image.open(io.BytesIO(blob))
    image.load()
    image = image.convert("RGB")
    made = []
    for width in WIDTHS:
        if image.width < width:
            continue
        height = round(image.height * width / image.width)
        resized = image.resize((width, height), Image.LANCZOS)
        resized.save(Path(out) / f"{digest}-{width}.webp", "WEBP", quality=82, method=6)
        made.append(width)
    return made


def build(data_path, out_dir):
    data = json.loads(Path(data_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    for entry in data.get("entries", []):
        url = (entry.get("presentation") or {}).get("screenshot_url", "")
        digest = entry.get("digest", "")
        if not PINNED.fullmatch(url) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            continue
        try:
            widths = make_thumbnails(fetch(url), digest, out)
        except Exception as error:  # noqa: BLE001 - one bad image must not stop the build
            print(f"skipped thumbnails for {digest[:12]}: {error}", file=sys.stderr)
            continue
        if widths:
            index[digest] = widths
    (out / "index.json").write_text(json.dumps(index, separators=(",", ":")) + "\n")
    return index


if __name__ == "__main__":
    result = build(sys.argv[1], sys.argv[2])
    print(json.dumps({"thumbnails": len(result)}))
