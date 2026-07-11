"""Shared helpers for converting internal DB rows / stats dicts into the
API-facing (camelCase) shape the frontend expects.

Deliberately has zero imports from database.py / pipeline.py / main.py so it
can be imported by both main.py (REST responses) and pipeline.py (SSE events)
without creating a circular import between the two.
"""
from typing import Any, Dict, Optional


def format_stats(stats: Dict[str, int]) -> Dict[str, int]:
    """Normalize the raw stats dict from Database.get_stats() into the
    camelCase shape the frontend's PipelineContext expects. This is the one
    place `bad_framing` -> `badFraming` translation happens, so REST
    responses and SSE events never disagree on the key name.
    """
    return {
        "total": stats.get("total", 0),
        "pending": stats.get("pending", 0),
        "accepted": stats.get("accepted", 0),
        "rejected": stats.get("rejected", 0),
        "error": stats.get("error", 0),
        "corrupt": stats.get("corrupt", 0),
        "irrelevant": stats.get("irrelevant", 0),
        "badFraming": stats.get("bad_framing", 0),
    }


def format_image_row(row: Dict[str, Any], detailed: bool = False) -> Dict[str, Any]:
    size_str = f"{row['file_size_bytes'] / (1024 * 1024):.1f} MB" if row.get("file_size_bytes") else "—"
    dim_str = f"{row['width']}x{row['height']}" if row.get("width") else "—"

    # Prefer the framing score (later, more holistic pipeline stage) but fall
    # back to the relevance score. Use explicit None-checks rather than `or`
    # so a legitimate score of 0.0 isn't mistaken for "missing".
    framing_score = row.get("framing_score")
    relevance_score = row.get("relevance_score")
    score: Optional[float] = framing_score if framing_score is not None else relevance_score

    result = {
        "id": row["id"],
        "filename": row["filename"],
        "url": f"/api/images/{row['id']}/full",
        "thumbnailUrl": f"/api/images/{row['id']}/thumb",
        "status": row["status"],
        "score": score,
        "reason": row.get("corrupt_reason") or row.get("relevance_reason") or row.get("framing_reason"),
        "fileSize": size_str,
        "dimensions": dim_str,
        "width": row.get("width"),
        "height": row.get("height"),
        "detections": row.get("detections"),
    }

    if detailed:
        result["metadata"] = {k: v for k, v in row.items() if v is not None and k != "image_data"}

    return result
