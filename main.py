from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import os
import subprocess

app = FastAPI(title="Snapshot Sandbox")

UPLOAD_DIR = "uploads"
KEYFRAME_DIR = "keyframes"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(KEYFRAME_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"status": "ok", "message": "snapshot-sandbox server running"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file"""
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return JSONResponse(
            {"status": "success", "filename": file.filename, "path": file_path}
        )
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@app.post("/extract-scenes")
async def extract_scenes(filename: str, threshold: float = 0.2, background_tasks: BackgroundTasks = None):
    """
    Extract key frames from uploaded video based on scene changes.
    threshold: 0.1–0.5 (lower = more sensitive, higher = fewer frames)
    """
    try:
        input_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(input_path):
            return JSONResponse({"error": "file not found"}, status_code=404)

        # Create output folder per video
        output_dir = os.path.join(KEYFRAME_DIR, os.path.splitext(filename)[0])
        os.makedirs(output_dir, exist_ok=True)

        # ffmpeg scene-detect command
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=gt(scene\\,{threshold}),showinfo",
            "-vsync", "vfr",
            os.path.join(output_dir, "frame_%04d.jpg"),
        ]

        # Run in background so API stays fast
        def run_ffmpeg():
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        background_tasks.add_task(run_ffmpeg)

        return {
            "status": "processing",
            "message": "scene extraction started",
            "threshold": threshold,
            "output_dir": output_dir
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
