import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import db
from pipeline import pipeline
from models import (
    PipelineConfig, ImageListResponse, ImageRecord,
    StatsResponse, ProgressMessage
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.rejected_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="PuraLens", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve thumbnails and images
if settings.static_dir.exists():
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.post("/api/pipeline/start")
async def start_pipeline(config: PipelineConfig):
    if pipeline.running:
        raise HTTPException(status_code=409, detail="Pipeline already running")

    # Register new files if input dir provided
    input_path = Path(config.input_dir)
    if input_path.exists():
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".tif"}
        files = [p for p in input_path.rglob("*") if p.suffix.lower() in exts]
        db.register_files(files)

    asyncio.create_task(pipeline.run(config.model_dump()))
    return {"status": "started"}


@app.post("/api/pipeline/stop")
async def stop_pipeline():
    pipeline.stop()
    return {"status": "stopping"}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(**db.get_stats())


@app.get("/api/images")
async def get_images(status: str, limit: int = 100, offset: int = 0):
    rows = db.get_by_status(status, limit=limit, offset=offset)
    total = db.get_stats().get("total", 0)

    images = []
    for row in rows:
        filepath = Path(row["filepath"])
        size_str = f"{row['file_size_bytes'] / (1024 * 1024):.1f} MB" if row.get("file_size_bytes") else "—"
        dim_str = f"{row['width']}x{row['height']}" if row.get("width") else "—"

        images.append({
            "id": row["id"],
            "filename": row["filename"],
            "filepath": str(filepath),
            "url": f"/api/images/{row['id']}/full",
            "thumbnailUrl": f"/api/images/{row['id']}/thumb",
            "status": row["status"],
            "score": row.get("relevance_score") or row.get("framing_score"),
            "reason": row.get("corrupt_reason") or row.get("relevance_reason") or row.get("framing_reason"),
            "fileSize": size_str,
            "dimensions": dim_str,
            "width": row.get("width"),
            "height": row.get("height"),
            "metadata": {k: v for k, v in row.items() if v is not None},
            "detections": row.get("detections"),
        })

    return {"images": images, "total": total}


@app.get("/api/images/{image_id}")
async def get_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    filepath = Path(row["filepath"])
    size_str = f"{row['file_size_bytes'] / (1024 * 1024):.1f} MB" if row.get("file_size_bytes") else "—"
    dim_str = f"{row['width']}x{row['height']}" if row.get("width") else "—"

    return {
        "id": row["id"],
        "filename": row["filename"],
        "url": f"/api/images/{image_id}/full",
        "thumbnailUrl": f"/api/images/{image_id}/thumb",
        "status": row["status"],
        "score": row.get("relevance_score") or row.get("framing_score"),
        "reason": row.get("corrupt_reason") or row.get("relevance_reason") or row.get("framing_reason"),
        "fileSize": size_str,
        "dimensions": dim_str,
        "width": row.get("width"),
        "height": row.get("height"),
        "metadata": {k: v for k, v in row.items() if v is not None},
        "detections": row.get("detections"),
    }


@app.post("/api/images/{image_id}/accept")
async def accept_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    src = Path(row["filepath"])
    dest = settings.output_dir / src.name
    if dest.exists():
        dest = dest.with_stem(f"{dest.stem}_{src.stat().st_mtime}")
    import shutil
    shutil.copy2(src, dest)
    db.update_status(image_id, "accepted")
    return {"status": "accepted"}


@app.post("/api/images/{image_id}/reject")
async def reject_image(image_id: int, category: str = "other"):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    src = Path(row["filepath"])
    dest = settings.rejected_dir / category / src.name
    if dest.exists():
        dest = dest.with_stem(f"{dest.stem}_{src.stat().st_mtime}")
    import shutil
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    db.update_status(image_id, "rejected")
    return {"status": "rejected"}


@app.post("/api/images/{image_id}/reprocess")
async def reprocess_image(image_id: int):
    db.reset_to_pending(image_id)
    return {"status": "pending"}


@app.websocket("/ws/pipeline")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def send_update(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    pipeline.on_progress = send_update

    try:
        while True:
            await asyncio.sleep(1)
            if not pipeline.running and pipeline.progress >= 100:
                await asyncio.sleep(2)
                break
    except Exception:
        pass
    finally:
        pipeline.on_progress = None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)