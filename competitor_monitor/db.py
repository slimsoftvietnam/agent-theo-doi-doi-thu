from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .util import iso_utc


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
 frequency TEXT NOT NULL, lookback_hours INTEGER NOT NULL, received INTEGER NOT NULL DEFAULT 0,
 new_items INTEGER NOT NULL DEFAULT 0, duplicates INTEGER NOT NULL DEFAULT 0,
 source_healthy INTEGER NOT NULL DEFAULT 0, source_limited INTEGER NOT NULL DEFAULT 0,
 source_errors INTEGER NOT NULL DEFAULT 0, error TEXT
);
CREATE TABLE IF NOT EXISTS items (
 item_id TEXT PRIMARY KEY, dedupe_key TEXT NOT NULL UNIQUE, canonical_url TEXT NOT NULL UNIQUE,
 source_id TEXT NOT NULL, source_name TEXT NOT NULL, source_type TEXT NOT NULL,
 title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', published_at TEXT,
 first_seen_at TEXT NOT NULL, author TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL,
 competitor_json TEXT NOT NULL DEFAULT '[]', topic_json TEXT NOT NULL DEFAULT '[]',
 relevance_score INTEGER NOT NULL DEFAULT 0, engagement_json TEXT NOT NULL DEFAULT '{}',
 evidence_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_source_id ON items(source_id);
CREATE TABLE IF NOT EXISTS run_items (
 run_id TEXT NOT NULL REFERENCES runs(run_id), item_id TEXT NOT NULL REFERENCES items(item_id),
 is_new INTEGER NOT NULL CHECK(is_new IN (0,1)), PRIMARY KEY(run_id,item_id)
);
CREATE TABLE IF NOT EXISTS source_checks (
 run_id TEXT NOT NULL REFERENCES runs(run_id), source_id TEXT NOT NULL, source_name TEXT NOT NULL,
 source_type TEXT NOT NULL, status TEXT NOT NULL, item_count INTEGER NOT NULL DEFAULT 0,
 method TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', checked_at TEXT NOT NULL,
 PRIMARY KEY(run_id,source_id)
);
PRAGMA user_version=1;
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self):
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def begin_run(self, run_id: str, frequency: str, lookback_hours: int) -> None:
        self.connection.execute(
            "INSERT INTO runs(run_id,started_at,status,frequency,lookback_hours) VALUES(?,?,?,?,?)",
            (run_id, iso_utc(), "RUNNING", frequency, lookback_hours),
        )
        self.connection.commit()

    def finish_run(self, run_id: str, status: str, summary: dict, error: str = "") -> None:
        self.connection.execute(
            """UPDATE runs SET finished_at=?,status=?,received=?,new_items=?,duplicates=?,
               source_healthy=?,source_limited=?,source_errors=?,error=? WHERE run_id=?""",
            (
                iso_utc(), status, summary.get("received", 0), summary.get("new_items", 0),
                summary.get("duplicates", 0), summary.get("source_healthy", 0),
                summary.get("source_limited", 0), summary.get("source_errors", 0), error or None, run_id,
            ),
        )
        self.connection.commit()

    def add_source_check(self, run_id: str, result) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO source_checks
               (run_id,source_id,source_name,source_type,status,item_count,method,error,checked_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (run_id, result.source_id, result.source_name, result.source_type, result.status,
             len(result.items), result.method, result.error, iso_utc()),
        )

    def save_item(self, run_id: str, item: dict) -> bool:
        existing = self.connection.execute(
            "SELECT item_id FROM items WHERE canonical_url=? OR dedupe_key=?",
            (item["canonical_url"], item["dedupe_key"]),
        ).fetchone()
        if existing:
            self.connection.execute(
                "INSERT OR IGNORE INTO run_items(run_id,item_id,is_new) VALUES(?,?,0)",
                (run_id, existing["item_id"]),
            )
            return False
        self.connection.execute(
            """INSERT INTO items
               (item_id,dedupe_key,canonical_url,source_id,source_name,source_type,title,summary,
                published_at,first_seen_at,author,kind,competitor_json,topic_json,relevance_score,
                engagement_json,evidence_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["item_id"], item["dedupe_key"], item["canonical_url"], item["source_id"],
                item["source_name"], item["source_type"], item["title"], item.get("summary", ""),
                item.get("published_at"), iso_utc(), item.get("author", ""), item["kind"],
                json.dumps(item.get("competitors", []), ensure_ascii=False),
                json.dumps(item.get("topics", []), ensure_ascii=False), int(item.get("relevance_score", 0)),
                json.dumps(item.get("engagement", {}), ensure_ascii=False),
                json.dumps(item.get("evidence", {}), ensure_ascii=False),
            ),
        )
        self.connection.execute(
            "INSERT INTO run_items(run_id,item_id,is_new) VALUES(?,?,1)", (run_id, item["item_id"])
        )
        return True

    def commit(self) -> None:
        self.connection.commit()

    def items_for_run(self, run_id: str, only_new: bool = True) -> list[dict]:
        condition = "AND ri.is_new=1" if only_new else ""
        rows = self.connection.execute(
            f"""SELECT i.*,ri.is_new FROM items i JOIN run_items ri ON ri.item_id=i.item_id
                WHERE ri.run_id=? {condition} ORDER BY i.published_at DESC,i.relevance_score DESC""",
            (run_id,),
        ).fetchall()
        return [self._decode(dict(row)) for row in rows]

    def items_between(self, start_iso: str, end_iso: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM items WHERE published_at>=? AND published_at<? ORDER BY published_at DESC",
            (start_iso, end_iso),
        ).fetchall()
        return [self._decode(dict(row)) for row in rows]

    def source_checks(self, run_id: str) -> list[dict]:
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM source_checks WHERE run_id=? ORDER BY status,source_id", (run_id,)
        ).fetchall()]

    def latest_runs(self, limit: int = 10) -> list[dict]:
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()]

    @staticmethod
    def _decode(item: dict) -> dict:
        item["competitors"] = json.loads(item.pop("competitor_json", "[]"))
        item["topics"] = json.loads(item.pop("topic_json", "[]"))
        item["engagement"] = json.loads(item.pop("engagement_json", "{}"))
        item["evidence"] = json.loads(item.pop("evidence_json", "{}"))
        return item
