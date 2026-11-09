"""Perceptual hash duplicate detection."""

from __future__ import annotations

import random
from io import BytesIO

from PIL import Image

from app import dedupe


def _jpeg(kind: str, quality: int = 90) -> bytes:
    image = Image.new("RGB", (256, 256))
    pixels = image.load()
    rnd = random.Random(5)
    for x in range(256):
        for y in range(256):
            if kind == "noise":
                pixels[x, y] = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
            else:
                value = 255 if ((x // 16) + (y // 16)) % 2 else 0
                pixels[x, y] = (value, value, value)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def test_identical_images_are_duplicates():
    data = _jpeg("noise")
    first = dedupe.hash_image_bytes(data)
    second = dedupe.hash_image_bytes(data)
    assert first == second
    assert first["sha256"]
    assert dedupe.is_duplicate(
        first["dhash"], first["ahash"], second["dhash"], second["ahash"], 6
    )


def test_reencoded_image_is_detected_as_near_duplicate():
    original = dedupe.hash_image_bytes(_jpeg("noise", quality=92))
    reencoded = dedupe.hash_image_bytes(_jpeg("noise", quality=60))
    assert dedupe.hamming(original["dhash"], reencoded["dhash"]) <= 12
    assert dedupe.is_duplicate(
        original["dhash"], original["ahash"], reencoded["dhash"], reencoded["ahash"], 12
    )


def test_different_images_are_not_duplicates():
    noise = dedupe.hash_image_bytes(_jpeg("noise"))
    checker = dedupe.hash_image_bytes(_jpeg("checker"))
    assert dedupe.hamming(noise["dhash"], checker["dhash"]) > 6
    assert not dedupe.is_duplicate(
        noise["dhash"], noise["ahash"], checker["dhash"], checker["ahash"], 6
    )


def test_storage_finds_duplicate_after_generation(store, settings):
    from app import generator

    post = generator.generate_post(store, settings, rng=random.Random(4))
    hashes = dedupe.hash_image_file(post["image_path"])
    match = store.find_duplicate(
        hashes["dhash"], hashes["ahash"], hashes["sha256"], settings.phash_threshold
    )
    assert match is not None
    assert match["id"] == post["id"]
