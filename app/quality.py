"""Image inspection used to prove a provider returned a real photograph.

Pillow is used here **only for image processing** - decoding, resizing and
measuring pixels. It never generates a photo and this module never claims an
image is "AI generated"; it measures whether the bytes are a real, detailed
raster photograph instead of a blank frame or a procedural placeholder.

Two independent pieces of evidence are combined elsewhere in the pipeline:

* provider identity (which backend produced the bytes, and whether that backend
  is a remote diffusion model or the offline placeholder), and
* these pixel measurements (entropy, colour variety, edge detail, contrast).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from io import BytesIO

from PIL import Image, ImageFilter, ImageStat

MIN_DIMENSION = 256
MIN_UNIQUE_COLORS = 1_500
MIN_ENTROPY = 6.0
MIN_DETAIL = 15.0
MIN_CONTRAST = 12.0
MIN_BYTES = 5_000


class ImageValidationError(RuntimeError):
    """Raised when provider bytes are not a usable photograph."""

    def __init__(self, message: str, quality: "ImageQuality | None" = None) -> None:
        super().__init__(message)
        self.quality = quality


@dataclass(frozen=True)
class ImageQuality:
    """Measured properties of one encoded image."""

    width: int
    height: int
    size_bytes: int
    format: str
    entropy: float
    unique_colors: int
    detail: float
    contrast: float
    brightness: float
    has_exif: bool
    sha256: str
    is_photographic: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data

    def summary(self) -> str:
        return (
            f"{self.width}x{self.height} {self.format} {self.size_bytes}B "
            f"entropy={self.entropy:.2f} colors={self.unique_colors} "
            f"detail={self.detail:.1f} contrast={self.contrast:.1f}"
        )


def _entropy(gray: Image.Image) -> float:
    histogram = gray.histogram()
    total = sum(histogram)
    if not total:
        return 0.0
    entropy = 0.0
    for count in histogram:
        if count:
            probability = count / total
            entropy -= probability * math.log2(probability)
    return entropy


def inspect_image(data: bytes) -> ImageQuality:
    """Decode ``data`` and measure it. Raises if the bytes are not an image."""
    if not data:
        raise ImageValidationError("Provider returned zero bytes.")

    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            width, height = image.size
            image_format = (image.format or "unknown").upper()
            has_exif = bool(image.getexif())
            rgb = image.convert("RGB")
    except Exception as exc:  # noqa: BLE001 - any decode failure means invalid bytes
        raise ImageValidationError(
            f"Provider returned data that is not a decodable image ({exc.__class__.__name__})."
        ) from exc

    gray = rgb.convert("L")
    stats = ImageStat.Stat(gray)
    contrast = float(stats.stddev[0])
    brightness = float(stats.mean[0])

    small = rgb.resize((96, 96), Image.BILINEAR)
    colours = small.getcolors(maxcolors=1 << 20)
    unique_colors = len(colours) if colours else 0

    edges = gray.filter(ImageFilter.FIND_EDGES)
    detail = float(ImageStat.Stat(edges).stddev[0])

    reasons: list[str] = []
    if len(data) < MIN_BYTES:
        reasons.append(f"file too small ({len(data)} bytes)")
    if min(width, height) < MIN_DIMENSION:
        reasons.append(f"resolution too low ({width}x{height})")
    if unique_colors < MIN_UNIQUE_COLORS:
        reasons.append(f"too few distinct colours ({unique_colors})")
    if _entropy(gray) < MIN_ENTROPY:
        reasons.append("pixel distribution is too flat for a photograph")
    if detail < MIN_DETAIL:
        reasons.append(f"no photographic detail ({detail:.1f})")
    if contrast < MIN_CONTRAST:
        reasons.append(f"no tonal range ({contrast:.1f})")

    return ImageQuality(
        width=width,
        height=height,
        size_bytes=len(data),
        format=image_format,
        entropy=round(_entropy(gray), 3),
        unique_colors=unique_colors,
        detail=round(detail, 2),
        contrast=round(contrast, 2),
        brightness=round(brightness, 2),
        has_exif=has_exif,
        sha256=hashlib.sha256(data).hexdigest(),
        is_photographic=not reasons,
        reasons=tuple(reasons),
    )


def validate_photo(data: bytes, provider: str = "", min_dimension: int = MIN_DIMENSION) -> ImageQuality:
    """Return measurements for a real photo, or raise :class:`ImageValidationError`.

    Used by every network/self-hosted provider so a blank, truncated or flat
    response can never be stored as if it were a generated photograph.
    """
    quality = inspect_image(data)
    reasons = list(quality.reasons)
    if min(quality.width, quality.height) < min_dimension:
        reasons.append(f"below requested minimum {min_dimension}px")

    if reasons:
        prefix = f"{provider}: " if provider else ""
        raise ImageValidationError(
            prefix + "image failed quality validation - " + "; ".join(reasons), quality
        )
    return quality
