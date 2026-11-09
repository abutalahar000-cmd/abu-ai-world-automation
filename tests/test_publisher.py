"""Manual approval gate and Graph API publishing."""

from __future__ import annotations

import random

import pytest

from app import generator, publisher
from app.facebook import FacebookError


class FakeClient:
    def __init__(self, error: str | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.error = error

    def publish_photo(self, image_path, message):
        if self.error:
            raise FacebookError(self.error)
        self.calls.append((str(image_path), message))
        return {"photo_id": "999_888", "permalink": "https://www.facebook.com/999_888"}


def test_publish_requires_credentials(store, settings):
    post = generator.generate_post(store, settings, rng=random.Random(1))
    publisher.approve_post(store, post["id"])
    with pytest.raises(publisher.PublishBlocked) as excinfo:
        publisher.publish_post(store, settings, post["id"], client=FakeClient())
    assert "FB_PAGE_ID" in str(excinfo.value)
    assert store.get_post(post["id"])["status"] == "approved"


def test_publish_requires_manual_approval(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(2))
    assert post["status"] == "pending"
    with pytest.raises(publisher.PublishBlocked) as excinfo:
        publisher.publish_post(store, fb_settings, post["id"], client=FakeClient())
    assert "approval" in str(excinfo.value).lower()
    assert store.get_post(post["id"])["status"] == "pending"


def test_approved_post_publishes_with_full_message(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(3))
    publisher.approve_post(store, post["id"])
    client = FakeClient()

    result = publisher.publish_post(store, fb_settings, post["id"], client=client)

    assert result["status"] == "published"
    assert result["facebook_post_id"] == "999_888"
    assert result["published_at"]
    assert len(client.calls) == 1
    _path, message = client.calls[0]
    assert post["title"] in message or post["caption"].splitlines()[0][:10] in message
    assert post["hashtags"][0] in message


def test_rejected_post_cannot_publish(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(4))
    publisher.reject_post(store, post["id"], "off-brand")
    with pytest.raises(publisher.PublishBlocked):
        publisher.publish_post(store, fb_settings, post["id"], client=FakeClient())
    assert store.get_post(post["id"])["status"] == "rejected"


def test_graph_error_marks_post_failed(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(5))
    publisher.approve_post(store, post["id"])
    with pytest.raises(FacebookError):
        publisher.publish_post(
            store, fb_settings, post["id"], client=FakeClient(error="Graph API error 190: token expired")
        )
    stored = store.get_post(post["id"])
    assert stored["status"] == "failed"
    assert "190" in stored["error"]


def test_auto_publish_never_runs_without_opt_in(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(6))
    publisher.approve_post(store, post["id"])
    assert publisher.auto_publish_approved(store, fb_settings, client=FakeClient()) == []
    assert store.get_post(post["id"])["status"] == "approved"


def test_auto_publish_runs_only_for_approved_posts(store, fb_settings):
    import dataclasses

    opted_in = dataclasses.replace(fb_settings, auto_publish=True)
    approved = generator.generate_post(store, opted_in, rng=random.Random(7))
    pending = generator.generate_post(store, opted_in, rng=random.Random(8))
    publisher.approve_post(store, approved["id"])

    published = publisher.auto_publish_approved(store, opted_in, client=FakeClient())

    assert [item["id"] for item in published] == [approved["id"]]
    assert store.get_post(approved["id"])["status"] == "published"
    assert store.get_post(pending["id"])["status"] == "pending"


def test_published_post_is_idempotent(store, fb_settings):
    post = generator.generate_post(store, fb_settings, rng=random.Random(10))
    publisher.approve_post(store, post["id"])
    client = FakeClient()
    publisher.publish_post(store, fb_settings, post["id"], client=client)
    again = publisher.publish_post(store, fb_settings, post["id"], client=client)
    assert again["status"] == "published"
    assert len(client.calls) == 1
