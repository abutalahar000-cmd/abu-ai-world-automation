"""Unique Facebook titles, captions and hashtags.

Templates are local and free; no paid text API is used. Optional local Ollama
support can add a hook line, but the deterministic template path always works.
"""

from __future__ import annotations

import hashlib
import json
import random
import re

from app import prompts

HOOKS = [
    "Some days just look better in soft light.",
    "This is your sign to slow down.",
    "Light like this never waits.",
    "A small moment worth keeping.",
    "Today's mood, in one frame.",
    "Not every story needs words.",
    "Found a little magic in the ordinary.",
    "The kind of scene you save for later.",
    "Chasing good light and better moods.",
    "A quiet reminder to notice more.",
    "Some frames feel like a deep breath.",
    "Making room for slow, beautiful things.",
    "Stopped for a second and this happened.",
    "The best moments rarely announce themselves.",
    "Nothing staged, everything felt.",
]

CTAS = [
    "Save this for your next mood board 📌",
    "Which detail is your favourite? 👇",
    "Tag someone who'd love this 💬",
    "Follow for more everyday beauty ✨",
    "Double tap if this speaks to you ❤️",
    "Tell us: city or coast? 🌊",
    "Would you frame this? 🖼️",
    "Drop a colour in the comments 🎨",
    "Share this with your favourite person 💫",
    "What does this remind you of? ☁️",
]

FOOTER = "🤖 AI-generated image"

TITLE_PATTERNS = [
    "Golden Light, {vibe} Energy",
    "{vibe} in {place}",
    "A {vibe} Kind of Day",
    "{subject} Diaries: {vibe}",
    "Chasing {vibe} in {place}",
    "Soft Light and {vibe}",
    "{place} Mornings",
    "The {vibe} Edit",
    "Everyday {subject}, Elevated",
    "{vibe} Mood, {place} Views",
    "Caught in {vibe}",
    "{subject} Story: {place}",
    "Where {vibe} Meets {place}",
    "Notes From {place}",
    "Simply {vibe}",
    "{vibe} Frames From {place}",
    "A Little {vibe} Never Hurts",
    "{place}, {vibe}, and Good Light",
    "{vibe} Looks Good on {subject}",
    "Slow {vibe} in {place}",
]

VIBES = [
    "Golden Hour",
    "Slow Morning",
    "Soft Focus",
    "Quiet Luxury",
    "Weekend",
    "Neon",
    "Sun-Kissed",
    "Off-Duty",
    "Editorial",
    "Dreamy",
    "Effortless",
    "City",
    "Coastal",
    "Warm Minimal",
    "Playful",
    "Timeless",
    "Vintage",
    "Fresh",
]

