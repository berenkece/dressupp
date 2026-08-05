"""Clean image pipeline: rembg (U²-Net) background removal and cropping."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from src.utils import convert_to_jpeg

__all__ = ["SegmentationPipeline", "remove_background", "trim_to_content", "process"]


class SegmentationPipeline:
    """Encapsulates the rembg (U²-Net) background-removal workflow with configurable defaults."""

    def __init__(
        self,
        max_edge: int = 1024,
        padding: int = 10,
        model_name: str = "u2net",
    ) -> None:
        self.max_edge = max_edge
        self.padding = padding
        self.model_name = model_name
        self._session = None

    def _resolve_input_image(
        self,
        image_input: Image.Image | str | Path,
        output_dir: str | Path = "data/processed",
    ) -> Image.Image:
        """Return a PIL image from a file path or from an in-memory PIL image.

        If a filesystem path is provided and it is not already JPEG, it is normalized
        through the utility converter before segmentation.
        """
        if isinstance(image_input, (str, Path)):
            normalized_path = convert_to_jpeg(image_input, output_dir=output_dir)
            with Image.open(normalized_path) as opened:
                return opened.copy()

        return image_input.copy()

    def _normalize_input(self, img: Image.Image) -> Image.Image:
        """Convert the image to RGBA, correct EXIF orientation, and downscale it."""
        image = ImageOps.exif_transpose(img)

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        width, height = image.size
        max_side = max(width, height)
        if max_side > self.max_edge:
            scale = self.max_edge / max_side
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        return image

    def _load_session(self):
        """Lazily create the rembg inference session on first use."""
        if self._session is not None:
            return self._session

        try:
            from rembg import new_session
        except ModuleNotFoundError as exc:
            raise ImportError(
                "rembg is not installed. Run 'pip install rembg'."
            ) from exc

        self._session = new_session(self.model_name)
        return self._session

    def remove_background(self, img: Image.Image | str | Path) -> Image.Image:
        """Remove the background via rembg's class-agnostic saliency segmentation."""
        from rembg import remove

        normalized = self._normalize_input(self._resolve_input_image(img))
        session = self._load_session()

        result = remove(normalized, session=session)
        return result if result.mode == "RGBA" else result.convert("RGBA")

    def trim_to_content(self, img: Image.Image | str | Path, padding: int | None = None) -> Image.Image:
        """Crop the image around its content using the alpha channel bounding box."""
        if padding is None:
            padding = self.padding

        image = self._normalize_input(self._resolve_input_image(img))
        alpha = image.getchannel("A")
        alpha_bbox = alpha.getbbox()

        if alpha_bbox is None:
            return image.copy()

        left, upper, right, bottom = alpha_bbox
        padding = max(0, int(padding))

        width, height = image.size
        left = max(0, left - padding)
        upper = max(0, upper - padding)
        right = min(width, right + 1 + padding)
        bottom = min(height, bottom + 1 + padding)

        if left >= right or upper >= bottom:
            return image.copy()

        cropped = image.crop((left, upper, right, bottom)).copy()
        return cropped.convert("RGBA")

    def process(
        self,
        img: Image.Image | str | Path,
        trim: bool = True,
        padding: int | None = None,
        output_dir: str | Path = "data/processed",
    ) -> Image.Image:
        """Run rembg background removal and optional cropping in a single call.

        The input may be either an in-memory PIL image or a filesystem path. Path-based
        inputs are checked for JPEG format and converted through the helper utility when
        needed before segmentation begins.
        """
        resolved = self._resolve_input_image(img, output_dir=output_dir)
        removed = self.remove_background(resolved)
        if trim:
            return self.trim_to_content(removed, padding=padding)
        return removed.convert("RGBA")


_DEFAULT_PIPELINE = SegmentationPipeline()


def remove_background(img: Image.Image | str | Path) -> Image.Image:
    """Backward-compatible wrapper for rembg-based background removal."""
    return _DEFAULT_PIPELINE.remove_background(img)


def trim_to_content(img: Image.Image | str | Path, padding: int = 10) -> Image.Image:
    """Backward-compatible wrapper for content-aware cropping."""
    return _DEFAULT_PIPELINE.trim_to_content(img, padding=padding)


def process(img: Image.Image | str | Path, trim: bool = True) -> Image.Image:
    """Backward-compatible wrapper for the full rembg-based pipeline."""
    return _DEFAULT_PIPELINE.process(img, trim=trim)
