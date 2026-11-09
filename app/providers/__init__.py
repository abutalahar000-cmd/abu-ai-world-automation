"""Provider registry."""

from __future__ import annotations

from app.providers.base import ImageProvider, ImageRequest, ImageResult, ProviderError
from app.providers.huggingface import HuggingFaceProvider
from app.providers.local_sd import LocalStableDiffusionProvider
from app.providers.placeholder import PlaceholderProvider
from app.providers.pollinations import PollinationsProvider

PROVIDERS = {
    "pollinations": PollinationsProvider,
    "huggingface": HuggingFaceProvider,
    "local": LocalStableDiffusionProvider,
    "placeholder": PlaceholderProvider,
}

__all__ = [
    "ImageProvider",
    "ImageRequest",
    "ImageResult",
    "ProviderError",
    "PROVIDERS",
    "get_provider",
    "provider_status",
]


def get_provider(name: str | None, settings) -> ImageProvider:
    key = (name or settings.image_provider or "pollinations").lower()
    factory = PROVIDERS.get(key)
    if factory is None:
        raise ProviderError(f"Unknown image provider: {name}")
    return factory(settings)


def provider_status(settings) -> list[dict]:
    """Configuration status for the dashboard (no credentials are exposed)."""
    return [factory(settings).status() for factory in PROVIDERS.values()]
