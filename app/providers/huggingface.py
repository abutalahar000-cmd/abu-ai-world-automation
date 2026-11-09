"""Hugging Face Inference API provider (free tier, open models).

Requires a free account token in ``HF_TOKEN``. No paid plan is needed for
occasional generation; if the free quota is exhausted the caller falls back to
the configured fallback provider.
"""

from __future__ import annotations

import requests

from app import quality
from app.providers.base import ImageProvider, ImageRequest, ImageResult, ProviderError

DEFAULT_ENDPOINT = "https://router.huggingface.co/hf-inference/models"


class HuggingFaceProvider(ImageProvider):
    name = "huggingface"
    requires_credentials = True
    notes = "Free-tier Hugging Face token with an open model such as FLUX.1-schnell."

    def available(self) -> bool:
        return bool(self.settings.hf_token)

    def generate(self, request: ImageRequest) -> ImageResult:
        if not self.settings.hf_token:
            raise ProviderError("HF_TOKEN is not set.")

        url = f"{DEFAULT_ENDPOINT}/{self.settings.hf_model}"
        payload = {
            "inputs": " ".join(request.prompt.split()),
            "parameters": {
                "width": request.width,
                "height": request.height,
                "seed": request.seed,
            },
        }
        if request.negative_prompt:
            payload["parameters"]["negative_prompt"] = request.negative_prompt

        headers = {
            "Authorization": f"Bearer {self.settings.hf_token}",
            "Accept": "image/png",
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=180)
        except requests.RequestException as exc:
            raise ProviderError(f"Hugging Face request failed: {exc.__class__.__name__}") from exc

        if response.status_code == 503:
            raise ProviderError(
                "Hugging Face is loading the model (HTTP 503). Retry shortly or use another provider."
            )
        if response.status_code != 200:
            raise ProviderError(f"Hugging Face returned HTTP {response.status_code}.")

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ProviderError("Hugging Face returned a non-image response (check model access).")

        try:
            measured = quality.validate_photo(response.content, provider=self.name)
        except quality.ImageValidationError as exc:
            raise ProviderError(str(exc)) from exc

        return ImageResult(
            data=response.content,
            provider=self.name,
            mime=content_type.split(";")[0] or "image/png",
            meta={
                "model": self.settings.hf_model,
                "seed": request.seed,
                "is_ai": True,
                "quality": measured.to_dict(),
            },
        )
