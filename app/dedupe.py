"""Perceptual hashing used to reject duplicate and near-duplicate photos.

Everything here is implemented with Pillow + the standard library, so no paid
service or extra model is required.
"""

from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image, ImageOps


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _grayscale(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        converted = image.convert("RGBA")
        background.paste(converted, mask=converted.split()[-1])
        image = background
    return ImageOps.grayscale(image)


def dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Difference hash: robust to resizing/compression, sensitive to structure."""
    gray = _grayscale(image).resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = list(gray.getdata())
    bits = 0
    for row in range(hash_size):
        offset = row * (hash_size + 1)
        for column in range(hash_size):
            bits = (bits << 1) | (1 if pixels[offset + column] > pixels[offset + column + 1] else 0)
    return f"{bits:016x}"


def ahash(image: Image.Image, hash_size: int = 8) -> str:
    """Average hash: catches near-identical frames with small edits."""
    gray = _grayscale(image).resize((hash_size, hash_size), Image.LANCZOS)
    pixels = list(gray.getdata())
    average = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel > average else 0)
    return f"{bits:016x}"


def hamming(hex_a: str, hex_b: str) -> int:
    """Number of differing bits between two hexadecimal hashes."""
    if not hex_a or not hex_b:
        return 64
    try:
        return bin(int(hex_a, 16) ^ int(hex_b, 16)).count("1")
    except ValueError:
        return 64


def is_duplicate(
    dhash_a: str,
    ahash_a: str,
    dhash_b: str,
    ahash_b: str,
    threshold: int = 6,
) -> bool:
    """True when either perceptual hash is within ``threshold`` bits."""
    return hamming(dhash_a, dhash_b) <= threshold or hamming(ahash_a, ahash_b) <= threshold


def hash_image_bytes(data: bytes) -> dict[str, str]:
    """Return ``sha256``, ``dhash`` and ``ahash`` for encoded image bytes."""
    with Image.open(BytesIO(data)) as image:
        image.load()
        return {
            "sha256": sha256_bytes(data),
            "dhash": dhash(image),
            "ahash": ahash(image),
        }


def hash_image_file(path) -> dict[str, str]:
    with open(path, "rb") as handle:
        return hash_image_bytes(handle.read())
