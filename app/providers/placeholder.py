"""Offline procedural image provider.

This exists so the full pipeline (generation, dedupe, captions, review,
publishing) works with no network access and no paid API. It produces abstract
artwork, **not** a photograph, and marks itself as a placeholder in metadata so
the dashboard can label it honestly.
"""

from __future__ import annotations

import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

from app.providers.base import ImageProvider, ImageRequest, ImageResult

PALETTES = {
    "girls": [(250, 218, 221), (247, 202, 201), (255, 245, 230), (216, 191, 216)],
    "boys": [(40, 54, 74), (86, 108, 134), (168, 186, 200), (233, 240, 245)],
    "lifestyle": [(246, 240, 231), (223, 206, 184), (176, 155, 132), (108, 96, 84)],
    "fashion": [(24, 24, 27), (196, 164, 132), (240, 236, 229), (120, 60, 70)],
    "travel": [(240, 180, 120), (58, 120, 140), (250, 235, 205), (200, 90, 60)],
    "food": [(220, 120, 70), (250, 225, 180), (110, 60, 40), (140, 170, 90)],
    "nature": [(60, 110, 80), (140, 175, 130), (210, 225, 200), (90, 130, 150)],
    "fitness": [(35, 45, 55), (230, 120, 60), (200, 210, 215), (90, 160, 170)],
    "street": [(30, 30, 40), (230, 90, 120), (70, 200, 220), (240, 220, 90)],
    "architecture": [(200, 200, 195), (120, 130, 140), (60, 70, 80), (235, 235, 230)],
}


class PlaceholderProvider(ImageProvider):
    name = "placeholder"
    requires_credentials = False
    notes = "Offline procedural artwork for testing the pipeline. Not a photograph."

    def generate(self, request: ImageRequest) -> ImageResult:
        rng = random.Random(request.seed or 0)
        width, height = request.width, request.height
        category = self._category_from_prompt(request.prompt)
        palette = PALETTES.get(category, PALETTES["lifestyle"])

        start, end = rng.sample(palette, 2)
        image = Image.new("RGB", (width, height), start)
        gradient = Image.new("RGB", (1, height))
        for y in range(height):
            ratio = y / max(1, height - 1)
            gradient.putpixel(
                (0, y),
                tuple(int(start[channel] + (end[channel] - start[channel]) * ratio) for channel in range(3)),
            )
        image = gradient.resize((width, height), Image.BILINEAR)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for _ in range(rng.randint(6, 10)):
            radius = rng.randint(width // 10, width // 2)
            centre_x = rng.randint(0, width)
            centre_y = rng.randint(0, height)
            colour = (*rng.choice(palette), rng.randint(50, 130))
            draw.ellipse(
                [centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius],
                fill=colour,
            )
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(8, width // 18)))
        image = Image.alpha_composite(image.convert("RGBA"), overlay)

        lines = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        line_draw = ImageDraw.Draw(lines)
        for _ in range(rng.randint(3, 6)):
            points = [
                (rng.randint(0, width), rng.randint(0, height)),
                (rng.randint(0, width), rng.randint(0, height)),
                (rng.randint(0, width), rng.randint(0, height)),
            ]
            line_draw.line(points, fill=(*rng.choice(palette), rng.randint(40, 110)), width=rng.randint(2, 7))
        image = Image.alpha_composite(image, lines.filter(ImageFilter.GaussianBlur(2)))

        noise = Image.effect_noise((width, height), 16).convert("RGB")
        image = Image.blend(image.convert("RGB"), noise, 0.06)

        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return ImageResult(
            data=buffer.getvalue(),
            provider=self.name,
            mime="image/png",
            meta={"placeholder": True, "seed": request.seed},
        )

    @staticmethod
    def _category_from_prompt(prompt: str) -> str:
        lowered = prompt.lower()
        for category in PALETTES:
            if category in lowered:
                return category
        if "food" in lowered or "dish" in lowered:
            return "food"
        if "nature" in lowered or "forest" in lowered:
            return "nature"
        return "lifestyle"
