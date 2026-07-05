import asyncio
from typing import Optional, Callable
from io import BytesIO

from PIL import Image

from config import settings
from database import db
from filters import CorruptFilter, RelevanceFilter, FramingFilter


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
        self.current_stage = None
        self.on_progress: Optional[Callable] = None
        self.filters = {
            "corrupt": CorruptFilter(),
            "relevance": RelevanceFilter(device=settings.device),
            "framing": FramingFilter(device=settings.device),
        }

    def _emit(self, stage: str, progress: float, stats: dict, message: str = "", level: str = "info"):
        self.current_stage = stage
        self.progress = progress
        if self.on_progress:
            asyncio.create_task(self.on_progress({
                "type": "progress",
                "stage": stage,
                "progress": progress,
                "stats": stats,
                "message": message,
                "level": level,
            }))

    async def run(self, config_override: Optional[dict] = None):
        self.running = True
        self.cancelled = False

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

        pending = db.get_pending()
        total = len(pending)
        if total == 0:
            self._emit("Complete", 100.0, db.get_stats(), "No pending images", "info")
            self.running = False
            return

        accepted = rejected = errors = 0

        for idx, record in enumerate(pending):
            if self.cancelled:
                break

            progress = (idx / total) * 100
            stats = db.get_stats()
            self._emit("Processing", progress, stats, f"Processing {record['filename']}")

            try:
                success = await self._process_single(record, cfg)
                if success:
                    accepted += 1
                else:
                    rejected += 1
            except Exception as e:
                errors += 1
                db.update_status(record["id"], "error", corrupt_reason=f"pipeline_crash: {e}")
                self._emit("Error", progress, db.get_stats(), str(e), "error")

        final_stats = db.get_stats()
        self._emit("Complete", 100.0, final_stats, "Pipeline complete", "info")
        self.running = False

    async def _process_single(self, record: dict, cfg: dict) -> bool:
        image_id = record["id"]
        image_bytes = db.get_image_data(image_id)

        if image_bytes is None:
            db.update_status(image_id, "error", corrupt_reason="image_data_missing")
            return False

        if cfg["corrupt_enabled"]:
            ok, score, reason = self.filters["corrupt"].check_bytes(image_bytes, min_size=cfg["min_image_size"])
            if not ok:
                db.update_status(image_id, "rejected", corrupt_pass=False, corrupt_reason=reason)
                return False

        if cfg["relevance_enabled"]:
            ok, score, reason = self.filters["relevance"].check_bytes(
                image_bytes,
                settings.dog_prompts,
                settings.not_dog_prompts,
                cfg["relevance_threshold"],
            )
            if not ok:
                db.update_status(image_id, "rejected", relevance_score=score, relevance_reason=reason)
                return False

        if cfg["framing_enabled"]:
            ok, score, reason, detections = self.filters["framing"].check_bytes(
                image_bytes,
                confidence=cfg["dog_confidence"],
                min_box_ratio=cfg["min_box_ratio"],
                max_box_ratio=cfg["max_box_ratio"],
            )
            if not ok:
                db.update_status(image_id, "rejected", framing_score=score, framing_reason=reason,
                                 detections=detections)
                return False
            db.update_status(image_id, "accepted", detections=detections, framing_score=score)
        else:
            db.update_status(image_id, "accepted")

        return True

    def stop(self):
        self.cancelled = True


pipeline = Pipeline()