"""Caption, title and hashtag generation."""

from __future__ import annotations

import random

from app import captioner, randomizer


def _copy(store, settings, category="travel", seed=99, count=1):
    """Generate copy the way the pipeline does: each post is persisted, so the
    next call's uniqueness checks see everything already used."""
    rng = random.Random(seed)
    results = []
    for index in range(count):
        blueprint = randomizer.build_unique_blueprint(store, category=category, rng=rng)
        copy = captioner.create_caption(store, blueprint, settings=settings, rng=rng)
        store.create_post(
            {
                "category": category,
                "title": copy["title"],
                "caption": copy["caption"],
                "hashtags": copy["hashtags"],
                "prompt": blueprint.prompt,
                "negative_prompt": blueprint.negative_prompt,
                "blueprint": {
                    "category": blueprint.category,
                    "kind": blueprint.kind,
                    "seed": blueprint.seed,
                    "attributes": blueprint.attributes,
                },
                "seed": blueprint.seed,
                "provider": "test",
                "image_path": f"media/test-{seed}-{index}.jpg",
                "image_sha256": f"{seed}{index}".ljust(64, "0"),
                "phash": f"{seed}{index}".ljust(16, "0"),
                "ahash": f"{seed}{index}".ljust(16, "0"),
                "prompt_fingerprint": blueprint.fingerprint,
                "caption_signature": copy["caption_signature"],
                "hashtag_signature": copy["hashtag_signature"],
            }
        )
        results.append(copy)
    return results


def test_copy_is_unique_per_photo(store, settings):
    results = _copy(store, settings, category="lifestyle", seed=31, count=15)
    assert len({item["title"] for item in results}) == 15
    assert len({item["caption"] for item in results}) == 15
    assert len({tuple(item["hashtags"]) for item in results}) == 15


def test_hashtags_are_well_formed(store, settings):
    result = _copy(store, settings, seed=5)[0]
    tags = result["hashtags"]
    assert 3 <= len(tags) <= 30
    assert all(tag.startswith("#") and len(tag) > 2 for tag in tags)
    assert len(set(tags)) == len(tags)


def test_caption_discloses_ai_and_fits_facebook_limits(store, settings):
    result = _copy(store, settings, seed=6)[0]
    assert "AI" in result["caption"]
    assert len(result["caption"]) <= 5000
    assert len(result["title"]) <= 200
    assert result["caption_signature"]
    assert result["hashtag_signature"]


def test_facebook_message_includes_caption_and_tags(store, settings):
    result = _copy(store, settings, seed=8)[0]
    message = captioner.build_facebook_message(result)
    assert result["caption"].splitlines()[0][:12] in message
    assert result["hashtags"][0] in message
    assert len(message) <= 6000


def test_every_category_produces_usable_copy(store, settings):
    from app import prompts

    for category in prompts.CATEGORY_LABELS:
        result = _copy(store, settings, category=category, seed=12)[0]
        assert result["title"].strip()
        assert result["caption"].strip()
        assert result["hashtags"]
