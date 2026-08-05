from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def convert_to_jpeg(image_source: str | Path, output_dir: str | Path = "data/processed") -> str:
    """Convert a non-JPEG image source into JPEG and return the destination path."""
    source = Path(image_source)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() in {".jpg", ".jpeg"}:
        return str(source)

    target_path = target_dir / f"{source.stem}.jpg"

    try:
        with Image.open(source) as img:
            rgb = img.convert("RGB")
            rgb.save(target_path, format="JPEG", quality=95)
        return str(target_path)
    except UnidentifiedImageError:
        if source.suffix.lower() in {".heic", ".heif"}:
            subprocess.run(
                ["sips", "-s", "format", "jpeg", str(source), "--out", str(target_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return str(target_path)
        raise


def save_output(img: Image.Image, filename: str = "output.png", output_dir: str | Path = "data/processed") -> str:
    """Persist a processed image to disk and return the output path.

    Images with an alpha channel are saved as PNG to preserve transparency
    (converting RGBA to RGB drops alpha without compositing, which would
    silently reveal the "removed" background instead of showing it as clear).
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        output_path = target_dir / Path(filename).with_suffix(".png")
        img.save(output_path, format="PNG")
        return str(output_path)

    output_path = target_dir / filename
    rgb = img.convert("RGB") if img.mode != "RGB" else img
    rgb.save(output_path, format="JPEG", quality=95)
    return str(output_path)
