"""One-shot live verification of the real image pipeline.

Runs sequentially (no request loops) and writes to a throwaway database so the
real project data is untouched. It answers, with evidence:

* does each image provider actually work right now, and is it a real model?
* do five different categories produce real, distinct photos?
* are captions, hashtags and duplicate detection working?
* does the Facebook Graph API request build correctly without publishing?

Usage: python3 scripts/verify_live.py [category ...]
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import captioner, config, dedupe, generator, provider_check, quality  # noqa: E402
from app import storage as storage_module  # noqa: E402
from app.facebook import FacebookGraphClient  # noqa: E402
from app.providers import provider_status  # noqa: E402

DEFAULT_CATEGORIES = ["girls", "boys", "fashion", "travel", "food"]
LIVE_SIZE = 768


def _tags(post: dict) -> list[str]:
    """Hashtags are stored as a list in memory and as JSON text in SQLite."""
    tags = post["hashtags"]
    return tags if isinstance(tags, list) else json.loads(tags)


def _live_settings(tmp: Path, provider: str = "pollinations"):
    base = config.load_settings()
    return dataclasses.replace(
        base,
        database_path=tmp / "live.db",
        media_dir=tmp / "media",
        image_provider=provider,
        fallback_provider="placeholder",
        require_approval=True,
        auto_publish=False,
        image_width=LIVE_SIZE,
        image_height=LIVE_SIZE,
    )


def main(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if not arg.startswith("-")]
    categories = args or DEFAULT_CATEGORIES
    provider = "placeholder" if "--placeholder" in argv[1:] else "pollinations"
    summary: dict = {"provider": provider, "providers": [], "categories": [], "dedupe": {}, "facebook": {}}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        settings = _live_settings(tmp, provider)
        store = storage_module.Storage(settings.database_path, settings.media_dir)
        print(f"== image provider for generation: {provider} ==")

        print("== provider status (configuration) ==")
        for row in provider_status(settings):
            print(
                f"  {row['name']:<12} available={row['available']!s:<5} "
                f"is_ai={row['is_ai']!s:<5} placeholder={row['is_placeholder']!s:<5} {row['notes']}"
            )

        print("\n== provider live checks (one call each) ==")
        for name in ("pollinations", "huggingface", "local", "placeholder"):
            report = provider_check.check_provider(settings, name)
            summary["providers"].append(
                {
                    "provider": name,
                    "ok": report["ok"],
                    "real_photo": report["real_photo"],
                    "available": report["available"],
                    "model": report.get("model", ""),
                    "bytes": report.get("bytes", 0),
                    "detail": report["detail"],
                }
            )
            print(f"  {name:<12} ok={report['ok']!s:<5} real_photo={report['real_photo']!s:<5} {report['detail']}")
            time.sleep(2)

        print(f"\n== generating one real photo per category: {', '.join(categories)} ==")
        posts = []
        for category in categories:
            try:
                post = generator.generate_post(store, settings, category=category)
            except Exception as exc:  # noqa: BLE001 - report the failure verbatim
                summary["categories"].append({"category": category, "ok": False, "error": str(exc)})
                print(f"  {category:<10} FAILED: {exc}")
                continue

            data = Path(post["image_path"]).read_bytes()
            measured = quality.inspect_image(data)
            posts.append(post)
            summary["categories"].append(
                {
                    "category": category,
                    "ok": True,
                    "provider": post["provider"],
                    "is_placeholder": bool(post["is_placeholder"]),
                    "size": f"{measured.width}x{measured.height}",
                    "bytes": measured.size_bytes,
                    "entropy": measured.entropy,
                    "unique_colors": measured.unique_colors,
                    "detail": measured.detail,
                    "title": post["title"],
                    "caption_chars": len(post["caption"]),
                    "hashtags": len(_tags(post)),
                    "sha256": post["image_sha256"][:16],
                }
            )
            print(
                f"  {category:<10} provider={post['provider']:<12} {measured.width}x{measured.height} "
                f"{measured.size_bytes}B entropy={measured.entropy:.2f} colors={measured.unique_colors} "
                f"sha={post['image_sha256'][:12]} placeholder={bool(post['is_placeholder'])}"
            )
            print(f"             title: {post['title']}")
            print(f"             caption: {post['caption'][:110]}...")
            print(f"             hashtags: {' '.join(_tags(post))}")
            time.sleep(2)

        if len(posts) >= 2:
            shas = {post["image_sha256"] for post in posts}
            titles = {post["title"] for post in posts}
            captions = {post["caption"] for post in posts}
            tags = {post["hashtag_signature"] for post in posts}
            summary["uniqueness"] = {
                "posts": len(posts),
                "distinct_images": len(shas),
                "distinct_titles": len(titles),
                "distinct_captions": len(captions),
                "distinct_hashtag_sets": len(tags),
            }
            print("\n== uniqueness ==")
            print(json.dumps(summary["uniqueness"], indent=2))

        if posts:
            first = posts[0]
            duplicate = store.find_duplicate(
                first["phash"], first["ahash"], first["image_sha256"], settings.phash_threshold
            )
            summary["dedupe"] = {
                "identical_image_detected": bool(duplicate),
                "reason": (duplicate or {}).get("reason", ""),
                "matched_post": (duplicate or {}).get("id", ""),
            }
            print("\n== duplicate detection ==")
            print(json.dumps(summary["dedupe"], indent=2))

            graph = FacebookGraphClient(
                dataclasses.replace(
                    settings, fb_page_id="1234567890", fb_page_access_token="dry-run-token"
                )
            )
            message = captioner.build_facebook_message(first)
            dry = graph.dry_run_publish(first["image_path"], message)
            summary["facebook"] = {
                "dry_run_sent": dry["sent"],
                "endpoint": dry["request"]["url"],
                "checks": dry["checks"],
                "token_in_request": "dry-run-token" in json.dumps(dry["request"]),
            }
            print("\n== Facebook Graph API (dry run, nothing published) ==")
            print(json.dumps(summary["facebook"], indent=2))

        counts = store.counts()
        summary["storage_counts"] = counts
        print("\n== storage ==")
        print(json.dumps(counts, indent=2))

    print("\n== SUMMARY JSON ==")
    print(json.dumps(summary, indent=2))
    failures = [row for row in summary["categories"] if not row["ok"]]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
