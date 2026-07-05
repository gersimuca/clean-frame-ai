import os
import io
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image

from config import settings
from database import db
from pipeline import pipeline, create_thumbnail
from models import PipelineConfig, StatsResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="PuraLens", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    uploaded = []
    for file in files:
        contents = await file.read()
        if len(contents) == 0:
            continue

        try:
            img = Image.open(io.BytesIO(contents))
            width, height = img.size
            thumb = create_thumbnail(contents, size=(400, 400))

            image_id = db.register_image(
                filename=file.filename,
                file_size=len(contents),
                image_bytes=contents,
                thumbnail_bytes=thumb,
                width=width,
                height=height,
            )
            uploaded.append({"id": image_id, "filename": file.filename})
        except Exception as e:
            image_id = db.register_image(
                filename=file.filename,
                file_size=len(contents),
                image_bytes=contents,
                thumbnail_bytes=b"",
                width=0,
                height=0,
            )
            db.update_status(image_id, "rejected", corrupt_reason=f"upload_parse_error: {e}")
            uploaded.append({"id": image_id, "filename": file.filename, "error": str(e)})

    return {"uploaded": uploaded, "total": len(uploaded)}


@app.post("/api/upload/url")
async def upload_from_url(url: str = Form(...)):
    import requests
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        contents = resp.content

        img = Image.open(io.BytesIO(contents))
        width, height = img.size
        thumb = create_thumbnail(contents, size=(400, 400))

        image_id = db.register_image(
            filename=Path(url).name or "from_url.jpg",
            file_size=len(contents),
            image_bytes=contents,
            thumbnail_bytes=thumb,
            width=width,
            height=height,
        )
        return {"id": image_id, "filename": Path(url).name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/pipeline/start")
async def start_pipeline(config: PipelineConfig):
    if pipeline.running:
        raise HTTPException(status_code=409, detail="Pipeline already running")

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
    return {"images": [_format_image(row) for row in rows], "total": total}


@app.get("/api/images/invalid")
async def get_all_invalid():
    rows = db.get_all_invalid()
    return {"images": [_format_image(row) for row in rows], "total": len(rows)}


@app.get("/api/images/{image_id}")
async def get_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    return _format_image(row, detailed=True)


@app.get("/api/images/{image_id}/full")
async def get_image_full(image_id: int):
    data = db.get_image_data(image_id, thumbnail=False)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type="image/jpeg")


@app.get("/api/images/{image_id}/thumb")
async def get_image_thumb(image_id: int):
    data = db.get_image_data(image_id, thumbnail=True)
    if data is None or len(data) == 0:
        data = db.get_image_data(image_id, thumbnail=False)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type="image/jpeg")


@app.post("/api/images/{image_id}/accept")
async def accept_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    db.update_status(image_id, "accepted")
    return {"status": "accepted"}


@app.post("/api/images/{image_id}/reject")
async def reject_image(image_id: int, reason: str = "manual"):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    db.update_status(image_id, "rejected", corrupt_reason=f"manual: {reason}")
    return {"status": "rejected"}


@app.post("/api/images/{image_id}/reprocess")
async def reprocess_image(image_id: int):
    db.reset_to_pending(image_id)
    return {"status": "pending"}


@app.delete("/api/images/{image_id}")
async def delete_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    with db._connect() as conn:
        conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
    return {"status": "deleted"}


@app.post("/api/clear")
async def clear_all():
    db.clear_all()
    return {"status": "cleared"}


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


def _format_image(row: dict, detailed: bool = False) -> dict:
    size_str = f"{row['file_size_bytes'] / (1024 * 1024):.1f} MB" if row.get('file_size_bytes') else "—"
    dim_str = f"{row['width']}x{row['height']}" if row.get('width') else "—"

    result = {
        "id": row["id"],
        "filename": row["filename"],
        "url": f"/api/images/{row['id']}/full",
        "thumbnailUrl": f"/api/images/{row['id']}/thumb",
        "status": row["status"],
        "score": row.get("relevance_score") or row.get("framing_score"),
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)