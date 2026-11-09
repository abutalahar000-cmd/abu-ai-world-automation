# Facebook AI Photo Automation

An automated, **approval-gated** system that creates unique AI photos, writes unique Facebook
titles/captions/hashtags, blocks duplicates, and publishes to a Facebook Page through the official
Meta Graph API.

Everything runs on free or open-source tools. No paid API is used, and nothing is published until a
human approves it.

---

## What this repository used to be

This repo was previously an autonomous **YouTube Shorts** project ("Abu AI World") with a permanent
character identity. It has been fully replaced. See [`docs/PLAN.md`](docs/PLAN.md) for the detailed
migration record.

| Removed | Why |
| --- | --- |
| `main.py` | YouTube Data API research script; hardcoded the `Abu AI World` channel and the `Abu AI` character |
| `.github/workflows/daily.yml` | Cron workflow that ran the YouTube automation |
| `.github/workflows/research.yml` | Cron workflow using the `YOUTUBE_API_KEY` secret |
| `character_reference.png` | Permanent character asset used only by the old YouTube project |

No old character, identity, prompt or asset is reused. The new system generates a **different person
every time** from random attribute pools.

---

## Features

- **Random photo generation** across 10 categories: `girls`, `boys`, `lifestyle`, `fashion`,
  `travel`, `food`, `nature`, `architecture`, `fitness`, `street`.
- **Guaranteed variety** — every photo gets its own appearance, clothing, pose, background and
  camera angle. Each blueprint fingerprint is stored with a `UNIQUE` constraint, and recently used
  values are actively avoided, so the same combination is never generated twice.
- **Unique copy** — a fresh title, caption and hashtag set per photo, checked against the database
  before use.
- **Duplicate-photo detection** — SHA-256 exact match plus perceptual dHash/aHash near-duplicate
  detection (Pillow only, no paid service).
- **Manual approval mode** — new photos land in a review dashboard as `pending`. Publishing requires
  both an explicit approval and a publish action.
- **Official Meta Graph API publishing** to `/{page-id}/photos`.
- **Secure credentials** — read only from environment variables, never written to the database,
  logs or dashboard.
- **Free providers** — Pollinations (no key), Hugging Face free tier, self-hosted Stable Diffusion,
  and an offline placeholder so the pipeline works without network access.
- **Photographic quality gate** — every image from an AI provider is decoded and measured (detail,
  entropy, colour spread) so a blank, flat or HTML error response is rejected instead of stored.
- **Facebook dry run** — `publish --dry-run` builds and validates the Graph API request without
  sending it, so the integration can be checked before anything is published.
- **Provider verification** — `verify-providers` calls each backend once and reports what actually
  works, rather than inferring availability from settings.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional: only needed for Facebook publishing
python -m app.cli init-db
python -m app.cli generate --count 3
python -m app.cli list --status pending

# Review dashboard (manual approval UI)
python -m app.cli serve       # http://127.0.0.1:8000
```

Check what the image backends can actually do right now (one call each):

```bash
python -m app.cli verify-providers
python3 scripts/verify_live.py            # live run, 5 categories
python3 scripts/verify_live.py --placeholder   # same pipeline, no network
```

No credentials are required to generate and review photos. The default provider chain produces
real images with Pollinations and falls back to a clearly labelled offline placeholder if the network
is unavailable.

---

## Configuration

All settings come from environment variables (a git-ignored `.env` is supported). See
[`.env.example`](.env.example) for the full list.

| Variable | Required | Purpose |
| --- | --- | --- |
| `FB_PAGE_ID` | only to publish | Facebook Page ID |
| `FB_PAGE_ACCESS_TOKEN` | only to publish | Page access token with `pages_manage_posts` |
| `GRAPH_API_VERSION` | no | Graph API version (default `v23.0`) |
| `IMAGE_PROVIDER` | no | `pollinations` (default), `huggingface`, `local`, `placeholder` |
| `FALLBACK_PROVIDER` | no | Used when the primary provider fails |
| `HF_TOKEN` | no | Free Hugging Face token, only for the `huggingface` provider |
| `POLLINATIONS_TOKEN` | no | Optional free token to raise rate limits |
| `LOCAL_SD_URL` | no | Your own AUTOMATIC1111/Forge endpoint for `local` |
| `REQUIRE_APPROVAL` | no | Default `true` — keep this on for manual approval |
| `AUTO_PUBLISH` | no | Default `false` — publishing stays off until you enable it |
| `DASHBOARD_PASSWORD` | no | Protects the review dashboard with HTTP Basic auth |
| `PHASH_THRESHOLD` | no | Near-duplicate sensitivity (default `6`) |

> Never commit `.env`. `.gitignore` already excludes it. Rotate any token that was ever exposed.

---

## How uniqueness is enforced

1. A **blueprint** samples every attribute — heritage, age range, face, hair, outfit, pose,
   background, camera angle, lighting, lens — from large local pools.
2. Recently used values for those fields are excluded, so consecutive posts differ visibly.
3. The blueprint's canonical fingerprint is stored with a `UNIQUE` index; a repeat raises instead of
   silently duplicating.
4. The rendered image is hashed (SHA-256, dHash, aHash). If it matches an existing photo within the
   perceptual threshold, the post is rejected and logged as a duplicate.

---

## Approval and publishing flow

```
generate  ->  pending  ->  approve  ->  publish  ->  published
                    \-> reject
