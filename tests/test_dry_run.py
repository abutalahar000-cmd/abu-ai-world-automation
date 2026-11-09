"""Facebook Graph API dry-run tests.

The dry run must describe and validate the upload without ever contacting
Facebook, so the integration can be checked without publishing a real post.
"""

from __future__ import annotations

import json

import pytest

from app import generator, publisher
from app.facebook import FacebookGraphClient


class _NoNetworkSession:
    """Fails loudly if a dry run touches the network."""

    def get(self, *args, **kwargs):  # pragma: no cover - asserted by never running
        raise AssertionError("Dry run must not call the Graph API")

    def post(self, *args, **kwargs):  # pragma: no cover - asserted by never running
        raise AssertionError("Dry run must not upload anything")


def _client(settings) -> FacebookGraphClient:
    return FacebookGraphClient(settings, session=_NoNetworkSession())


def test_dry_run_builds_request_without_sending(store, settings, fb_settings):
    post = generator.generate_post(store, settings, category="girls")
    client = _client(fb_settings)

    result = publisher.publish_post(store, fb_settings, post["id"], client=client, dry_run=True)

    assert result["dry_run"]["sent"] is False
    checks = result["dry_run"]["checks"]
    assert checks["credentials_present"] is True
    assert checks["image_exists"] is True
    assert checks["image_not_empty"] is True
    assert checks["message_not_empty"] is True
    assert checks["message_within_limit"] is True
    # Manual approval is still enabled, so the dry run reports it as pending.
    assert checks["approved"] is False
    assert checks["require_approval"] is True

    request = result["dry_run"]["request"]
    assert request["method"] == "POST"
    assert request["url"].endswith("/1234567890/photos")
    assert request["file"]["field"] == "source"
    assert request["file"]["bytes"] > 0
    # The token must never appear in the described request.
    assert "test-token" not in json.dumps(request)

    # Nothing changed in storage: the post is still awaiting review.
    assert store.get_post(post["id"])["status"] == "pending"


def test_dry_run_leaves_publish_gate_intact(store, settings, fb_settings):
    post = generator.generate_post(store, settings, category="travel")
    client = _client(fb_settings)

    publisher.publish_post(store, fb_settings, post["id"], client=client, dry_run=True)

    with pytest.raises(publisher.PublishBlocked) as excinfo:
        publisher.publish_post(store, fb_settings, post["id"], client=client)
    assert "Manual approval required" in str(excinfo.value)


def test_dry_run_requires_credentials(store, settings):
    post = generator.generate_post(store, settings, category="fashion")
    with pytest.raises(publisher.PublishBlocked) as excinfo:
        publisher.publish_post(store, settings, post["id"], dry_run=True)
    assert "credentials are not configured" in str(excinfo.value)


def test_auto_publish_defaults_to_off(settings):
    assert settings.auto_publish is False
    assert settings.require_approval is True