FLAVOR = {
    "girls": {
        "subjects": ["Portrait", "Her", "Girl", "Style"],
        "places": ["Golden Hour", "the Balcony", "the Studio", "Old Town", "the Garden"],
        "body": [
            "Loved how the light landed here.",
            "Simple outfit, strong mood.",
            "A little confidence goes a long way.",
            "Soft tones, sharp details.",
            "The kind of frame that feels like a memory.",
            "Styled for the moment, not the algorithm.",
        ],
        "tags": ["#portraitphotography", "#womensfashion", "#portraitmood", "#femalephotography", "#styleinspo"],
    },
    "boys": {
        "subjects": ["Portrait", "Him", "Menswear", "The Fit"],
        "places": ["the Rooftop", "Downtown", "the Studio", "the Boardwalk", "Old Town"],
        "body": [
            "Clean lines and good light.",
            "The fit did the talking.",
            "Quiet confidence, no effort.",
            "Classic pieces, modern mood.",
            "Sharp tailoring meets soft daylight.",
            "A portrait that keeps it simple.",
        ],
        "tags": ["#mensfashion", "#mensstyle", "#portraitphotography", "#menswear", "#streetstyle"],
    },
    "lifestyle": {
        "subjects": ["Slow Living", "Everyday", "Home", "The Morning"],
        "places": ["the Kitchen", "the Balcony", "a Sunday", "the Corner Cafe", "Home"],
        "body": [
            "Small rituals make the best days.",
            "Slow mornings are underrated.",
            "Beauty lives in the everyday.",
            "Nothing special, everything lovely.",
            "A corner of the day worth keeping.",
            "The simple things, framed properly.",
        ],
        "tags": ["#slowliving", "#lifestylephotography", "#everydaymoments", "#minimalaesthetic", "#homestyling"],
    },
    "fashion": {
        "subjects": ["The Look", "Editorial", "Street Style", "The Fit"],
        "places": ["the Studio", "the Runway", "Downtown", "the Atelier", "Backstage"],
        "body": [
            "Texture, silhouette, attitude.",
            "This look needed no caption.",
            "Tailoring with a soft edge.",
            "Statement pieces, quiet palette.",
            "Fashion is just confidence, styled.",
            "A fit worth saving to the mood board.",
        ],
        "tags": ["#fashioneditorial", "#ootd", "#styleinspo", "#fashionphotography", "#outfitideas"],
    },
    "travel": {
        "subjects": ["Wander", "The Journey", "Postcard", "Travel"],
        "places": ["the Coast", "Old Town", "the Mountains", "the Islands", "Somewhere New"],
        "body": [
            "Went for the view, stayed for the light.",
            "New streets, same curiosity.",
            "The kind of place you linger in.",
            "Pack light, look around.",
            "Every corner had a story.",
            "Travel days always taste better.",
        ],
        "tags": ["#travelphotography", "#wanderlust", "#travelgram", "#exploremore", "#destinationphotography"],
    },
    "food": {
        "subjects": ["On the Table", "The Plate", "Kitchen Notes", "Today's Dish"],
        "places": ["the Kitchen", "the Table", "a Slow Lunch", "the Cafe", "Home"],
        "body": [
            "Made with butter and good intentions.",
            "Simple ingredients, proper flavour.",
            "The kind of plate you photograph first.",
            "Fresh, warm, gone in minutes.",
            "Recipes are better with patience.",
            "A small feast for no reason at all.",
        ],
        "tags": ["#foodphotography", "#foodstyling", "#homemade", "#foodie", "#recipeinspiration"],
    },
    "nature": {
        "subjects": ["Wild", "The Outdoors", "Landscape", "Nature"],
        "places": ["the Forest", "the Coast", "the Valley", "the Lake", "the Hills"],
        "body": [
            "Nature does not need a filter.",
            "The quietest places say the most.",
            "Fresh air and long views.",
            "Nothing but weather and light.",
            "A reminder that slow is beautiful.",
            "Went outside and felt better.",
        ],
        "tags": ["#naturephotography", "#landscapephotography", "#outdoors", "#naturelover", "#wildandfree"],
    },
    "fitness": {
        "subjects": ["Training", "The Work", "Movement", "Progress"],
        "places": ["the Studio", "the Track", "the Gym", "the Park", "the Courts"],
        "body": [
            "Showing up is the whole secret.",
            "Strong is a habit, not a look.",
            "Movement that feels good.",
            "Small gains, loud progress.",
            "Sweat, stretch, repeat.",
            "Built steady, not overnight.",
        ],
        "tags": ["#fitnessmotivation", "#fitlifestyle", "#trainingday", "#activewear", "#wellnessjourney"],
    },
    "street": {
        "subjects": ["Street", "City Life", "The Block", "After Hours"],
        "places": ["Downtown", "the Alley", "the Crossing", "the Night Market", "the Station"],
        "body": [
            "The city posed without asking.",
            "Neon looks better on film.",
            "Street light and strange timing.",
            "Ordinary corners, extraordinary light.",
            "Late trains and longer stories.",
            "Caught the city mid-thought.",
        ],
        "tags": ["#streetphotography", "#citylife", "#urbanphotography", "#nightphotography", "#documentarystyle"],
    },
    "architecture": {
        "subjects": ["Structure", "The Building", "Lines", "Architecture"],
        "places": ["the Facade", "Old Town", "the Museum", "the Tower", "the Courtyard"],
        "body": [
            "Good architecture knows how to be quiet.",
            "Lines, shadow, geometry.",
            "Built to be looked up at.",
            "Concrete never looked this warm.",
            "The details carry the whole story.",
            "A study in light and structure.",
        ],
        "tags": ["#architecturephotography", "#modernarchitecture", "#buildingdesign", "#minimalism", "#archilovers"],
    },
}

BASE_TAGS = [
    "#photography",
    "#photooftheday",
    "#instadaily",
    "#visualsoflife",
    "#creativephotography",
    "#lightandshadow",
    "#aesthetic",
    "#dailyinspiration",
    "#moodboard",
    "#framedaily",
    "#contentcreator",
    "#artofvisuals",
]

ENGAGEMENT_TAGS = [
    "#explorepage",
    "#trending",
    "#discover",
    "#community",
    "#dailyfeature",
    "#photogram",
]

STOP_WORDS = {"a", "an", "the", "with", "in", "on", "at", "of", "and", "to", "for", "by", "from"}


