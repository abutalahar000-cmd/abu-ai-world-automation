"""Environment-driven configuration.

Every credential is read from the process environment (or a local ``.env``
file that is git-ignored). Nothing sensitive is ever written to the database,
logged, or rendered into the dashboard.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv is optional at import time
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements

    def load_dotenv(*_args, **_kwargs):  # type: ignore[misc]
        return False


BASE_DIR = Path(__file__).resolve().parent.parent

PROVIDER_CHOICES = ("pollinations", "huggingface", "local", "placeholder")


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _bool(name: str, default: bool = False) -> bool:
    raw = _str(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int | None = None) -> int:
    try:
        value = int(_str(name, str(default)))
    except ValueError:
        return default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _float(name: str, default: float) -> float:
    try:
        return float(_str(name, str(default)))
    except ValueError:
        return default


def _path(name: str, default: str) -> Path:
    raw = _str(name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings resolved from the environment."""

    fb_page_id: str
    fb_page_access_token: str
    graph_api_version: str

    image_provider: str
    fallback_provider: str
    pollinations_token: str
    pollinations_model: str
    hf_token: str
    hf_model: str
    local_sd_url: str
    local_sd_steps: int
    local_sd_cfg_scale: float

    require_approval: bool
    auto_publish: bool
    posts_per_run: int
    scheduler_interval_minutes: int

    phash_threshold: int
    image_width: int
    image_height: int
    jpeg_quality: int

    database_path: Path
    media_dir: Path

    dashboard_password: str
    ollama_url: str
    ollama_model: str
    host: str
    port: int

    # -- derived ---------------------------------------------------------
    @property
    def facebook_configured(self) -> bool:
        return bool(self.fb_page_id and self.fb_page_access_token)

    @property
    def facebook_missing(self) -> list[str]:
        missing: list[str] = []
        if not self.fb_page_id:
            missing.append("FB_PAGE_ID")
        if not self.fb_page_access_token:
            missing.append("FB_PAGE_ACCESS_TOKEN")
        return missing

    @property
    def image_generation_configured(self) -> bool:
        provider = self.image_provider
        if provider == "pollinations":
            return True  # free, no account required
        if provider == "huggingface":
            return bool(self.hf_token)
        if provider == "local":
            return bool(self.local_sd_url)
        return provider == "placeholder"

    def public_status(self) -> dict:
        """Safe-to-render configuration summary (never includes secrets)."""
        return {
            "facebook_configured": self.facebook_configured,
            "facebook_missing": self.facebook_missing,
            "image_provider": self.image_provider,
            "fallback_provider": self.fallback_provider,
            "image_generation_configured": self.image_generation_configured,
            "require_approval": self.require_approval,
            "auto_publish": self.auto_publish,
            "graph_api_version": self.graph_api_version,
            "ollama_enabled": bool(self.ollama_url),
            "dashboard_password_set": bool(self.dashboard_password),
        }


def load_settings() -> Settings:
    """Read settings from the environment, loading ``.env`` when present."""
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    provider = _str("IMAGE_PROVIDER", "pollinations").lower()
    if provider not in PROVIDER_CHOICES:
        provider = "pollinations"

    fallback = _str("FALLBACK_PROVIDER", "placeholder").lower()
    if fallback not in PROVIDER_CHOICES:
        fallback = "placeholder"

    return Settings(
        fb_page_id=_str("FB_PAGE_ID"),
        fb_page_access_token=_str("FB_PAGE_ACCESS_TOKEN"),
        graph_api_version=_str("GRAPH_API_VERSION", "v23.0"),
        image_provider=provider,
        fallback_provider=fallback,
        pollinations_token=_str("POLLINATIONS_TOKEN"),
        pollinations_model=_str("POLLINATIONS_MODEL", "flux"),
        hf_token=_str("HF_TOKEN"),
        hf_model=_str("HF_MODEL", "black-forest-labs/FLUX.1-schnell"),
        local_sd_url=_str("LOCAL_SD_URL", "http://127.0.0.1:7860").rstrip("/"),
        local_sd_steps=_int("LOCAL_SD_STEPS", 28, minimum=1),
        local_sd_cfg_scale=_float("LOCAL_SD_CFG_SCALE", 6.5),
        require_approval=_bool("REQUIRE_APPROVAL", True),
        auto_publish=_bool("AUTO_PUBLISH", False),
        posts_per_run=_int("POSTS_PER_RUN", 3, minimum=1),
        scheduler_interval_minutes=_int("SCHEDULER_INTERVAL_MINUTES", 180, minimum=5),
        phash_threshold=_int("PHASH_THRESHOLD", 6, minimum=0),
        image_width=_int("IMAGE_WIDTH", 1080, minimum=256),
        image_height=_int("IMAGE_HEIGHT", 1080, minimum=256),
        jpeg_quality=_int("JPEG_QUALITY", 92, minimum=60),
        database_path=_path("DATABASE_PATH", "data/app.db"),
        media_dir=_path("MEDIA_DIR", "data/media"),
        dashboard_password=_str("DASHBOARD_PASSWORD"),
        ollama_url=_str("OLLAMA_URL").rstrip("/"),
        ollama_model=_str("OLLAMA_MODEL", "llama3.2"),
        host=_str("HOST", "0.0.0.0"),
        port=_int("PORT", 5000, minimum=1),
    )
