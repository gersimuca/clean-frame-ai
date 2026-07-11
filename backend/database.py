import sqlite3
import json
import struct
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from config import settings

# Maps the "reason" categories used by the review UI (corrupt / irrelevant /
# bad-framing) to the DB column that is populated when an image is rejected
# for that reason. These are NOT values of the `status` column - `status` is
# only ever 'pending' | 'accepted' | 'rejected' | 'error'. Keeping this as a
# whitelist dict (rather than interpolating caller input into SQL) is what
# keeps the f-string in get_by_reason/count_by_reason safe.
REASON_COLUMNS = {
    "corrupt": "corrupt_reason",
    "irrelevant": "relevance_reason",
    "bad-framing": "framing_reason",
}

_IMAGE_COLUMNS = """id, filename, file_size_bytes, width, height, status, corrupt_pass, corrupt_reason,
                    relevance_score, relevance_reason, framing_score, framing_reason, detections,
                    processed_at, accepted_at"""


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
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    width INTEGER,
                    height INTEGER,
                    image_data BLOB,
                    thumbnail_data BLOB,
                    status TEXT DEFAULT 'pending',
                    corrupt_pass INTEGER,
                    corrupt_reason TEXT,
                    relevance_score REAL,
                    relevance_reason TEXT,
                    framing_score REAL,
                    framing_reason TEXT,
                    detections TEXT,
                    processed_at TIMESTAMP,
                    accepted_at TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON images(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON images(filename)")
            conn.commit()

    def register_image(self, filename: str, file_size: int, image_bytes: bytes, thumbnail_bytes: bytes, width: int, height: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO images (filename, file_size_bytes, image_data, thumbnail_data, width, height, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (filename, file_size, image_bytes, thumbnail_bytes, width, height),
            )
            return cursor.lastrowid

    def get_image_data(self, image_id: int, thumbnail: bool = False) -> Optional[bytes]:
        with self._connect() as conn:
            col = "thumbnail_data" if thumbnail else "image_data"
            row = conn.execute(f"SELECT {col} FROM images WHERE id = ?", (image_id,)).fetchone()
            return row[0] if row else None

    def get_pending(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            sql = f"SELECT {_IMAGE_COLUMNS} FROM images WHERE status = 'pending' ORDER BY id"
            if limit:
                sql += f" LIMIT {limit}"
            rows = conn.execute(sql).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_by_status(self, status: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_IMAGE_COLUMNS} FROM images WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def count_by_status(self, status: str) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM images WHERE status = ?", (status,)).fetchone()[0]

    def get_by_reason(self, reason_type: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        column = REASON_COLUMNS.get(reason_type)
        if not column:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_IMAGE_COLUMNS} FROM images WHERE {column} IS NOT NULL ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def count_by_reason(self, reason_type: str) -> int:
        column = REASON_COLUMNS.get(reason_type)
        if not column:
            return 0
        with self._connect() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM images WHERE {column} IS NOT NULL").fetchone()[0]

    def get_all_invalid(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                f"""SELECT {_IMAGE_COLUMNS}
                   FROM images 
                   WHERE status IN ('rejected', 'error') 
                   ORDER BY id DESC"""
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_IMAGE_COLUMNS} FROM images WHERE id = ?",
                (image_id,)
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def update_status(self, image_id: int, status: str, **kwargs):
        fields = ["status = ?", "processed_at = ?"]
        values = [status, datetime.now()]

        for key, val in kwargs.items():
            if key == "detections":
                val = json.dumps(val) if val else None
            elif hasattr(val, "item") and not isinstance(val, (bytes, bytearray, memoryview)):
                # Catches numpy/torch scalar types (e.g. numpy.float32).
                # sqlite3 accepts these as bind parameters without error via
                # the buffer protocol and silently stores them as raw BLOB
                # bytes instead of the number they represent - the same bug
                # that corrupted framing_score. `.item()` unwraps them to a
                # native Python int/float that sqlite3 stores correctly.
                try:
                    val = val.item()
                except (ValueError, TypeError):
                    pass
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
                """UPDATE images SET status = 'pending', corrupt_pass = NULL, corrupt_reason = NULL,
                   relevance_score = NULL, relevance_reason = NULL, framing_score = NULL,
                   framing_reason = NULL, detections = NULL, processed_at = NULL
                   WHERE id = ?""",
                (image_id,),
            )

    def delete_image(self, image_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,))

    def clear_all(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM images")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("detections"):
            try:
                d["detections"] = json.loads(d["detections"])
            except (json.JSONDecodeError, TypeError):
                d["detections"] = None
        for key in ("relevance_score", "framing_score"):
            d[key] = _recover_real_from_blob(d.get(key))
        return d


def _recover_real_from_blob(value):
    """Best-effort recovery for a REAL column that was previously corrupted
    into raw BLOB bytes by the numpy-scalar bug (see framing_filter.py /
    update_status). A numpy.float32/float64 passed straight to sqlite3 gets
    silently stored as its raw little-endian byte representation instead of
    raising an error, so existing databases can have real, recoverable
    scores sitting behind a `bytes` value. If we can unpack it back to a
    float, return that; otherwise fall back to None rather than letting a
    raw bytes object reach the API and crash JSON serialization."""
    if not isinstance(value, (bytes, bytearray)):
        return value
    try:
        if len(value) == 4:
            return struct.unpack("<f", value)[0]
        if len(value) == 8:
            return struct.unpack("<d", value)[0]
    except struct.error:
        pass
    return None


db = Database(settings.db_path)
