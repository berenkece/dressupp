"""
Baskın renk çıkarımı.

KMeans ile şeffaf PNG üzerinden en fazla 3 baskın rengi çıkarır.
Bu modül, şeffaf arka plan piksellerini filtreleyip kalan kıyafet
pikselleri üzerinde kümeleme yapar. Her renk hem hex hem de HSV
formatında döndürülür.
"""

from __future__ import annotations

import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from sklearn.cluster import KMeans

__all__ = ["ColorExtractor", "extract_dominant_colors"]


class ColorExtractor:
    """Kıyafet görsellerinde baskın renkleri çıkaran sınıf."""

    def __init__(self, n_colors: int = 3, sample_size: int = 50000) -> None:
        self.n_colors = n_colors
        self.sample_size = sample_size

    def extract(self, image_input: Image.Image | str | Path) -> list[dict[str, str | tuple[float, float, float]]]:
        image = self._load_image(image_input)
        opaque_pixels = self._extract_opaque_pixels(image)

        if opaque_pixels.shape[0] == 0:
            return []

        sampled_pixels = self._sample_pixels(opaque_pixels)
        cluster_centers = self._cluster_pixels(sampled_pixels)
        return self._format_dominant_colors(cluster_centers)

    def _load_image(self, image_input: Image.Image | str | Path) -> Image.Image:
        image = self._resolve_input_image(image_input)
        return self._normalize_rgba(image)

    @staticmethod
    def _resolve_input_image(image_input: Image.Image | str | Path) -> Image.Image:
        if isinstance(image_input, (str, Path)):
            with Image.open(image_input) as opened:
                return opened.copy()
        return image_input.copy()

    @staticmethod
    def _normalize_rgba(image: Image.Image) -> Image.Image:
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        return image

    @staticmethod
    def _extract_opaque_pixels(image: Image.Image) -> np.ndarray:
        data = np.asarray(image)
        if data.ndim != 3 or data.shape[2] != 4:
            image = image.convert("RGBA")
            data = np.asarray(image)

        rgba = data.reshape(-1, 4)
        alpha = rgba[:, 3]
        return rgba[alpha > 0, :3].astype(np.float64)

    def _sample_pixels(self, pixels: np.ndarray) -> np.ndarray:
        if pixels.shape[0] <= self.sample_size:
            return pixels

        rng = np.random.default_rng(0)
        indices = rng.choice(pixels.shape[0], size=self.sample_size, replace=False)
        return pixels[indices]

    def _cluster_pixels(self, pixels: np.ndarray) -> np.ndarray:
        n_clusters = min(self.n_colors, pixels.shape[0])
        pixels = np.nan_to_num(pixels, nan=0.0, posinf=255.0, neginf=0.0)
        kmeans = KMeans(
            n_clusters=n_clusters,
            init="random",
            n_init=10,
            random_state=0,
            tol=1e-4,
        )
        kmeans.fit(pixels)
        counts = np.bincount(kmeans.labels_, minlength=n_clusters)
        order = np.argsort(counts)[::-1]
        return np.round(kmeans.cluster_centers_[order]).astype(int)

    def _format_dominant_colors(self, centers: np.ndarray) -> list[dict[str, str | tuple[float, float, float]]]:
        return [
            {
                "hex": self._rgb_to_hex(center),
                "hsv": self._rgb_to_hsv(center),
            }
            for center in centers
        ]

    @staticmethod
    def _rgb_to_hex(rgb: np.ndarray) -> str:
        return "#{:02X}{:02X}{:02X}".format(*(int(c) for c in rgb))

    @staticmethod
    def _rgb_to_hsv(rgb: np.ndarray) -> tuple[float, float, float]:
        r, g, b = (float(c) / 255.0 for c in rgb)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (round(h * 360.0, 2), round(s, 4), round(v, 4))


_DEFAULT_EXTRACTOR = ColorExtractor()


def extract_dominant_colors(
    image_input: Image.Image | str | Path,
    n_colors: int = 3,
    sample_size: int = 50000,
) -> list[dict[str, str | tuple[float, float, float]]]:
    """Backward-compatible helper that uses ColorExtractor.

    Parameters:
        image_input: RGBA image or path to an image file.
        n_colors: Number of dominant colors to return.
        sample_size: Maximum number of pixels used for KMeans clustering.

    Returns:
        A list of dict objects with keys "hex" and "hsv".
    """
    extractor = ColorExtractor(n_colors=n_colors, sample_size=sample_size)
    return extractor.extract(image_input)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 0:
        print("Usage: python src/color.py <input-image> [--colors N]", file=sys.stderr)
        return 1

    input_path = Path(argv[0])
    n_colors = 3
    if "--colors" in argv:
        idx = argv.index("--colors")
        if idx + 1 < len(argv):
            n_colors = int(argv[idx + 1])

    colors = extract_dominant_colors(input_path, n_colors=n_colors)
    print(json.dumps({"input": str(input_path), "dominant_colors": colors}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
