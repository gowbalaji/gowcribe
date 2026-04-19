import asyncio
import json
import os
import uuid
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from auth import get_current_user, router as auth_router
from transcribe import OUTPUT_DIR, TEMP_DIR, job_progress, run_transcription

load_dotenv()

app = FastAPI(title="Gowcribe")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")

TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_BYTES = 640 * 1024 * 1024  # 640 MB safety margin
ALLOWED_SUFFIXES = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".webm", ".mpeg", ".aac"}


@app.post("/api/transcribe")
async def start_transcription(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: str = Depends(get_current_user),
):
    suffix = Path(file.filename or "audio.mp3").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported format. Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}")

    job_id = str(uuid.uuid4())
    file_path = TEMP_DIR / f"{job_id}{suffix}"
    size = 0
    too_large = False

    async with aiofiles.open(file_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                too_large = True
                break
            await out.write(chunk)

    if too_large:
        file_path.unlink(missing_ok=True)
        raise HTTPException(413, "File exceeds 600 MB limit")

    job_progress[job_id] = {"status": "queued", "percent": 0, "message": "Queued..."}
    background_tasks.add_task(run_transcription, job_id, str(file_path))
    return {"job_id": job_id}


@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: str, user: str = Depends(get_current_user)):
    async def generator():
        for _ in range(7200):  # max 1-hour poll window
            data = job_progress.get(
                job_id, {"status": "queued", "percent": 0, "message": "Waiting..."}
            )
            yield {"data": json.dumps(data)}
            if data.get("status") in ("done", "error"):
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(generator())


@app.get("/api/download/{job_id}")
async def download_file(
    job_id: str,
    fmt: str = "txt",
    user: str = Depends(get_current_user),
):
    if fmt not in ("txt", "srt"):
        raise HTTPException(400, "fmt must be txt or srt")
    path = OUTPUT_DIR / f"{job_id}.{fmt}"
    if not path.exists():
        raise HTTPException(404, "File not ready yet")
    return FileResponse(path, filename=f"gowcribe_{job_id[:8]}.{fmt}")


_frontend = Path("frontend/dist")
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="spa")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
