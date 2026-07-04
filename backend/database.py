import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from config import settings


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS images
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             filepath
                             TEXT
                             UNIQUE
                             NOT
                             NULL,
                             filename
                             TEXT
                             NOT
                             NULL,
                             file_size_bytes
                             INTEGER,
                             width
                             INTEGER,
                             height
                             INTEGER,
                             status
                             TEXT
                             DEFAULT
                             'pending',
                             corrupt_pass
                             INTEGER,
                             corrupt_reason
                             TEXT,
                             relevance_score
                             REAL,
                             relevance_reason
                             TEXT,
                             framing_score
                             REAL,
                             framing_reason
                             TEXT,
                             detections
                             TEXT,
                             processed_at
                             TIMESTAMP,
                             accepted_at
                             TIMESTAMP
                         )
                         """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON images(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON images(filename)")
            conn.commit()

    def register_files(self, filepaths: List[Path]):
        with self._connect() as conn:
            for fp in filepaths:
                try:
                    size = fp.stat().st_size
                    conn.execute(
                        """INSERT
                        OR IGNORE INTO images 
                           (filepath, filename, file_size_bytes) VALUES (?, ?, ?)""",
                        (str(fp.resolve()), fp.name, size),
                    )
                except Exception:
                    pass

    def get_pending(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            sql = "SELECT * FROM images WHERE status = 'pending' ORDER BY id"
            if limit:
                sql += f" LIMIT {limit}"
            rows = conn.execute(sql).fetchall()
            return [dict(row) for row in rows]

    def get_by_status(self, status: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM images WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def update_status(self, image_id: int, status: str, **kwargs):
        fields = ["status = ?", "processed_at = ?"]
        values = [status, datetime.now()]

        for key, val in kwargs.items():
            if key == "detections":
                val = json.dumps(val) if val else None
            fields.append(f"{key} = ?")
            values.append(val)

        values.append(image_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE images SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            if status == "accepted":
                conn.execute(
                    "UPDATE images SET accepted_at = ? WHERE id = ?",
                    (datetime.now(), image_id),
                )

    def update_filepath(self, image_id: int, filepath: str):
        with self._connect() as conn:
            conn.execute("UPDATE images SET filepath = ? WHERE id = ?", (filepath, image_id))

    def get_stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM images WHERE status = 'pending'").fetchone()[0]
            accepted = conn.execute("SELECT COUNT(*) FROM images WHERE status = 'accepted'").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM images WHERE status = 'rejected'").fetchone()[0]
            error = conn.execute("SELECT COUNT(*) FROM images WHERE status = 'error'").fetchone()[0]

            corrupt = conn.execute(
                "SELECT COUNT(*) FROM images WHERE corrupt_reason IS NOT NULL"
            ).fetchone()[0]
            irrelevant = conn.execute(
                "SELECT COUNT(*) FROM images WHERE relevance_reason IS NOT NULL"
            ).fetchone()[0]
            bad_framing = conn.execute(
                "SELECT COUNT(*) FROM images WHERE framing_reason IS NOT NULL"
            ).fetchone()[0]

            return {
                "total": total,
                "pending": pending,
                "accepted": accepted,
                "rejected": rejected,
                "error": error,
                "corrupt": corrupt,
                "irrelevant": irrelevant,
                "bad_framing": bad_framing,
            }

    def reset_to_pending(self, image_id: int):
        with self._connect() as conn:
            conn.execute(
                """UPDATE images
                   SET status           = 'pending',
                       corrupt_pass     = NULL,
                       corrupt_reason   = NULL,
                       relevance_score  = NULL,
                       relevance_reason = NULL,
                       framing_score    = NULL,
                       framing_reason   = NULL,
                       detections       = NULL,
                       processed_at     = NULL
                   WHERE id = ?""",
                (image_id,),
            )

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("detections"):
            d["detections"] = json.loads(d["detections"])
        return d


db = Database(settings.db_path)