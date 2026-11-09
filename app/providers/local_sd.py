"""Self-hosted Stable Diffusion provider (AUTOMATIC1111 / Forge web UI API).

Fully open source and free to run locally. Point ``LOCAL_SD_URL`` at your own
instance; no external service is contacted.
"""

from __future__ import annotations

import base64
import binascii

import requests

from app import quality
from app.providers.base import ImageProvider, ImageRequest, ImageResult, ProviderError


class LocalStableDiffusionProvider(ImageProvider):
    name = "local"
    requires_credentials = False
    notes = "Your own Stable Diffusion Web UI (AUTOMATIC1111/Forge) at LOCAL_SD_URL. Offline and free."

    def available(self) -> bool:
        return bool(self.settings.local_sd_url)

    def generate(self, request: ImageRequest) -> ImageResult:
        url = f"{self.settings.local_sd_url}/sdapi/v1/txt2img"
        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
            "steps": self.settings.local_sd_steps,
            "cfg_scale": self.settings.local_sd_cfg_scale,
            "sampler_name": "DPM++ 2M Karras",
        }
        try:
            response = requests.post(url, json=payload, timeout=300)
        except requests.RequestException as exc:
            raise ProviderError(
                f"Local Stable Diffusion is unreachable at {self.settings.local_sd_url}."
            ) from exc

        if response.status_code != 200:
            raise ProviderError(f"Local Stable Diffusion returned HTTP {response.status_code}.")

        try:
            images = response.json().get("images") or []
            encoded = images[0].split(",", 1)[-1]
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, KeyError, IndexError, binascii.Error) as exc:
            raise ProviderError("Local Stable Diffusion returned an unexpected payload.") from exc

        if len(data) < 5_000:
            raise ProviderError("Local Stable Diffusion returned an empty image.")

        try:
            measured = quality.validate_photo(data, provider=self.name)
        except quality.ImageValidationError as exc:
            raise ProviderError(str(exc)) from exc

        return ImageResult(
            data=data,
            provider=self.name,
            mime="image/png",
            meta={
                "model": "local",
                "seed": request.seed,
                "is_ai": True,
                "quality": measured.to_dict(),
            },
        )
