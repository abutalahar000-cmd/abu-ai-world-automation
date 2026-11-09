"""Unit tests for the image-quality validator.

Pillow is used here only to measure pixels: the tests prove the validator
accepts a detailed raster image and rejects flat or tiny frames, which is what
stops a blank response from being stored as a "generated photo".
"""

from __future__ import annotations

import random as random_module
from io import BytesIO

import pytest
from PIL import Image

from app import quality


def _noise_jpeg(size: int = 512) -> bytes:
    """A high-detail image used to exercise the upper thresholds."""
    rng = random_module.Random(11)
    image = Image.new("RGB", (size, size))
    image.putdata(
        [
            (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            for _ in range(size * size)
        ]
    )
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def _flat_jpeg(colour=(120, 120, 120), size: int = 512) -> bytes:
    image = Image.new("RGB", (size, size), colour)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def test_detailed_image_passes_validation():
    measured = quality.validate_photo(_noise_jpeg(), provider="test")
    assert measured.is_photographic is True
    assert measured.reasons == ()
    assert measured.width == 512
    assert measured.unique_colors >= quality.MIN_UNIQUE_COLORS
    assert measured.entropy >= quality.MIN_ENTROPY
    assert measured.detail >= quality.MIN_DETAIL


def test_flat_image_is_rejected_as_not_photographic():
    with pytest.raises(quality.ImageValidationError) as excinfo:
        quality.validate_photo(_flat_jpeg(), provider="test")
    message = str(excinfo.value)
    assert "test:" in message
    assert "failed quality validation" in message


def test_non_image_bytes_are_rejected():
    with pytest.raises(quality.ImageValidationError) as excinfo:
        quality.validate_photo(b"<html>rate limited</html>")
    assert "not a decodable image" in str(excinfo.value)


def test_empty_response_is_rejected():
    with pytest.raises(quality.ImageValidationError):
        quality.inspect_image(b"")


def test_low_resolution_is_rejected():
    with pytest.raises(quality.ImageValidationError) as excinfo:
        quality.validate_photo(_noise_jpeg(128), provider="test")
    assert "resolution too low" in str(excinfo.value)


def test_measurements_serialise_for_reports():
    measured = quality.inspect_image(_noise_jpeg(256))
    data = measured.to_dict()
    assert data["format"] == "JPEG"
    assert isinstance(data["reasons"], list)
    assert len(data["sha256"]) == 64
    assert "entropy=" in measured.summary()
