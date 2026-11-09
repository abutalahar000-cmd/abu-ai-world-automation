"""Provider honesty and automatic fallback tests.

These prove two requirements: the offline backend is never reported as an AI
image generator, and a failing free provider automatically falls through to the
next configured provider.
"""

from __future__ import annotations

from app import generator, providers
from app.providers.base import ImageResult, ProviderError


def test_placeholder_is_flagged_and_not_reported_as_ai(settings):
    status = {row["name"]: row for row in providers.provider_status(settings)}
    assert status["placeholder"]["is_placeholder"] is True
    assert status["placeholder"]["is_ai"] is False
    # Real diffusion backends are marked as AI providers.
    assert status["pollinations"]["is_ai"] is True
    assert status["pollinations"]["is_placeholder"] is False


def test_placeholder_post_is_marked_in_storage(store, settings):
    post = generator.generate_post(store, settings, category="nature")
    assert post["provider"] == "placeholder"
    assert post["is_placeholder"] == 1


def test_failing_provider_falls_back_automatically(store, settings, monkeypatch):
    calls: list[str] = []
    real_get_provider = providers.get_provider

    def fake_get_provider(name, config):
        calls.append(name)
        if name == "pollinations":
            return _BrokenProvider(config)
        return real_get_provider(name, config)

    monkeypatch.setattr(providers, "get_provider", fake_get_provider)
    settings = _with_providers(settings, image_provider="pollinations", fallback_provider="placeholder")

    post = generator.generate_post(store, settings, category="lifestyle")

    assert calls[:2] == ["pollinations", "placeholder"]
    assert post["provider"] == "placeholder"
    events = [event["message"] for event in store.list_events()]
    assert any("fallback after" in message for message in events)


class _BrokenProvider:
    """A provider that is configured but always fails."""

    name = "pollinations"
    is_ai = True
    is_placeholder = False

    def __init__(self, settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return True

    def generate(self, request):
        raise ProviderError("upstream returned HTTP 500")


def _with_providers(settings, **overrides):
    import dataclasses

    return dataclasses.replace(settings, **overrides)
