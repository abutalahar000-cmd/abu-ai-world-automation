"""Image provider interface shared by every backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    """Raised when an image backend cannot produce an image."""


@dataclass(frozen=True)
class ImageRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 1080
    height: int = 1080
    seed: int = 0


@dataclass(frozen=True)
class ImageResult:
    data: bytes
    provider: str
    mime: str = "image/jpeg"
    meta: dict = field(default_factory=dict)


class ImageProvider(ABC):
    """A free / open-source image backend."""

    name = "base"
    requires_credentials = False
    notes = ""
    #: True when the backend is a diffusion/AI model rather than offline artwork.
    is_ai = True
    #: True only for the offline procedural backend.
    is_placeholder = False

    def __init__(self, settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return True

    def status(self) -> dict:
        return {
            "name": self.name,
            "available": self.available(),
            "requires_credentials": self.requires_credentials,
            "notes": self.notes,
            "is_ai": self.is_ai,
            "is_placeholder": self.is_placeholder,
            "selected": self.name == self.settings.image_provider,
        }

    @abstractmethod
    def generate(self, request: ImageRequest) -> ImageResult:
        """Return encoded image bytes or raise :class:`ProviderError`."""
