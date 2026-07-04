import shutil
import asyncio
from pathlib import Path
from typing import Optional, Callable
from config import settings
from database import db
from filters import CorruptFilter, RelevanceFilter, FramingFilter


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

    def _ensure_dirs(self):
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        settings.rejected_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("corrupt", "irrelevant", "bad_framing", "other"):
            (settings.rejected_dir / sub).mkdir(parents=True, exist_ok=True)

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
        self._ensure_dirs()

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
        filepath = Path(record["filepath"])
        image_id = record["id"]

        # Stage 1: Corrupt
        if cfg["corrupt_enabled"]:
            ok, score, reason = self.filters["corrupt"].check(filepath, min_size=cfg["min_image_size"])
            if not ok:
                self._reject(image_id, filepath, "corrupt", corrupt_pass=False, corrupt_reason=reason)
                return False

        # Stage 2: Relevance
        if cfg["relevance_enabled"]:
            ok, score, reason = self.filters["relevance"].check(
                filepath,
                settings.dog_prompts,
                settings.not_dog_prompts,
                cfg["relevance_threshold"],
            )
            if not ok:
                self._reject(image_id, filepath, "irrelevant", relevance_score=score, relevance_reason=reason)
                return False

        # Stage 3: Framing
        if cfg["framing_enabled"]:
            ok, score, reason, detections = self.filters["framing"].check(
                filepath,
                confidence=cfg["dog_confidence"],
                min_box_ratio=cfg["min_box_ratio"],
                max_box_ratio=cfg["max_box_ratio"],
            )
            if not ok:
                self._reject(image_id, filepath, "bad_framing", framing_score=score, framing_reason=reason, detections=detections)
                return False
            db.update_status(image_id, "accepted", detections=detections, framing_score=score)
        else:
            db.update_status(image_id, "accepted")

        # Copy to output
        dest = settings.output_dir / filepath.name
        if dest.exists():
            dest = dest.with_stem(f"{dest.stem}_{filepath.stat().st_mtime}")
        shutil.copy2(filepath, dest)
        db.update_filepath(image_id, str(dest))
        return True

    def _reject(self, image_id: int, filepath: Path, category: str, **kwargs):
        dest = settings.rejected_dir / category / filepath.name
        if dest.exists():
            dest = dest.with_stem(f"{dest.stem}_{filepath.stat().st_mtime}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, dest)
        db.update_status(image_id, "rejected", **kwargs)

    def stop(self):
        self.cancelled = True


pipeline = Pipeline()