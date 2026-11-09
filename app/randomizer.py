"""Blueprint sampling with collision-aware uniqueness.

A blueprint is the complete attribute set for one photo. Its fingerprint is
stored with a UNIQUE constraint in SQLite, so the same combination can never be
generated twice. Recent per-field values are also excluded while sampling, which
keeps appearance, outfit, pose, background and camera angle rotating instead of
only guaranteeing a unique full combination.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from app import prompts

MAX_BLUEPRINT_ATTEMPTS = 60

AVOID_FIELDS = (
    "appearance_signature",
    "outfit",
    "pose",
    "background",
    "camera_angle",
    "subject",
    "setting",
)


class UniquenessError(RuntimeError):
    """Raised when no unused prompt combination can be found."""


@dataclass(frozen=True)
class Blueprint:
    category: str
    kind: str
    seed: int
    attributes: dict
    prompt: str
    negative_prompt: str
    fingerprint: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "kind": self.kind,
            "seed": self.seed,
            "attributes": self.attributes,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Blueprint":
        category = data.get("category", "lifestyle")
        attributes = data.get("attributes", {})
        return cls(
            category=category,
            kind=data.get("kind", attributes.get("kind", "scene")),
            seed=int(data.get("seed", 0)),
            attributes=attributes,
            prompt=prompts.render_prompt(attributes, category),
            negative_prompt=prompts.NEGATIVE_PROMPT,
            fingerprint=data.get("fingerprint", ""),
        )


def fingerprint(category: str, kind: str, attributes: dict) -> str:
    canonical = json.dumps(
        {"category": category, "kind": kind, "attributes": attributes},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pick(rng: random.Random, pool: list, avoid: set | None = None) -> str:
    """Sample from a pool, skipping recently used values when enough remain."""
    if avoid:
        filtered = [value for value in pool if value not in avoid]
        if len(filtered) >= 3:
            pool = filtered
    return rng.choice(pool)


def _appearance(rng: random.Random, avoid: dict) -> tuple[dict, str]:
    """Sample a facial/body appearance and avoid repeating recent signatures."""
    avoided = avoid.get("appearance_signature", set())
    appearance: dict = {}
    signature = ""
    for _ in range(12):
        appearance = {
            "heritage": rng.choice(prompts.HERITAGES),
            "hair_style": rng.choice(prompts.HAIR_STYLES),
            "hair_color": rng.choice(prompts.HAIR_COLORS),
            "eyes": rng.choice(prompts.EYES),
            "face": rng.choice(prompts.FACES),
        }
        signature = "|".join(appearance.values())
        if signature not in avoided:
            break
    return appearance, signature


def _camera_look(rng: random.Random, avoid: dict) -> dict:
    return {
        "camera_angle": _pick(rng, prompts.CAMERA_ANGLES, avoid.get("camera_angle")),
        "lens": rng.choice(prompts.LENSES),
        "lighting": rng.choice(prompts.LIGHTING),
        "time_of_day": rng.choice(prompts.TIMES_OF_DAY),
        "color_grade": rng.choice(prompts.COLOR_GRADES),
        "aesthetic": rng.choice(prompts.AESTHETICS),
    }


def _person_attributes(category: str, rng: random.Random, avoid: dict) -> dict:
    if category == "girls":
        gender = "woman"
    elif category == "boys":
        gender = "man"
    else:
        gender = rng.choice(["woman", "man"])

    appearance, signature = _appearance(rng, avoid)
    outfit_pool = prompts.OUTFITS.get(category, prompts.OUTFITS["lifestyle"])
    background_pool = prompts.BACKGROUNDS.get(category, prompts.BACKGROUNDS["lifestyle"])

    attributes = {
        "kind": "person",
        "gender": gender,
        "heritage": appearance["heritage"],
        "age": rng.choice(prompts.AGES[gender]),
        "hair_style": appearance["hair_style"],
        "hair_color": appearance["hair_color"],
        "eyes": appearance["eyes"],
        "face": appearance["face"],
        "build": rng.choice(prompts.BUILDS),
        "expression": rng.choice(prompts.EXPRESSIONS),
        "outfit": _pick(rng, outfit_pool, avoid.get("outfit")),
        "accessories": rng.choice(prompts.ACCESSORIES),
        "pose": _pick(rng, prompts.POSES, avoid.get("pose")),
        "background": _pick(rng, background_pool, avoid.get("background")),
        "appearance_signature": signature,
    }
    attributes.update(_camera_look(rng, avoid))
    return attributes


def _scene_pools(category: str) -> tuple[list, list, list, list]:
    if category == "food":
        return (
            prompts.FOOD_DISHES,
            prompts.FOOD_DETAILS,
            prompts.FOOD_SETTINGS,
            prompts.FOOD_PROPS,
        )
    if category == "nature":
        return prompts.NATURE_SCENES, prompts.NATURE_DETAILS, prompts.NATURE_CONDITIONS, []
    if category == "architecture":
        return (
            prompts.ARCHITECTURE_BUILDINGS,
            prompts.ARCHITECTURE_DETAILS,
            prompts.ARCHITECTURE_CONDITIONS,
            [],
        )
    if category == "travel":
        return prompts.TRAVEL_SCENES, prompts.TRAVEL_DETAILS, [], []
    return prompts.LIFESTYLE_SCENES, prompts.LIFESTYLE_DETAILS, [], []


def _scene_attributes(category: str, rng: random.Random, avoid: dict) -> dict:
    subjects, details, settings, props = _scene_pools(category)
    attributes = {
        "kind": "scene",
        "subject": _pick(rng, subjects, avoid.get("subject")),
        "detail": rng.choice(details),
    }
    if settings:
        attributes["setting"] = _pick(rng, settings, avoid.get("setting"))
    if props:
        attributes["props"] = rng.choice(props)
    attributes.update(_camera_look(rng, avoid))
    return attributes


def build_blueprint(
    category: str | None = None,
    rng: random.Random | None = None,
    avoid: dict | None = None,
) -> Blueprint:
    """Sample one blueprint (no database check yet)."""
    rng = rng or random.Random()
    avoid = avoid or {}
    chosen = category or rng.choice(prompts.CATEGORIES)
    if chosen not in prompts.CATEGORY_LABELS:
        raise ValueError(f"Unknown category: {chosen}")

    if chosen in prompts.PERSON_CATEGORIES:
        kind = "person"
    elif chosen in prompts.MIXED_CATEGORIES:
        kind = "person" if rng.random() < prompts.MIX_PROBABILITY[chosen] else "scene"
    else:
        kind = "scene"

    attributes = (
        _person_attributes(chosen, rng, avoid)
        if kind == "person"
        else _scene_attributes(chosen, rng, avoid)
    )
    seed = rng.randrange(1, 2**31 - 1)
    return Blueprint(
        category=chosen,
        kind=kind,
        seed=seed,
        attributes=attributes,
        prompt=prompts.render_prompt(attributes, chosen),
        negative_prompt=prompts.NEGATIVE_PROMPT,
        fingerprint=fingerprint(chosen, kind, attributes),
    )


def recent_avoid_sets(storage, category: str | None = None, limit: int = 40) -> dict:
    """Collect recently used values so new photos visibly differ from old ones."""
    avoid = {field: set() for field in AVOID_FIELDS}
    for blueprint in storage.recent_blueprints(category=category, limit=limit):
        attributes = blueprint.get("attributes", {})
        for field in AVOID_FIELDS:
            value = attributes.get(field)
            if value:
                avoid[field].add(value)
    return avoid


def build_unique_blueprint(
    storage,
    category: str | None = None,
    rng: random.Random | None = None,
    attempts: int = MAX_BLUEPRINT_ATTEMPTS,
) -> Blueprint:
    """Sample until the fingerprint has never been used before."""
    rng = rng or random.Random()
    avoid = recent_avoid_sets(storage, category)
    for _ in range(attempts):
        blueprint = build_blueprint(category, rng, avoid)
        if not storage.prompt_fingerprint_exists(blueprint.fingerprint):
            return blueprint
    raise UniquenessError(
        "Could not find an unused prompt combination. Try another category "
        "or remove some old posts."
    )
