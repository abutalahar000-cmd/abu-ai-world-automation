# Migration & Implementation Plan

This document records the inspection of the original repository, what was removed,
and the architecture of the replacement Facebook AI Photo Automation system.

## 1. Repository inspection (before changes)

The repository contained exactly five files:

| Path | Purpose | Decision |
| --- | --- | --- |
| `main.py` | YouTube Data API research script. Queried `youtube/v3/search` and `youtube/v3/videos`, hardcoded the channel `Abu AI World` and the permanent character `MAIN_CHARACTER = "Abu AI"`, wrote `topic_plan.json`. | **Removed** - YouTube-only, and it carried the old character identity. |
| `.github/workflows/daily.yml` | Two daily cron triggers running `python main.py`. | **Removed** - YouTube automation workflow. |
| `.github/workflows/research.yml` | Cron/manual workflow running `python main.py` with `YOUTUBE_API_KEY`. | **Removed** - YouTube secret + workflow. |
| `character_reference.png` | 2.4 MB character reference image. | **Removed** - only served the old YouTube character; no code in the new system references it. |
| `README.md` | Two-line description "Autonomous AI YouTube Shorts Automation". | **Rewritten** for the new project. |

Preserved: the Git repository itself, the selected branch, and the documentation
location (`README.md` + `docs/`). No old character, prompt, name or asset is reused.

Also removed conceptually: the `YOUTUBE_API_KEY` secret usage, the `topic_plan.json`
research output, and every reference to the "Abu AI" persona.

## 2. Goals mapped to implementation

| Requirement | Implementation |
| --- | --- |
| Random AI photo system with many categories | `app/prompts.py` attribute pools + `app/randomizer.py` combinatorial sampler for girls, boys, lifestyle, fashion, travel, food, nature, fitness, street, architecture. |
| Every person differs in appearance, clothing, pose, background, camera angle | Fingerprint over the full attribute set is stored with a `UNIQUE` constraint; recent per-field values are excluded during sampling; generation retries on collision. |
| Unique captions, titles, hashtags | `app/captioner.py` template + slot engine, per-category vocabulary, uniqueness signatures checked against SQLite. |
| Facebook Page publishing via official Graph API | `app/facebook.py` (`POST /{page_id}/photos`, multipart upload) + `app/publisher.py` approval gate. |
| Duplicate-photo detection | `app/dedupe.py` dHash + aHash perceptual hashes plus SHA-256 exact hash; near-duplicates rejected before a post is stored. |
| Free / open-source tools only | Flask, Pillow, SQLite, stdlib + free Pollinations endpoint, free-tier Hugging Face Inference API, self-hosted Stable Diffusion, offline Pillow fallback. No paid API. |
| Credentials as environment variables | `app/config.py` reads everything from env / `.env`; `.env.example` documents names only; nothing is written to the database or rendered in the UI. |
| Manual approval before publishing | Posts are created as `pending`. Publishing requires `approved` status **and** configured Page credentials. `AUTO_PUBLISH=false` by default. |

## 3. Architecture

```
app/
  config.py        Environment-driven settings (no secrets in code or logs)
  storage.py       SQLite: posts, uniqueness signatures, audit events
  prompts.py       Attribute pools + prompt/negative-prompt rendering
  randomizer.py    Unique blueprint sampling (collision-aware)
  captioner.py     Unique titles, captions, hashtag sets (+ optional Ollama)
  dedupe.py        dHash / aHash / SHA-256 duplicate detection
  providers/       pollinations | huggingface | local | placeholder
  generator.py     Orchestration: blueprint -> image -> dedupe -> caption -> store
  facebook.py      Meta Graph API client (verify page, upload photo)
  publisher.py     Approval + configuration gating around facebook.py
  scheduler.py     Opt-in batch generation / approved-post publishing loop
  web.py           Flask review dashboard
  cli.py           Command-line interface
templates/         Jinja templates for the dashboard
static/            Dashboard CSS
tests/             Pytest suite (offline providers, no network required)
```

### Generation pipeline

1. Sample a category (or use the requested one).
2. Sample a blueprint: heritage, age, hair, eyes, face, build, expression,
   outfit, accessories, pose, background, camera angle, lens, lighting, time of
   day, colour grade, film look, plus a random seed.
3. Reject the blueprint if its fingerprint already exists, or if it repeats
   recent pose/outfit/background/angle values for that category.
4. Render the positive and negative prompt and call the configured free provider
   (with an automatic fallback provider if the primary fails).
5. Normalise to JPEG at the configured size, compute SHA-256 + perceptual hashes,
   and compare against every stored post.
6. If a duplicate is found, discard the image, log the event and resample.
7. Build a unique title, caption and hashtag set, then store the post as
   `pending` for human review.

### Publishing safety

* `pending` -> (human) `approved` / `rejected`
* `approved` -> publish only when `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` exist
  and either a human clicks **Publish** or `AUTO_PUBLISH=true`.
* Failures are stored on the post and in the audit log; nothing is retried
  blindly and nothing is published twice (`facebook_post_id` is persisted).

## 4. Rollout steps

1. `pip install -r requirements.txt`
2. `cp .env.example .env` and fill only what you need.
3. `python -m app.cli init-db` then `python -m app.cli generate --count 3`
4. Review in `python -m app.web` (or `flask --app app.web run`).
5. Add Page credentials, run `python -m app.cli test-facebook`, then approve and
   publish one post manually.
6. Optionally run `python -m app.scheduler` on a persistent host for automation.