```

- `REQUIRE_APPROVAL=true` (default) means nothing can be published before approval.
- `publish` additionally requires `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN`; without them the attempt
  is blocked with a clear message and nothing is sent.
- `AUTO_PUBLISH=false` (default) means even the opt-in scheduler will not publish unapproved posts.

### CLI

```bash
python -m app.cli generate --count 5 --category travel
python -m app.cli list --status approved
python -m app.cli approve <post-id>
python -m app.cli publish <post-id>
python -m app.cli verify-facebook     # confirms the Page token works
python -m app.cli serve
```

### Dashboard

The dashboard shows every post with its photo, title, caption, hashtags, prompt, duplicate hashes
and status, and provides approve / reject / edit / publish / delete actions with CSRF protection.

### Scheduler (opt-in)

```bash
python -m app.cli schedule            # generates on an interval, never bypasses approval
```

---

## Tests

```bash
pytest          # 48 tests: blueprints, captions, dedupe, quality gate, pipeline, approval gate,
                #            Facebook dry run, provider fallback, dashboard
ruff check .    # lint
```

Tests run fully offline against the placeholder provider and a temporary database. What was actually
executed — including which providers were reachable — is recorded in
[`docs/VERIFICATION.md`](docs/VERIFICATION.md).

---

## Project layout

```
app/
  config.py        environment-driven settings
  prompts.py       attribute pools + prompt rendering
  randomizer.py    uniqueness-aware blueprint sampling
  captioner.py     unique titles, captions, hashtags
  dedupe.py        SHA-256 + perceptual hashes
  quality.py       photographic quality gate (decode, detail, entropy)
  provider_check.py one-call availability checks per provider
  storage.py       SQLite posts, signatures, events
  generator.py     generation pipeline
  publisher.py     approval gate + publish rules
  facebook.py      Meta Graph API client
  scheduler.py     opt-in background loop
  cli.py           command-line interface
  web.py           Flask review dashboard
  providers/       pollinations, huggingface, local_sd, placeholder
tests/             pytest suite
scripts/verify_live.py   live 5-category verification run
docs/PLAN.md       migration + implementation plan
docs/VERIFICATION.md     what was tested, what needs credentials
```

---

## Notes and limitations

- AI-generated images are labelled as such in every caption. Keep that disclosure — it is required
  by Meta's synthetic-content policy for realistic AI imagery.
- Free provider quotas can change. If generation fails, the fallback provider or the offline
  placeholder is used and the reason is recorded in the event log. Pollinations returned HTTP
  402/503 during the last verification run; set `POLLINATIONS_TOKEN`, `HF_TOKEN` or `LOCAL_SD_URL`
  to enable real AI photos, then confirm with `python -m app.cli verify-providers`.
- The placeholder is labelled `is_placeholder` everywhere and is never reported as an AI image.
- This repository is source code only: no deployment is configured, and no credentials are included.