def _signature(text: str) -> str:
    normalised = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _tagify(phrase: str) -> str:
    words = [word for word in re.split(r"[^0-9A-Za-z]+", phrase) if word]
    kept = [word for word in words if word.lower() not in STOP_WORDS][:3]
    if not kept:
        return ""
    tag = "#" + "".join(word[:1].upper() + word[1:] for word in kept)
    return tag if len(tag) > 2 else ""


def _flavor(category: str) -> dict:
    return FLAVOR.get(category, FLAVOR["lifestyle"])


def _make_title(category: str, attributes: dict, rng: random.Random) -> str:
    flavor = _flavor(category)
    pattern = rng.choice(TITLE_PATTERNS)
    place = attributes.get("background") or attributes.get("setting") or rng.choice(flavor["places"])
    return pattern.format(
        vibe=rng.choice(VIBES),
        place=rng.choice(flavor["places"]),
        subject=rng.choice(flavor["subjects"]),
    ) if "{place}" not in pattern else pattern.format(
        vibe=rng.choice(VIBES),
        place=place.title()[:40],
        subject=rng.choice(flavor["subjects"]),
    )


def _candidate_tags(category: str, attributes: dict, rng: random.Random) -> list[str]:
    pool = list(BASE_TAGS) + list(_flavor(category)["tags"]) + list(ENGAGEMENT_TAGS)

    derived_sources = [
        attributes.get("aesthetic"),
        attributes.get("time_of_day"),
        attributes.get("background"),
        attributes.get("subject"),
        attributes.get("outfit"),
        prompts.CATEGORY_LABELS.get(category, ""),
        category,
    ]
    for source in derived_sources:
        if not source:
            continue
        tag = _tagify(str(source))
        if tag:
            pool.append(tag)

    seen: set[str] = set()
    unique: list[str] = []
    for tag in pool:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            unique.append(tag)
    rng.shuffle(unique)
    return unique


def _ollama_hook(settings, blueprint) -> str | None:
    """Optional local LLM hook. Returns None on any failure."""
    if not settings.ollama_url:
        return None
    try:
        import requests

        prompt = (
            "Write one short, natural Facebook caption opener (max 14 words) for a "
            f"{blueprint.category} photo. Do not use hashtags, quotes or emojis. "
            f"Scene: {blueprint.prompt[:400]}"
        )
        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if response.status_code != 200:
            return None
        text = (response.json().get("response") or "").strip().splitlines()[0].strip()
        return text if 10 <= len(text) <= 140 else None
    except Exception:  # noqa: BLE001 - optional enhancement must never break generation
        return None


def create_caption(storage, blueprint, settings=None, rng: random.Random | None = None) -> dict:
    """Build a title, caption and hashtag set that has never been used before."""
    rng = rng or random.Random()
    category = blueprint.category
    attributes = blueprint.attributes
    flavor = _flavor(category)

    hook = None
    if settings is not None:
        hook = _ollama_hook(settings, blueprint)
    if not hook:
        hook = rng.choice(HOOKS)

    title = None
    for _ in range(40):
        candidate = _make_title(category, attributes, rng)
        if not storage.title_exists(candidate):
            title = candidate
            break
    if title is None:
        title = f"{_make_title(category, attributes, rng)} {rng.randint(2, 99)}"

    caption_signature = ""
    caption = ""
    for _ in range(40):
        body = rng.choice(flavor["body"])
        cta = rng.choice(CTAS)
        caption = f"{hook}\n\n{body}\n\n{cta}\n\n{FOOTER}"
        caption_signature = _signature(caption)
        if not storage.signature_exists("caption_signature", caption_signature):
            break

    tags: list[str] = []
    hashtag_signature = ""
    for _ in range(40):
        pool = _candidate_tags(category, attributes, rng)
        tags = pool[: rng.randint(9, 12)]
        hashtag_signature = _signature(" ".join(sorted(tag.lower() for tag in tags)))
        if not storage.signature_exists("hashtag_signature", hashtag_signature):
            break

    return {
        "title": title,
        "caption": caption,
        "hashtags": tags,
        "caption_signature": caption_signature,
        "hashtag_signature": hashtag_signature,
        "hashtag_text": " ".join(tags),
    }


def caption_signature(text: str) -> str:
    """Exposed for tests and manual edits."""
    return _signature(text)


def hashtag_signature(tags: list[str]) -> str:
    return _signature(" ".join(sorted(tag.lower() for tag in tags)))


def build_facebook_message(post: dict) -> str:
    """Message body sent to the Graph API."""
    tags = post.get("hashtags") or []
    parts = [post.get("title", "").strip(), post.get("caption", "").strip(), " ".join(tags).strip()]
    return "\n\n".join(part for part in parts if part)[:63000]
