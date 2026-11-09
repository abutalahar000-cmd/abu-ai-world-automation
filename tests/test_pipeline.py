"""End-to-end generation pipeline."""

from __future__ import annotations

import dataclasses
import random
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import generator


def _fixed_image() -> bytes:
    image = Image.new("RGB", (512, 512))
    pixels = image.load()
    for x in range(512):
        for y in range(512):
            pixels[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 2) % 256)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


class _StubProvider:
    """Duck-typed provider that always returns the same image."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def available(self) -> bool:
        return True

    def generate(self, request):  # noqa: ARG002 - signature parity
        class _Result:
            data = self.data
            provider = "stub"
            meta = {}

        return _Result()


def test_batch_creates_unique_pending_posts(store, settings):
    outcome = generator.generate_batch(store, settings, count=3, rng=random.Random(42))
    assert outcome.errors == []
    assert len(outcome.created) == 3

    for post in outcome.created:
        assert post["status"] == "pending"
        assert post["category"] in {"girls", "boys", "lifestyle", "fashion", "travel", "food",
                                    "nature", "architecture", "fitness", "street"}
        assert Path(post["image_path"]).exists()
        assert post["prompt"].strip()
        assert post["title"].strip()
        assert post["caption"].strip()
        assert post["hashtags"]
        assert post["blueprint"]["attributes"]

    assert len({post["prompt_fingerprint"] for post in outcome.created}) == 3
    assert len({post["phash"] for post in outcome.created}) == 3
    assert len({post["title"] for post in outcome.created}) == 3
    assert store.counts()["pending"] == 3


def test_duplicate_photo_is_rejected(store, settings, monkeypatch):
    monkeypatch.setattr(
        generator.providers, "get_provider", lambda name, settings: _StubProvider(_fixed_image())
    )
    first = generator.generate_post(store, settings, rng=random.Random(1))
    assert first["status"] == "pending"

    with pytest.raises(generator.GenerationError):
        generator.generate_post(store, settings, rng=random.Random(2))

    assert store.counts()["total"] == 1
    events = store.list_events(limit=20)
    assert any("duplicate" in (event["kind"] + event["message"]).lower() for event in events)


def test_same_blueprint_cannot_be_stored_twice(store, settings):
    post = generator.generate_post(store, settings, rng=random.Random(9))
    with pytest.raises(Exception):
        store.create_post({**post, "id": "second-id", "image_file": post["image_file"]})


def test_approval_mode_can_be_disabled(store, settings):
    relaxed = dataclasses.replace(settings, require_approval=False)
    post = generator.generate_post(store, relaxed, rng=random.Random(5))
    assert post["status"] == "approved"
    assert post["approved_at"]


def test_generation_continues_after_a_provider_failure(store, settings, monkeypatch):
    calls = {"count": 0}
    real = generator.providers.get_provider

    def flaky(name, settings):
        provider = real(name, settings)
        calls["count"] += 1
        if calls["count"] == 1:
            class _Broken:
                def available(self):
                    return True

                def generate(self, request):
                    raise generator.providers.ProviderError("temporary failure")

            return _Broken()
        return provider

    monkeypatch.setattr(generator.providers, "get_provider", flaky)
    outcome = generator.generate_batch(store, settings, count=2, rng=random.Random(21))
    # The configured provider and its fallback are the same backend here, so the
    # failing post is reported instead of crashing the batch, and the next post
    # still succeeds.
    assert len(outcome.created) == 1
    assert len(outcome.errors) == 1
    assert store.counts()["total"] == 1
