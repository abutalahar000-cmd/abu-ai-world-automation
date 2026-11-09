"""Blueprint uniqueness and category coverage."""

from __future__ import annotations

import random

from app import prompts, randomizer


def test_every_category_builds_a_blueprint(store):
    for category in prompts.CATEGORY_LABELS:
        blueprint = randomizer.build_unique_blueprint(store, category=category, rng=random.Random(7))
        assert blueprint.category == category
        assert blueprint.prompt.strip()
        assert blueprint.negative_prompt.strip()
        assert blueprint.fingerprint
        assert blueprint.attributes


def test_girls_blueprints_never_repeat_and_vary(store):
    rng = random.Random(2024)
    blueprints = [
        randomizer.build_unique_blueprint(store, category="girls", rng=rng) for _ in range(25)
    ]
    assert len({bp.fingerprint for bp in blueprints}) == 25
    assert len({bp.prompt for bp in blueprints}) == 25

    common = set(blueprints[0].attributes)
    for bp in blueprints[1:]:
        common &= set(bp.attributes)
    varying = [key for key in common if len({bp.attributes[key] for bp in blueprints}) > 1]
    # appearance, outfit, pose, background and camera angle must all rotate
    assert len(varying) >= 5


def test_boys_blueprints_differ_in_appearance(store):
    rng = random.Random(11)
    blueprints = [
        randomizer.build_unique_blueprint(store, category="boys", rng=rng) for _ in range(20)
    ]
    assert len({bp.fingerprint for bp in blueprints}) == 20
    assert len({bp.prompt for bp in blueprints}) == 20


def test_random_category_selection_spreads_across_categories(store):
    rng = random.Random(3)
    categories = {
        randomizer.build_unique_blueprint(store, category=None, rng=rng).category
        for _ in range(150)
    }
    assert len(categories) >= 6
    assert categories <= set(prompts.CATEGORY_LABELS)


def test_fingerprint_changes_with_any_attribute():
    first = randomizer.fingerprint("girls", "person", {"hair": "sleek bob", "pose": "walking"})
    second = randomizer.fingerprint("girls", "person", {"hair": "sleek bob", "pose": "sitting"})
    third = randomizer.fingerprint("girls", "person", {"hair": "curly afro", "pose": "walking"})
    assert len({first, second, third}) == 3


def test_scene_categories_have_no_people(store):
    for category in ("food", "nature", "architecture"):
        blueprint = randomizer.build_unique_blueprint(store, category=category, rng=random.Random(5))
        assert blueprint.kind != "person"
        assert "person" not in blueprint.prompt.lower().split()
