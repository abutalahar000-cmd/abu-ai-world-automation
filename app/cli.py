"""Command-line interface.

Examples:
    python -m app.cli init-db
    python -m app.cli generate --count 2 --category travel
    python -m app.cli list --status pending
    python -m app.cli approve <post-id>
    python -m app.cli publish <post-id>
    python -m app.cli verify-facebook
"""

from __future__ import annotations

import argparse
import json
import sys

from app import config, generator, prompts, providers, publisher, scheduler
from app import storage as storage_module


def _services():
    settings = config.load_settings()
    store = storage_module.Storage(settings.database_path, settings.media_dir)
    return settings, store


def _print_post(post: dict) -> None:
    print(f"[{post['id']}] {post['status'].upper()} · {post['category']} · {post['title']}")
    print(f"    provider: {post['provider']}   created: {post['created_at']}")
    print(f"    image:    {post['image_file']}")
    if post.get("permalink"):
        print(f"    facebook: {post['permalink']}")


def cmd_init_db(args) -> int:
    settings, store = _services()
    print(f"Database ready at {store.database_path}")
    print(f"Media directory: {store.media_dir}")
    print(f"Approval required: {settings.require_approval}")
    return 0


def cmd_generate(args) -> int:
    settings, store = _services()
    outcome = generator.generate_batch(
        store,
        settings,
        count=args.count,
        category=args.category,
        provider_name=args.provider,
    )
    for post in outcome.created:
        _print_post(post)
    for error in outcome.errors:
        print(f"error: {error}", file=sys.stderr)
    if not outcome.created:
        return 1
    if settings.require_approval:
        print("\nThese photos are waiting for manual approval:")
        print("  python -m app.cli approve <post-id>")
    return 0


def cmd_list(args) -> int:
    _, store = _services()
    posts = store.list_posts(status=args.status, limit=args.limit)
    if not posts:
        print("No posts found.")
        return 0
    for post in posts:
        _print_post(post)
    return 0


def cmd_show(args) -> int:
    _, store = _services()
    post = store.get_post(args.post_id)
    if post is None:
        print("Post not found.", file=sys.stderr)
        return 1
    print(f"Title:    {post['title']}")
    print(f"Status:   {post['status']}")
    print(f"Category: {post['category']}")
    print(f"Provider: {post['provider']}")
    print(f"Image:    {post['image_path']}")
    print(f"Prompt:   {post['prompt']}")
    print("\nCaption:\n" + post["caption"])
    print("\nHashtags:\n" + " ".join(post["hashtags"]))
    if post.get("permalink"):
        print("\nFacebook: " + post["permalink"])
    if post.get("error"):
        print("\nLast error: " + post["error"])
    return 0


def cmd_approve(args) -> int:
    _, store = _services()
    post = publisher.approve_post(store, args.post_id)
    print(f"Approved {post['id']} - ready to publish.")
    return 0


def cmd_reject(args) -> int:
    _, store = _services()
    post = publisher.reject_post(store, args.post_id, args.reason or "")
    print(f"Rejected {post['id']}.")
    return 0


def cmd_publish(args) -> int:
    settings, store = _services()
    try:
        post = publisher.publish_post(store, settings, args.post_id)
    except publisher.PublishBlocked as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Published: {post.get('permalink') or post.get('facebook_post_id')}")
    return 0


def cmd_publish_approved(args) -> int:
    settings, store = _services()
    try:
        result = publisher.publish_approved(store, settings, limit=args.limit)
    except publisher.PublishBlocked as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Published {len(result['published'])} post(s).")
    for error in result["errors"]:
        print(f"error {error['id']}: {error['error']}", file=sys.stderr)
    return 0


def cmd_verify_facebook(args) -> int:
    settings, _ = _services()
    from app.facebook import FacebookError, FacebookGraphClient

    try:
        page = FacebookGraphClient(settings).verify_page()
    except FacebookError as exc:
        print(f"Facebook check failed: {exc}", file=sys.stderr)
        return 2
    print(f"Connected to Page: {page.get('name')} (id {page.get('id')})")
    return 0


def cmd_providers(args) -> int:
    settings, _ = _services()
    for row in providers.provider_status(settings):
        marker = "*" if row["selected"] else " "
        state = "ready" if row["available"] else "not configured"
        print(f"{marker} {row['name']:<12} {state:<16} {row['notes']}")
    return 0


def cmd_stats(args) -> int:
    settings, store = _services()
    print(json.dumps({"counts": store.counts(), "settings": settings.public_status()}, indent=2))
    return 0


def cmd_run_once(args) -> int:
    settings, store = _services()
    print(json.dumps(scheduler.run_once(store, settings), indent=2))
    return 0


def cmd_scheduler(args) -> int:
    settings, store = _services()
    scheduler.main(store, settings)
    return 0


def cmd_serve(args) -> int:
    from app.web import main as web_main

    web_main()
    return 0


def cmd_categories(args) -> int:
    for key, label in prompts.CATEGORY_LABELS.items():
        print(f"{key:<14} {label}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="facebook-ai-photo-automation",
        description="Generate unique AI photos and publish them to a Facebook Page (manual approval by default).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create the SQLite database and media folder").set_defaults(func=cmd_init_db)
    sub.add_parser("categories", help="List photo categories").set_defaults(func=cmd_categories)
    sub.add_parser("providers", help="Show image provider status").set_defaults(func=cmd_providers)
    sub.add_parser("stats", help="Show post counts and safe config status").set_defaults(func=cmd_stats)
    sub.add_parser("verify-facebook", help="Verify Page credentials with the Graph API").set_defaults(
        func=cmd_verify_facebook
    )
    sub.add_parser("run-once", help="One generate (+optional auto-publish) cycle").set_defaults(func=cmd_run_once)
    sub.add_parser("scheduler", help="Run the opt-in background scheduler").set_defaults(func=cmd_scheduler)
    sub.add_parser("serve", help="Start the review dashboard").set_defaults(func=cmd_serve)

    generate = sub.add_parser("generate", help="Generate new photo posts")
    generate.add_argument("--count", type=int, default=1)
    generate.add_argument("--category", choices=list(prompts.CATEGORY_LABELS), default=None)
    generate.add_argument("--provider", choices=list(providers.PROVIDERS), default=None)
    generate.set_defaults(func=cmd_generate)

    listing = sub.add_parser("list", help="List posts")
    listing.add_argument("--status", default="all", choices=["all", *storage_module.STATUSES])
    listing.add_argument("--limit", type=int, default=20)
    listing.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="Show one post")
    show.add_argument("post_id")
    show.set_defaults(func=cmd_show)

    approve = sub.add_parser("approve", help="Approve a post for publishing")
    approve.add_argument("post_id")
    approve.set_defaults(func=cmd_approve)

    reject = sub.add_parser("reject", help="Reject a post")
    reject.add_argument("post_id")
    reject.add_argument("--reason", default="")
    reject.set_defaults(func=cmd_reject)

    publish = sub.add_parser("publish", help="Publish one approved post")
    publish.add_argument("post_id")
    publish.set_defaults(func=cmd_publish)

    bulk = sub.add_parser("publish-approved", help="Publish all approved posts")
    bulk.add_argument("--limit", type=int, default=10)
    bulk.set_defaults(func=cmd_publish_approved)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
