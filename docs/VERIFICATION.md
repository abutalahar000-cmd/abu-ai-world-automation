# Verification report

What was actually executed, what passed, and what is blocked. Everything below was run in this
repository; nothing is claimed from reading code alone.

Reproduce with:

```bash
python3 -m pytest -q                 # full offline suite
python3 scripts/verify_live.py       # live providers + 5 categories (real network)
python3 scripts/verify_live.py --placeholder   # same pipeline, no network
```

---

## 1. Image providers — availability at test time

| Provider | Type | Configured | Live result | Verdict |
| --- | --- | --- | --- | --- |
| `pollinations` | free hosted FLUX, no key | yes (default) | `HTTP 402`, retried `HTTP 503` | **Unavailable right now** |
| `huggingface` | free-tier token, FLUX.1-schnell | no | `Not configured: missing credentials` | **Needs `HF_TOKEN`** |
| `local` | self-hosted Stable Diffusion Web UI | no server | `unreachable at http://127.0.0.1:7860` | **Needs `LOCAL_SD_URL` running** |
| `placeholder` | offline procedural artwork | yes | generated 38–42 KB PNGs | **Works, and is not an AI photo** |

Pollinations returned `402` (quota/payment) on the first call and `503` on the check call from this
environment. That is a provider-side availability problem, not a code path that was skipped: the
client sent a real prompt, received a non-image response, and raised `ProviderError`, which triggered
the configured fallback exactly as designed.

**Consequence:** no real AI photo could be produced during this run. Real-photo generation is
implemented and wired, but its live output is **unverified** until one backend is reachable. To
enable it, do any one of:

1. Set `POLLINATIONS_TOKEN` (free account, raises the anonymous limit) and retry.
2. Set `HF_TOKEN` and `IMAGE_PROVIDER=huggingface`.
3. Run AUTOMATIC1111/Forge locally, set `LOCAL_SD_URL`, and use `IMAGE_PROVIDER=local`.

Verify with `python -m app.cli verify-providers` — it calls each provider once and reports
`ok` / `real_photo` / the exact error, so "available" is never inferred from settings alone.

---

## 2. Placeholder honesty (requirement: Pillow is not an AI generator)

- `PlaceholderProvider.is_ai = False`, `is_placeholder = True`, and every result carries
  `meta={"placeholder": True}`.
- The generator stores `is_placeholder = 1` on the post and writes
  `(PLACEHOLDER artwork - not a real AI photo)` into the note.
- `provider_status()` reports `is_ai=False` for the placeholder and `is_ai=True` only for
  Pollinations, Hugging Face and local Stable Diffusion.
- Placeholder art measured `958–1413` distinct colours and `11.5–13.3` detail, below the
  photographic thresholds (`1500` colours, `15` detail) — so it would be rejected if it were ever
  presented as a photo. Tests assert this.

Pillow is used for hashing, dedupe, quality measurement and procedural test artwork only. It is
never described as generating AI images.

---

## 3. Five categories — offline pipeline run (`--placeholder`)

`python3 scripts/verify_live.py --placeholder` produced one post per category with a throwaway
database:

| Category | Provider | Size | Bytes | Entropy | Distinct image | Title |
| --- | --- | --- | --- | --- | --- | --- |
| girls | placeholder | 768×768 | 38.5 KB | 6.65 | yes | A Little Dreamy Never Hurts |
| boys | placeholder | 768×768 | ~38 KB | ~6.6 | yes | (distinct) |
| fashion | placeholder | 768×768 | ~40 KB | ~6.5 | yes | (distinct) |
| travel | placeholder | 768×768 | 42.4 KB | 6.81 | yes | The Journey Story: Old Town |
| food | placeholder | 768×768 | 42.5 KB | 6.11 | yes | Everyday The Plate, Elevated |

Uniqueness summary from the run:

```json
{"posts": 5, "distinct_images": 5, "distinct_titles": 5, "distinct_captions": 5, "distinct_hashtag_sets": 5}
```

Captions were 119–130 characters with 9–11 hashtags each. Every post landed in `pending`
(`{"pending": 5, "approved": 0, "published": 0}`), confirming the approval gate.

**What this proves:** blueprint variety, prompt rendering, caption/title/hashtag generation,
hashing, storage and the approval flow all work end to end.

**What it does not prove:** that a diffusion model returns realistic adult men and women. That needs
a reachable backend (section 1).

---

## 4. Duplicate detection

- Re-submitting the first post's exact bytes returned
  `{"identical_image_detected": true, "reason": "identical file"}`.
- Perceptual dHash/aHash near-duplicate checks and the `phash_threshold` path are covered by
  `tests/test_dedupe.py` (resized, re-encoded and slightly cropped copies are caught).

---

## 5. Facebook Graph API — dry run only, nothing published

`tests/test_dry_run.py` and the live script both build the real request with a fake session that
raises if any network call is attempted:

```json
{
  "dry_run_sent": false,
  "endpoint": "https://graph.facebook.com/v23.0/<page-id>/photos",
  "checks": {"credentials_present": true, "image_exists": true, "image_not_empty": true,
             "message_not_empty": true, "message_within_limit": true},
  "token_in_request": false
}
```

- The access token never appears in the described request.
- A dry run leaves the post `pending`; a real publish still raises `PublishBlocked`
  ("Manual approval required").
- `AUTO_PUBLISH=false` and `REQUIRE_APPROVAL=true` are asserted by tests.

**Unverified:** an actual upload to a live Page. That requires a real `FB_PAGE_ID` and Page access
token with `pages_manage_posts`, and it was deliberately not performed.

---

## 6. Test suite

```text
python3 -m pytest -q  ->  48 passed
```

Coverage includes blueprints/uniqueness, captions and hashtag signatures, dedupe, generation
pipeline, approval and publish gate, Facebook dry run, provider honesty, automatic fallback, image
quality thresholds, the CLI and the dashboard.

Note: `Image.Image.getdata` emits a Pillow deprecation warning (removal in Pillow 14, 2027). It is
harmless today and tracked as a future cleanup in `app/dedupe.py`.

---

## Summary

| Requirement | Status |
| --- | --- |
| Real AI images, not placeholders | Implemented; **live output unverified** (no reachable backend) |
| Pollinations / Hugging Face tested | Tested — Pollinations 402/503, HF needs token |
| Free providers + automatic fallback | Working, proven by `test_fallback.py` |
| Pillow not presented as AI | Working, proven by tests and provider flags |
| Diverse adults across attributes | Prompting + blueprint variety proven offline; photographic realism unverified |
| 5+ categories | Verified offline (5 categories, 5 distinct posts) |
| Captions, hashtags, duplicate detection | Verified |
| Graph API without publishing | Verified via dry run, no token leakage |
| Manual approval, `AUTO_PUBLISH=false` | Verified |
| No deployment, no paid APIs | Respected — nothing deployed, no paid service used |
