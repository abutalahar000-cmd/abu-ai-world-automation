"""Opt-in background scheduler.

Nothing runs on a timer unless you start it explicitly. Even then, publishing
only happens for posts that are already approved and only when AUTO_PUBLISH=true.
"""

from __future__ import annotations

import logging
import signal
import time

from app import generator, publisher

LOGGER = logging.getLogger(__name__)


def run_once(storage, settings) -> dict:
    outcome = generator.generate_batch(
        storage,
        settings,
        count=settings.posts_per_run,
    )
    published = publisher.auto_publish_approved(storage, settings, limit=settings.posts_per_run)
    return {
        "generated": [post["id"] for post in outcome.created],
        "errors": outcome.errors,
        "published": [post["id"] for post in published],
        "auto_publish": settings.auto_publish,
    }


def main(storage, settings) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    running = True

    def _stop(_signum, _frame):
        nonlocal running
        running = False
        LOGGER.info("Scheduler stopping after the current cycle")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    LOGGER.info(
        "Scheduler started: %s post(s) every %s minutes, auto_publish=%s, approval_required=%s",
        settings.posts_per_run,
        settings.scheduler_interval_minutes,
        settings.auto_publish,
        settings.require_approval,
    )
    while running:
        try:
            result = run_once(storage, settings)
            LOGGER.info("Cycle finished: %s", result)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            LOGGER.exception("Scheduler cycle failed: %s", exc)
        for _ in range(settings.scheduler_interval_minutes * 60):
            if not running:
                break
            time.sleep(1)
