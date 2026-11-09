"""Live availability checks for the image providers.

Each provider is called once with a real prompt so its status reflects what
actually works right now, not just whether configuration is present. A provider
is never reported as working on the strength of its settings alone, and the
offline placeholder is reported as artwork rather than an AI photo.
"""

from __future__ import annotations

import random

from app import prompts, quality, randomizer
from app.providers import PROVIDERS, get_provider
from app.providers.base import ImageRequest, ProviderError

CHECK_SIZE = 768
CHECK_SEED = 20260101


def check_request(settings) -> ImageRequest:
    """A representative lifestyle prompt used for every availability check."""
    blueprint = randomizer.build_blueprint("lifestyle", rng=random.Random(CHECK_SEED))
    return ImageRequest(
        prompt=prompts.render_prompt(blueprint.attributes, blueprint.category),
        negative_prompt=prompts.NEGATIVE_PROMPT,
        width=min(settings.image_width, CHECK_SIZE),
        height=min(settings.image_height, CHECK_SIZE),
        seed=CHECK_SEED,
    )


def check_provider(settings, name: str) -> dict:
    """Call one provider once and report exactly what came back."""
    provider = get_provider(name, settings)
    report: dict = {
        "provider": name,
        "is_ai": provider.is_ai,
        "is_placeholder": provider.is_placeholder,
        "available": provider.available(),
        "notes": provider.notes,
        "ok": False,
        "real_photo": False,
        "detail": "",
    }

    if not provider.available():
        report["detail"] = "Not configured: missing credentials or endpoint."
        return report

    try:
        result = provider.generate(check_request(settings))
    except ProviderError as exc:
        report["detail"] = f"Failed: {exc}"
        return report
    except Exception as exc:  # noqa: BLE001 - a check reports, it never crashes
        report["detail"] = f"Failed: {exc.__class__.__name__}: {exc}"
        return report

    report["bytes"] = len(result.data)
    report["mime"] = result.mime
    report["model"] = result.meta.get("model", "")

    try:
        measured = quality.validate_photo(result.data, provider=name)
    except quality.ImageValidationError as exc:
        report["detail"] = f"Returned an unusable image: {exc}"
        return report

    report["quality"] = measured.to_dict()
    report["ok"] = True
    report["real_photo"] = bool(provider.is_ai and measured.is_photographic)
    if provider.is_placeholder:
        report["detail"] = "Offline procedural artwork for tests - NOT a photograph."
    elif report["real_photo"]:
        report["detail"] = "Returned a real photographic image from a diffusion model."
    else:
        report["detail"] = "Returned an image but is not marked as a real model."
    return report


def check_all(settings, names=None) -> list[dict]:
    return [check_provider(settings, name) for name in (names or list(PROVIDERS))]
