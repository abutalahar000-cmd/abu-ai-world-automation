"""Publishing rules: manual approval is mandatory before anything goes live."""

from __future__ import annotations

import logging

from app import captioner
from app import storage as storage_module
from app.facebook import FacebookError, FacebookGraphClient

LOGGER = logging.getLogger(__name__)


class PublishBlocked(RuntimeError):
    """Raised when the approval or configuration gate stops a publish."""


def approve_post(storage, post_id: str) -> dict:
    post = storage.get_post(post_id)
    if post is None:
        raise PublishBlocked("Post not found.")
    if post["status"] == "published":
        raise PublishBlocked("This post has already been published.")
    if post["status"] == "rejected":
        raise PublishBlocked("This post was rejected. Regenerate it instead.")
    storage.update_post(post_id, status="approved", approved_at=storage_module.utcnow(), error="")
    storage.add_event(post_id, "approved", "Manually approved for Facebook publishing")
    return storage.get_post(post_id)


def reject_post(storage, post_id: str, reason: str = "") -> dict:
    post = storage.get_post(post_id)
    if post is None:
        raise PublishBlocked("Post not found.")
    if post["status"] == "published":
        raise PublishBlocked("Published posts cannot be rejected.")
    storage.update_post(post_id, status="rejected", error=reason[:500])
    storage.add_event(post_id, "rejected", reason or "Rejected during manual review")
    return storage.get_post(post_id)


def update_post_content(
    storage,
    post_id: str,
    title: str | None = None,
    caption: str | None = None,
    hashtags: list[str] | None = None,
) -> dict:
    """Let a human edit copy before approval, keeping signatures unique."""
    post = storage.get_post(post_id)
    if post is None:
        raise PublishBlocked("Post not found.")
    if post["status"] == "published":
        raise PublishBlocked("Published posts cannot be edited.")

    updates: dict = {}
    if title is not None:
        title = title.strip()
        if not title:
            raise PublishBlocked("Title cannot be empty.")
        if title.lower() != post["title"].lower() and storage.title_exists(title):
            raise PublishBlocked("Another post already uses that title.")
        updates["title"] = title[:200]

    if caption is not None:
        caption = caption.strip()
        if not caption:
            raise PublishBlocked("Caption cannot be empty.")
        signature = captioner.caption_signature(caption)
        if signature != post["caption_signature"] and storage.signature_exists(
            "caption_signature", signature
        ):
            raise PublishBlocked("Another post already uses that caption.")
        updates["caption"] = caption[:5000]
        updates["caption_signature"] = signature

    if hashtags is not None:
        cleaned = [tag.strip() for tag in hashtags if tag.strip()]
        signature = captioner.hashtag_signature(cleaned)
        if signature != post["hashtag_signature"] and storage.signature_exists(
            "hashtag_signature", signature
        ):
            raise PublishBlocked("Another post already uses that hashtag set.")
        updates["hashtags"] = cleaned
        updates["hashtag_signature"] = signature

    if updates:
        storage.update_post(post_id, **updates)
        storage.add_event(post_id, "edited", "Copy edited during manual review")
    return storage.get_post(post_id)


def publish_post(storage, settings, post_id: str, client=None) -> dict:
    """Publish one approved post to the configured Facebook Page."""
    post = storage.get_post(post_id)
    if post is None:
        raise PublishBlocked("Post not found.")

    if post["status"] == "published" and post.get("facebook_post_id"):
        return post

    if not settings.facebook_configured:
        raise PublishBlocked(
            "Facebook Page credentials are not configured. Set FB_PAGE_ID and "
            "FB_PAGE_ACCESS_TOKEN before publishing."
        )

    if settings.require_approval and post["status"] != "approved":
        raise PublishBlocked(
            "Manual approval required: approve this photo in the review dashboard "
            "before publishing."
        )

    if post["status"] == "rejected":
        raise PublishBlocked("Rejected posts cannot be published.")

    message = captioner.build_facebook_message(post)
    graph = client or FacebookGraphClient(settings)

    try:
        result = graph.publish_photo(post["image_path"], message)
    except FacebookError as exc:
        storage.update_post(post_id, status="failed", error=str(exc)[:500])
        storage.add_event(post_id, "publish_failed", str(exc))
        raise

    storage.update_post(
        post_id,
        status="published",
        published_at=storage_module.utcnow(),
        facebook_post_id=result.get("photo_id", ""),
        permalink=result.get("permalink", ""),
        error="",
    )
    storage.add_event(
        post_id,
        "published",
        f"Published to Facebook Page (photo id {result.get('photo_id') or 'unknown'})",
    )
    return storage.get_post(post_id)


def publish_approved(storage, settings, limit: int = 10, client=None) -> dict:
    """Publish already-approved posts (still requires Facebook configuration)."""
    if not settings.facebook_configured:
        raise PublishBlocked(
            "Facebook Page credentials are not configured. Set FB_PAGE_ID and "
            "FB_PAGE_ACCESS_TOKEN before publishing."
        )
    approved = storage.list_posts(status="approved", limit=limit)
    results, errors = [], []
    for post in approved:
        try:
            results.append(publish_post(storage, settings, post["id"], client=client))
        except (PublishBlocked, FacebookError) as exc:
            errors.append({"id": post["id"], "error": str(exc)})
    return {"published": results, "errors": errors}


def auto_publish_approved(storage, settings, limit: int = 3, client=None) -> list[dict]:
    """Only runs when AUTO_PUBLISH=true *and* credentials exist *and* posts are approved."""
    if not settings.auto_publish:
        return []
    if not settings.facebook_configured:
        storage.add_event(
            None,
            "auto_publish_skipped",
            "AUTO_PUBLISH is on but Facebook credentials are missing; nothing was published.",
        )
        return []
    published = []
    for post in storage.list_posts(status="approved", limit=limit):
        try:
            published.append(publish_post(storage, settings, post["id"], client=client))
        except (PublishBlocked, FacebookError) as exc:
            LOGGER.warning("Auto publish failed for %s: %s", post["id"], exc)
            storage.add_event(post["id"], "auto_publish_failed", str(exc))
    return published
