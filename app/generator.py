"""Generation pipeline: blueprint -> free image provider -> dedupe -> caption -> review."""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from app import captioner, dedupe, providers, randomizer, storage as storage_module

LOGGER = logging.getLogger(__name__)

IMAGE_ATTEMPTS = 5


class GenerationError(RuntimeError):
    """Raised when a post could not be produced."""


@dataclass
class GenerationOutcome:
    created: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "skipped": self.skipped,
            "errors": self.errors,
            "created_count": len(self.created),
            "skipped_count": len(self.skipped),
        }


def _normalise_image(data: bytes, settings) -> bytes:
    """Decode, crop to the configured aspect ratio and re-encode as JPEG."""
    try:
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            fitted = ImageOps.fit(
                image,
                (settings.image_width, settings.image_height),
                method=Image.LANCZOS,
                centering=(0.5, 0.5),
            )
            buffer = BytesIO()
            fitted.save(buffer, format="JPEG", quality=settings.jpeg_quality, optimize=True)
            return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001 - any decode failure is a provider failure
        raise GenerationError(f"Provider returned an unreadable image: {exc.__class__.__name__}") from exc


def _render_image(settings, blueprint, provider_name: str | None = None):
    """Try the selected provider, then the fallback. Returns (bytes, provider, notes)."""
    names: list[str] = []
    for name in (provider_name or settings.image_provider, settings.fallback_provider):
        if name and name not in names:
            names.append(name)

    request = providers.ImageRequest(
        prompt=blueprint.prompt,
        negative_prompt=blueprint.negative_prompt,
        width=settings.image_width,
        height=settings.image_height,
        seed=blueprint.seed,
    )

    problems: list[str] = []
    for name in names:
        provider = providers.get_provider(name, settings)
        if not provider.available():
            problems.append(f"{name}: not configured")
            continue
        try:
            result = provider.generate(request)
            return result, problems
        except providers.ProviderError as exc:
            problems.append(f"{name}: {exc}")
            LOGGER.warning("Image provider %s failed: %s", name, exc)

    raise GenerationError("All image providers failed. " + " | ".join(problems))


def generate_post(
    storage,
    settings,
    category: str | None = None,
    provider_name: str | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Create exactly one unique, non-duplicate post and return it."""
    rng = rng or random.Random()
    rejections: list[str] = []

    for _ in range(IMAGE_ATTEMPTS):
        blueprint = randomizer.build_unique_blueprint(storage, category=category, rng=rng)

        result, problems = _render_image(settings, blueprint, provider_name)
        image_bytes = _normalise_image(result.data, settings)
        hashes = dedupe.hash_image_bytes(image_bytes)

        duplicate = storage.find_duplicate(
            hashes["dhash"],
            hashes["ahash"],
            hashes["sha256"],
            settings.phash_threshold,
        )
        if duplicate:
            rejections.append(
                f"duplicate of {duplicate['id']} ({duplicate['reason']}, distance {duplicate['distance']})"
            )
            storage.add_event(
                None,
                "duplicate_rejected",
                f"Rejected {blueprint.category} image: {rejections[-1]}",
            )
            continue

        content = captioner.create_caption(storage, blueprint, settings=settings, rng=rng)

        post_id = uuid.uuid4().hex[:12]
        image_path = Path(storage.media_dir) / f"{post_id}.jpg"
        image_path.write_bytes(image_bytes)

        status = "approved" if not settings.require_approval else "pending"
        fields = {
            "id": post_id,
            "category": blueprint.category,
            "status": status,
            "title": content["title"],
            "caption": content["caption"],
            "hashtags": content["hashtags"],
            "prompt": blueprint.prompt,
            "negative_prompt": blueprint.negative_prompt,
            "blueprint": blueprint.to_dict(),
            "seed": blueprint.seed,
            "provider": result.provider,
            "image_path": str(image_path),
            "image_sha256": hashes["sha256"],
            "phash": hashes["dhash"],
            "ahash": hashes["ahash"],
            "prompt_fingerprint": blueprint.fingerprint,
            "caption_signature": content["caption_signature"],
            "hashtag_signature": content["hashtag_signature"],
        }
        if not settings.require_approval:
            fields["approved_at"] = storage_module.utcnow()

        try:
            storage.create_post(fields)
        except Exception:
            image_path.unlink(missing_ok=True)
            raise

        note = f"Generated {blueprint.category} photo via {result.provider}"
        if problems:
            note += f" (fallback after: {'; '.join(problems)})"
        storage.add_event(post_id, "generated", note)
        return storage.get_post(post_id)

    raise GenerationError(
        "Could not create a non-duplicate photo after "
        f"{IMAGE_ATTEMPTS} attempts. " + " | ".join(rejections[-3:])
    )


def generate_batch(
    storage,
    settings,
    count: int = 1,
    category: str | None = None,
    provider_name: str | None = None,
    rng: random.Random | None = None,
) -> GenerationOutcome:
    """Generate several posts, continuing after individual failures."""
    outcome = GenerationOutcome()
    for _ in range(max(1, count)):
        try:
            outcome.created.append(generate_post(storage, settings, category, provider_name, rng))
        except (GenerationError, randomizer.UniquenessError) as exc:
            message = str(exc)
            outcome.errors.append(message)
            outcome.skipped.append({"reason": message})
            storage.add_event(None, "generation_failed", message)
    return outcome
