import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

from groq import Groq, RateLimitError

job_progress: dict[str, dict] = {}

OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _get_duration(file_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[-300:]}")
    return float(json.loads(result.stdout)["format"]["duration"])


def _split_audio(file_path: str, job_id: str) -> list[str]:
    chunk_dir = TEMP_DIR / f"{job_id}_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    duration = _get_duration(file_path)
    segment_sec = 600  # 10-minute chunks → ~2.4 MB each at 32kbps
    n = math.ceil(duration / segment_sec)

    chunks = []
    for i in range(n):
        out = str(chunk_dir / f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg",
            "-ss", str(i * segment_sec),
            "-i", file_path,
            "-t", str(segment_sec),
            "-ar", "16000",
            "-ac", "1",
            "-q:a", "2",
            out, "-y",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            raise RuntimeError(f"ffmpeg chunk {i} failed: {res.stderr[-300:]}")
        chunks.append(out)

    return chunks


def run_transcription(job_id: str, file_path: str) -> None:
    chunk_dir = TEMP_DIR / f"{job_id}_chunks"
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    try:
        job_progress[job_id] = {"status": "splitting", "percent": 2, "message": "Preparing audio..."}
        chunks = _split_audio(file_path, job_id)
        total = len(chunks)

        all_text: list[str] = []
        srt_lines: list[str] = []
        time_offset = 0.0
        srt_idx = 1

        for i, chunk_path in enumerate(chunks):
            pct = 5 + int((i / total) * 90)
            job_progress[job_id] = {
                "status": "transcribing",
                "percent": pct,
                "message": f"Transcribing part {i + 1} of {total}...",
            }

            chunk_duration = _get_duration(chunk_path)

            for attempt in range(3):
                try:
                    with open(chunk_path, "rb") as f:
                        response = client.audio.transcriptions.create(
                            file=(Path(chunk_path).name, f),
                            model="whisper-large-v3",
                            language="ta",
                            response_format="text",
                        )
                    break
                except RateLimitError:
                    if attempt == 2:
                        raise
                    time.sleep(60)

            text = response if isinstance(response, str) else getattr(response, "text", str(response))
            text = text.strip()
            all_text.append(text)

            if text:
                srt_lines.append(f"{srt_idx}")
                srt_lines.append(f"{_fmt_srt_time(time_offset)} --> {_fmt_srt_time(time_offset + chunk_duration)}")
                srt_lines.append(text)
                srt_lines.append("")
                srt_idx += 1

            time_offset += chunk_duration

            os.remove(chunk_path)
            if i < total - 1:
                time.sleep(1)

        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / f"{job_id}.txt").write_text("\n\n".join(all_text), encoding="utf-8")
        (OUTPUT_DIR / f"{job_id}.srt").write_text("\n".join(srt_lines), encoding="utf-8")

        job_progress[job_id] = {"status": "done", "percent": 100, "message": "Transcription complete!"}

    except Exception as exc:
        job_progress[job_id] = {"status": "error", "percent": 0, "message": str(exc)}
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass
        try:
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)
        except OSError:
            pass
