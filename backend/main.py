import io
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image

from config import settings
from database import db, REASON_COLUMNS
from pipeline import pipeline, create_thumbnail
from models import PipelineConfig, StatsResponse
from serializers import format_image_row, format_stats


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
        # requests.get is blocking I/O; running it directly here would freeze
        # the whole server (including the SSE stream) for up to 30s.
        resp = await asyncio.to_thread(requests.get, url, timeout=30)
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


@app.get("/api/pipeline/stream")
async def pipeline_stream(request: Request):
    """Server-Sent Events stream of pipeline progress. Replaces the old
    /ws/pipeline WebSocket, which only supported a single listener at a time
    and offered no way for a newly-opened tab to learn the current state."""
    queue = pipeline.subscribe()

    async def event_generator():
        try:
            # Send current state immediately so a client that connects mid-run
            # (or reconnects) doesn't have to wait for the next event.
            yield _sse_event(pipeline.snapshot())
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield _sse_event(event)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            pipeline.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(**format_stats(db.get_stats()))


@app.get("/api/images")
async def get_images(status: str, limit: int = 100, offset: int = 0):
    rows = db.get_by_status(status, limit=limit, offset=offset)
    total = db.count_by_status(status)
    return {"images": [format_image_row(row) for row in rows], "total": total}


@app.get("/api/images/by-reason/{reason_type}")
async def get_images_by_reason(reason_type: str, limit: int = 200, offset: int = 0):
    """Images rejected for a specific reason: corrupt / irrelevant / bad-framing.
    These are NOT `status` values (status is only pending/accepted/rejected/error),
    so this is a separate lookup from /api/images?status=..."""
    if reason_type not in REASON_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Unknown reason type: {reason_type}")
    rows = db.get_by_reason(reason_type, limit=limit, offset=offset)
    total = db.count_by_reason(reason_type)
    return {"images": [format_image_row(row) for row in rows], "total": total}


@app.get("/api/images/invalid")
async def get_all_invalid():
    rows = db.get_all_invalid()
    return {"images": [format_image_row(row) for row in rows], "total": len(rows)}


@app.get("/api/images/{image_id}")
async def get_image(image_id: int):
    row = db.get_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    return format_image_row(row, detailed=True)


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
    db.delete_image(image_id)
    return {"status": "deleted"}


@app.post("/api/clear")
async def clear_all():
    db.clear_all()
    return {"status": "cleared"}


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
