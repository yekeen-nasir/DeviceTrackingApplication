"""Local storage queue for offline telemetry."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from contextlib import contextmanager

from libs.core.logging import setup_logging

logger = setup_logging("tracker-agent.storage")


class LocalQueue:
    """SQLite-backed offline queue for telemetry and pending uploads."""

    def __init__(self, db_path: Path):
        """
        Initialize the local queue.

        Ensures the directories exist and creates the SQLite schema.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ----------------------------------------------------------------------
    # Internal DB Helpers
    # ----------------------------------------------------------------------

    def _init_db(self):
        """Initialize SQLite database schema."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retries INTEGER DEFAULT 0
                )
            """)

    @contextmanager
    def _get_conn(self):
        """Database connection with safety handling."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"SQLite error: {e}")
            raise
        finally:
            conn.close()

    # ----------------------------------------------------------------------
    # Queue Operations
    # ----------------------------------------------------------------------

    def enqueue(self, data: Dict[str, Any]):
        """Add an item to the queue."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO queue (data) VALUES (?)",
                (json.dumps(data),),
            )
        logger.debug("Enqueued item into local queue")

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Remove and return the oldest item."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, data FROM queue ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()

            if not row:
                return None

            item_id, data = row
            conn.execute("DELETE FROM queue WHERE id = ?", (item_id,))
            
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.error("Corrupted JSON in queue entry — discarded")
                return None

    def dequeue_with_id(self) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Dequeue and return (id, data), used for retry logic.
        Does NOT increment retries automatically.
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, data FROM queue ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()

            if not row:
                return None

            item_id, data = row
            conn.execute("DELETE FROM queue WHERE id = ?", (item_id,))

            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                logger.error("Corrupted JSON in queue entry — discarded")
                return None

            return item_id, parsed

    def requeue(self, data: Dict[str, Any], retries: int):
        """
        Put an item back into the queue with updated retry count.
        Used when sending to server fails.
        """
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO queue (data, retries) VALUES (?, ?)",
                (json.dumps(data), retries)
            )
        logger.debug(f"Requeued item (retry={retries})")

    # ----------------------------------------------------------------------
    # Inspection and Utility Methods
    # ----------------------------------------------------------------------

    def peek(self) -> Optional[Dict[str, Any]]:
        """Return the next item without deleting it."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT data FROM queue ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return None

    def size(self) -> int:
        """Get the number of queued items."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM queue")
            return cursor.fetchone()[0]

    def increment_retry(self, item_id: int) -> None:
        """Increase retry count for a queued item."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE queue SET retries = retries + 1 WHERE id = ?",
                (item_id,),
            )

    def get_failed(self, max_retries: int) -> List[Dict[str, Any]]:
        """
        Retrieve entries that have exceeded retry limits.
        Typically used to discard or log permanently failed items.
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT data FROM queue WHERE retries >= ?",
                (max_retries,),
            )
            rows = cursor.fetchall()

        results = []
        for (data,) in rows:
            try:
                results.append(json.loads(data))
            except json.JSONDecodeError:
                continue

        return results

    def clear(self):
        """Delete all queue entries."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM queue")
        logger.warning("Local queue cleared")

    def list_all(self) -> List[Dict[str, Any]]:
        """Debug helper — return all queued items."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT data FROM queue ORDER BY id ASC")
            rows = cursor.fetchall()

        items = []
        for (data,) in rows:
            try:
                items.append(json.loads(data))
            except json.JSONDecodeError:
                continue
        return items
