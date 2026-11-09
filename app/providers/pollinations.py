"""Pollinations.ai provider - free, open, no account or API key required.

Docs: https://github.com/pollinations/pollinations
An optional free token raises rate limits but is never required.
"""

from __future__ import annotations

from urllib.parse import quote

import requests

from app.providers.base import ImageProvider, ImageRequest, ImageResult, ProviderError

BASE_URL = "https://image.pollinations.ai/prompt/"
MIN_BYTES = 5_000


class PollinationsProvider(ImageProvider):
    name = "pollinations"
    requires_credentials = False
    notes = "Free hosted open model (FLUX). No API key required; optional free token for higher limits."

    def generate(self, request: ImageRequest) -> ImageResult:
        prompt = " ".join(request.prompt.split())
        url = BASE_URL + quote(prompt, safe="")
        params = {
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
            "model": self.settings.pollinations_model or "flux",
            "nologo": "true",
            "enhance": "false",
        }
        headers = {"User-Agent": "AppJet-FacebookPhotoAutomation/1.0"}
        if self.settings.pollinations_token:
            headers["Authorization"] = f"Bearer {self.settings.pollinations_token}"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=180)
        except requests.RequestException as exc:
            raise ProviderError(f"Pollinations request failed: {exc.__class__.__name__}") from exc

        if response.status_code != 200:
            raise ProviderError(
                f"Pollinations returned HTTP {response.status_code}. "
                "Try again later or set FALLBACK_PROVIDER."
            )

        content_type = response.headers.get("content-type", "")
        data = response.content
        if not content_type.startswith("image/"):
            raise ProviderError(f"Pollinations returned non-image content ({content_type or 'unknown'}).")
        if len(data) < MIN_BYTES:
            raise ProviderError("Pollinations returned an unexpectedly small image.")

        return ImageResult(
            data=data,
            provider=self.name,
            mime=content_type.split(";")[0] or "image/jpeg",
            meta={"model": params["model"], "seed": request.seed},
        )
