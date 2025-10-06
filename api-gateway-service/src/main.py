from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
import shutil
import os
import subprocess
import cv2
import pytesseract
import json

app = FastAPI(title="Snapshot Sandbox")

UPLOAD_DIR = "uploads"
KEYFRAME_DIR = "keyframes"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(KEYFRAME_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"status": "ok", "message": "snapshot-sandbox server running"}


# --------------------------------------------------
# 1️⃣ Upload video
# --------------------------------------------------
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


# --------------------------------------------------
# 2️⃣ Extract scenes + timestamps
# --------------------------------------------------
@app.post("/extract-scenes")
async def extract_scenes(filename: str, threshold: float = 0.08):
    """
    Extract key frames from uploaded video based on scene changes
    and record timestamps for each frame.
    """
    try:
        input_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(input_path):
            return JSONResponse({"error": "file not found"}, status_code=404)

        base_name = os.path.splitext(filename)[0]
        output_dir = os.path.join(KEYFRAME_DIR, base_name)
        os.makedirs(output_dir, exist_ok=True)

        # Temporary log file for ffmpeg output
        log_path = os.path.join(output_dir, "scene_log.txt")

        # ffmpeg scene-detect command with showinfo for timestamps
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"select=gt(scene\\,{threshold}),showinfo",
            "-vsync", "vfr",
            os.path.join(output_dir, "frame_%04d.jpg"),
        ]

        # Run ffmpeg and log scene timestamps
        with open(log_path, "w") as log_file:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log_file)

        # Parse timestamps from ffmpeg log
        timestamps = []
        with open(log_path, "r") as f:
            for line in f:
                if "showinfo" in line and "pts_time:" in line:
                    parts = line.split("pts_time:")
                    if len(parts) > 1:
                        try:
                            ts = float(parts[1].split()[0])
                            timestamps.append(ts)
                        except ValueError:
                            continue

        # Match frames to timestamps
        frame_files = sorted(
            [f for f in os.listdir(output_dir) if f.lower().endswith((".jpg", ".png"))]
        )
        index_data = [
            {"frame": frame, "timestamp": ts}
            for frame, ts in zip(frame_files, timestamps)
        ]

        # Save scene index JSON
        index_path = os.path.join(output_dir, "scene_index.json")
        with open(index_path, "w") as f:
            json.dump(index_data, f, indent=2)

        return {
            "status": "success",
            "frames_extracted": len(frame_files),
            "index_json": index_path,
            "threshold": threshold,
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# --------------------------------------------------
# 3️⃣ OCR extraction (OpenCV + PyTesseract)
# --------------------------------------------------
@app.post("/ocr-extract")
async def ocr_extract(filename: str):
    """
    Run OCR on extracted keyframes for a given video.
    Produces a JSON index: [ {frame, timestamp, text}, ... ]
    """
    try:
        base_name = os.path.splitext(filename)[0]
        frames_dir = os.path.join(KEYFRAME_DIR, base_name)
        if not os.path.exists(frames_dir):
            return JSONResponse({"error": "no keyframes found"}, status_code=404)

        # Load timestamps if available
        index_path = os.path.join(frames_dir, "scene_index.json")
        index_data = []
        if os.path.exists(index_path):
            with open(index_path) as f:
                index_data = json.load(f)

        result = []

        frame_files = sorted(
            [f for f in os.listdir(frames_dir) if f.lower().endswith((".jpg", ".png"))]
        )

        for frame_name in frame_files:
            frame_path = os.path.join(frames_dir, frame_name)
            img = cv2.imread(frame_path)
            if img is None:
                continue

            # --- Preprocess with OpenCV ---
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            thresh = cv2.adaptiveThreshold(
                filtered,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2,
            )

            # --- OCR with Tesseract ---
            text = pytesseract.image_to_string(thresh, lang="eng").strip()

            # Match timestamp from scene_index.json
            timestamp = None
            for item in index_data:
                if item["frame"] == frame_name:
                    timestamp = item["timestamp"]
                    break

            result.append(
                {"frame": frame_name, "timestamp": timestamp, "text": text}
            )

        # Save OCR results
        output_path = os.path.join(frames_dir, "ocr_index.json")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        return {
            "status": "success",
            "frames_processed": len(result),
            "output_json": output_path,
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# --------------------------------------------------
# 4️⃣ Search text across OCR results
# --------------------------------------------------
@app.get("/search")
def search_text(filename: str, q: str = Query(..., description="Search query text")):
    """
    Search for a word or phrase in the OCR results.
    Returns matching frames and timestamps.
    """
    try:
        base_name = os.path.splitext(filename)[0]
        frames_dir = os.path.join(KEYFRAME_DIR, base_name)
        ocr_path = os.path.join(frames_dir, "ocr_index.json")

        if not os.path.exists(ocr_path):
            return JSONResponse({"error": "OCR results not found"}, status_code=404)

        with open(ocr_path) as f:
            ocr_data = json.load(f)

        query = q.lower().strip()
        matches = [
            {
                "frame": item["frame"],
                "timestamp": item["timestamp"],
                "snippet": item["text"],
            }
            for item in ocr_data
            if query in item["text"].lower()
        ]

        return {
            "status": "success",
            "query": q,
            "matches_found": len(matches),
            "matches": matches,
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
