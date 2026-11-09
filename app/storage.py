"""SQLite persistence for posts, uniqueness signatures and audit events."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app import dedupe

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    title TEXT NOT NULL,
    caption TEXT NOT NULL,
    hashtags TEXT NOT NULL,
    prompt TEXT NOT NULL,
    negative_prompt TEXT NOT NULL DEFAULT '',
    blueprint TEXT NOT NULL,
    seed INTEGER NOT NULL DEFAULT 0,
    provider TEXT NOT NULL DEFAULT '',
    image_path TEXT NOT NULL,
    image_sha256 TEXT NOT NULL,
    phash TEXT NOT NULL,
    ahash TEXT NOT NULL,
    prompt_fingerprint TEXT NOT NULL,
    caption_signature TEXT NOT NULL,
    hashtag_signature TEXT NOT NULL,
    approved_at TEXT,
    published_at TEXT,
    facebook_post_id TEXT,
    permalink TEXT,
    error TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_prompt_fingerprint
    ON posts(prompt_fingerprint);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_phash ON posts(phash);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
"""

EDITABLE_COLUMNS = {
    "status",
    "title",
    "caption",
    "hashtags",
    "approved_at",
    "published_at",
    "facebook_post_id",
    "permalink",
    "error",
    "provider",
}

STATUSES = ("pending", "approved", "rejected", "published", "failed")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    """Small SQLite repository. One connection per operation keeps it safe
    across Flask worker threads and the scheduler loop."""

    def __init__(self, database_path: str | Path, media_dir: str | Path) -> None:
        self.database_path = Path(database_path)
        self.media_dir = Path(media_dir)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.init_db()

    # -- plumbing --------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def init_db(self) -> None:
        with closing(self.connect()) as connection, connection:
            connection.executescript(SCHEMA)

    # -- posts -----------------------------------------------------------
    def create_post(self, fields: dict) -> str:
        post_id = fields.get("id") or uuid.uuid4().hex[:12]
        now = utcnow()
        payload = {
            "id": post_id,
            "created_at": fields.get("created_at", now),
            "updated_at": now,
            "category": fields["category"],
            "status": fields.get("status", "pending"),
            "title": fields["title"],
            "caption": fields["caption"],
            "hashtags": json.dumps(fields.get("hashtags", []), ensure_ascii=False),
            "prompt": fields["prompt"],
            "negative_prompt": fields.get("negative_prompt", ""),
            "blueprint": json.dumps(fields.get("blueprint", {}), ensure_ascii=False),
            "seed": int(fields.get("seed", 0)),
            "provider": fields.get("provider", ""),
            "image_path": fields["image_path"],
            "image_sha256": fields["image_sha256"],
            "phash": fields["phash"],
            "ahash": fields["ahash"],
            "prompt_fingerprint": fields["prompt_fingerprint"],
            "caption_signature": fields["caption_signature"],
            "hashtag_signature": fields["hashtag_signature"],
        }
        columns = ", ".join(payload)
        placeholders = ", ".join(f":{name}" for name in payload)
        with closing(self.connect()) as connection, connection:
            connection.execute(f"INSERT INTO posts ({columns}) VALUES ({placeholders})", payload)
        return post_id

    def update_post(self, post_id: str, **fields) -> None:
        updates = {key: value for key, value in fields.items() if key in EDITABLE_COLUMNS}
        if not updates:
            return
        if "hashtags" in updates and isinstance(updates["hashtags"], list):
            updates["hashtags"] = json.dumps(updates["hashtags"], ensure_ascii=False)
        updates["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = :{key}" for key in updates)
        updates["post_id"] = post_id
        with closing(self.connect()) as connection, connection:
            connection.execute(f"UPDATE posts SET {assignments} WHERE id = :post_id", updates)

    @staticmethod
    def _row_to_post(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        post = dict(row)
        try:
            post["hashtags"] = json.loads(post.get("hashtags") or "[]")
        except (TypeError, ValueError):
            post["hashtags"] = []
        try:
            post["blueprint"] = json.loads(post.get("blueprint") or "{}")
        except (TypeError, ValueError):
            post["blueprint"] = {}
        post["image_file"] = Path(post["image_path"]).name
        return post

    def get_post(self, post_id: str) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return self._row_to_post(row)

    def list_posts(self, status: str | None = None, limit: int = 60, offset: int = 0) -> list[dict]:
        query = "SELECT * FROM posts"
        params: list = []
        if status and status != "all":
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with closing(self.connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_post(row) for row in rows]

    def counts(self) -> dict[str, int]:
        counts = {status: 0 for status in STATUSES}
        with closing(self.connect()) as connection:
            for row in connection.execute("SELECT status, COUNT(*) AS total FROM posts GROUP BY status"):
                counts[row["status"]] = row["total"]
        counts["total"] = sum(counts[status] for status in STATUSES)
        return counts

    def delete_post(self, post_id: str) -> bool:
        post = self.get_post(post_id)
        if not post:
            return False
        with closing(self.connect()) as connection, connection:
            connection.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        try:
            Path(post["image_path"]).unlink(missing_ok=True)
        except OSError:
            pass
        self.add_event(post_id, "deleted", "Post removed from the review queue")
        return True

    # -- uniqueness checks ----------------------------------------------
    def prompt_fingerprint_exists(self, fingerprint: str) -> bool:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM posts WHERE prompt_fingerprint = ? LIMIT 1", (fingerprint,)
            ).fetchone()
        return row is not None

    def signature_exists(self, column: str, value: str) -> bool:
        if column not in {"caption_signature", "hashtag_signature"}:
            raise ValueError(f"Unsupported signature column: {column}")
        with closing(self.connect()) as connection:
            row = connection.execute(
                f"SELECT 1 FROM posts WHERE {column} = ? LIMIT 1", (value,)
            ).fetchone()
        return row is not None

    def title_exists(self, title: str) -> bool:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM posts WHERE lower(title) = lower(?) LIMIT 1", (title,)
            ).fetchone()
        return row is not None

    def find_duplicate(
        self, dhash_value: str, ahash_value: str, sha256_value: str, threshold: int = 6
    ) -> dict | None:
        """Return the closest existing post if the image is a duplicate."""
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, status, title, phash, ahash, image_sha256 FROM posts"
            ).fetchall()
        best: dict | None = None
        best_distance = 65
        for row in rows:
            if row["image_sha256"] == sha256_value:
                return {
                    "id": row["id"],
                    "status": row["status"],
                    "title": row["title"],
                    "distance": 0,
                    "reason": "identical file",
                }
            distance = min(
                dedupe.hamming(dhash_value, row["phash"]),
                dedupe.hamming(ahash_value, row["ahash"]),
            )
            if dedupe.is_duplicate(dhash_value, ahash_value, row["phash"], row["ahash"], threshold):
                if distance < best_distance:
                    best_distance = distance
                    best = {
                        "id": row["id"],
                        "status": row["status"],
                        "title": row["title"],
                        "distance": distance,
                        "reason": "perceptual match",
                    }
        return best

    def recent_blueprints(self, category: str | None = None, limit: int = 40) -> list[dict]:
        query = "SELECT blueprint FROM posts"
        params: list = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params.append(limit)
        with closing(self.connect()) as connection:
            rows = connection.execute(query, params).fetchall()
        blueprints = []
        for row in rows:
            try:
                blueprints.append(json.loads(row["blueprint"] or "{}"))
            except (TypeError, ValueError):
                continue
        return blueprints

    # -- audit trail -----------------------------------------------------
    def add_event(self, post_id: str | None, kind: str, message: str) -> None:
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "INSERT INTO events (post_id, kind, message, created_at) VALUES (?, ?, ?, ?)",
                (post_id, kind, message[:2000], utcnow()),
            )

    def list_events(self, limit: int = 40) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
