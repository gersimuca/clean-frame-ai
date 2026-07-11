import asyncio
import time
from typing import Optional, List
from io import BytesIO

from PIL import Image

from config import settings
from database import db
from filters import CorruptFilter, RelevanceFilter, FramingFilter
from serializers import format_image_row, format_stats


def create_thumbnail(image_bytes: bytes, size: tuple = (256, 256)) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    img.thumbnail(size, Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class Pipeline:
    def __init__(self):
        self.running = False
        self.cancelled = False
        self.progress = 0.0
        self.current_stage: Optional[str] = None
        self.subscribers: List[asyncio.Queue] = []
        self.filters = {
            "corrupt": CorruptFilter(),
            "relevance": RelevanceFilter(device=settings.device),
            "framing": FramingFilter(device=settings.device),
        }

    # ---- pub/sub, so any number of SSE connections can watch progress live ----
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)

    def snapshot(self) -> dict:
        """Current state for a client that just connected (e.g. page refresh
        mid-run), so it doesn't have to wait for the next event to sync up."""
        return {
            "type": "snapshot",
            "running": self.running,
            "progress": self.progress,
            "stage": self.current_stage,
            "stats": format_stats(db.get_stats()),
        }

    def _emit(self, event: dict) -> None:
        for q in list(self.subscribers):
            q.put_nowait(event)

    def _emit_progress(self, stage, progress, rate, eta_seconds, message="", level="info"):
        self.current_stage = stage
        self.progress = progress
        self._emit({
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "rate": round(rate, 2),
            "eta_seconds": round(eta_seconds) if eta_seconds is not None else None,
            "stats": format_stats(db.get_stats()),
            "message": message,
            "level": level,
        })

    # ---- main run loop ----
    async def run(self, config_override: Optional[dict] = None):
        if self.running:
            return
        self.running = True
        self.cancelled = False
        config_override = config_override or {}

        cfg = {
            "corrupt_enabled": config_override.get("corrupt_enabled", settings.corrupt_enabled),
            "relevance_enabled": config_override.get("relevance_enabled", settings.relevance_enabled),
            "framing_enabled": config_override.get("framing_enabled", settings.framing_enabled),
            "relevance_threshold": config_override.get("relevance_threshold", settings.relevance_threshold),
            "dog_confidence": config_override.get("dog_confidence", settings.dog_confidence),
            "min_box_ratio": config_override.get("min_box_ratio", settings.min_box_ratio),
            "max_box_ratio": config_override.get("max_box_ratio", settings.max_box_ratio),
            "min_image_size": config_override.get("min_image_size", settings.min_image_size),
        }

        try:
            pending = db.get_pending()
            total = len(pending)

            if total == 0:
                self._emit_progress("Complete", 100.0, 0.0, None, "No pending images")
                self._emit({"type": "complete", "progress": 100.0, "stats": format_stats(db.get_stats()),
                            "message": "No pending images"})
                return

            start_time = time.monotonic()

            for idx, record in enumerate(pending):
                if self.cancelled:
                    break

                elapsed = time.monotonic() - start_time
                rate = idx / elapsed if elapsed > 0.5 else 0.0
                eta = ((total - idx) / rate) if rate > 0 else None

                self._emit_progress(
                    "Processing", (idx / total) * 100, rate, eta,
                    message=f"Processing {record['filename']}",
                )

                try:
                    accepted = await self._process_single(record, cfg)
                    row = db.get_by_id(record["id"])

                    elapsed = time.monotonic() - start_time
                    rate = (idx + 1) / elapsed if elapsed > 0.5 else 0.0
                    eta = ((total - (idx + 1)) / rate) if rate > 0 else None

                    self.progress = ((idx + 1) / total) * 100
                    self._emit({
                        "type": "image_result",
                        "progress": self.progress,
                        "rate": round(rate, 2),
                        "eta_seconds": round(eta) if eta is not None else None,
                        "stats": format_stats(db.get_stats()),
                        "image": format_image_row(row) if row else None,
                        "message": f"{'Accepted' if accepted else 'Rejected'}: {record['filename']}",
                        "level": "info" if accepted else "warn",
                    })
                except Exception as e:
                    db.update_status(record["id"], "error", corrupt_reason=f"pipeline_crash: {e}")
                    self._emit_progress(
                        "Error", ((idx + 1) / total) * 100, 0.0, None,
                        message=f"Failed on {record['filename']}: {e}", level="error",
                    )

            final_stats = format_stats(db.get_stats())
            message = "Pipeline stopped by user" if self.cancelled else "Pipeline complete"
            self.progress = 100.0
            self.current_stage = "Complete"
            self._emit({"type": "complete", "progress": 100.0, "stats": final_stats, "message": message})

        except Exception as e:
            self._emit({"type": "error", "message": f"Pipeline crashed: {e}", "level": "error"})
        finally:
            self.running = False
            self.cancelled = False

    async def _process_single(self, record: dict, cfg: dict) -> bool:
        image_id = record["id"]
        image_bytes = db.get_image_data(image_id)

        if image_bytes is None:
            db.update_status(image_id, "error", corrupt_reason="image_data_missing")
            return False

        # Each filter call below is synchronous, CPU/GPU-bound model inference
        # (CLIP, Faster R-CNN). Running it directly on the event loop would
        # block *every* connected request - including the SSE stream - for
        # the full duration of each inference call, which is why progress
        # previously appeared to freeze instead of updating live. Pushing it
        # onto a worker thread keeps the loop free to flush events as they
        # happen.
        if cfg["corrupt_enabled"]:
            ok, _, reason = await asyncio.to_thread(
                self.filters["corrupt"].check_bytes, image_bytes, min_size=cfg["min_image_size"]
            )
            if not ok:
                db.update_status(image_id, "rejected", corrupt_pass=False, corrupt_reason=reason)
                return False

        extra = {}
        if cfg["relevance_enabled"]:
            ok, score, reason = await asyncio.to_thread(
                self.filters["relevance"].check_bytes,
                image_bytes, settings.dog_prompts, settings.not_dog_prompts, cfg["relevance_threshold"],
            )
            if not ok:
                db.update_status(image_id, "rejected", relevance_score=score, relevance_reason=reason)
                return False
            # Keep the score even on a pass, so accepted images still show a
            # quality score if framing is disabled or never overwrites it.
            extra["relevance_score"] = score

        if cfg["framing_enabled"]:
            ok, score, reason, detections = await asyncio.to_thread(
                self.filters["framing"].check_bytes,
                image_bytes,
                confidence=cfg["dog_confidence"],
                min_box_ratio=cfg["min_box_ratio"],
                max_box_ratio=cfg["max_box_ratio"],
            )
            if not ok:
                db.update_status(image_id, "rejected", framing_score=score, framing_reason=reason,
                                  detections=detections, **extra)
                return False
            db.update_status(image_id, "accepted", detections=detections, framing_score=score, **extra)
        else:
            db.update_status(image_id, "accepted", **extra)

        return True

    def stop(self):
        self.cancelled = True


pipeline = Pipeline()
