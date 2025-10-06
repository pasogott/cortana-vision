from fastapi import APIRouter, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Frame, Video
from app.utils.storage import s3, S3_BUCKET
from botocore.exceptions import ClientError

import cv2
import numpy as np
import pytesseract
import tempfile
import re
import os
import asyncio

router = APIRouter(prefix="/ocr", tags=["ocr"])


# ---------- DB Session ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Background OCR Task ----------
async def run_ocr_task(video_id: str):
    """Background OCR task that downloads frames from S3, runs OCR, and updates DB."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        video = db.query(Video).filter_by(id=video_id).first()
        if not video:
            print(f"[OCR] ❌ Video {video_id} not found.")
            return

        frames = (
            db.query(Frame)
            .filter_by(video_id=video_id, greyscale_is_processed=False)
            .all()
        )
        if not frames:
            print(f"[OCR] ⚠️ No unprocessed frames for {video.filename}")
            return

        config = (
            "--oem 3 --psm 6 "
            "-c preserve_interword_spaces=1 "
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@._-"
        )

        total = len(frames)
        processed = 0
        print(f"[OCR] 🚀 Starting OCR for {video.filename} ({total} frames)...")

        for frame in frames:
            try:
                # --- Download frame from Hetzner S3 ---
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    s3_key = frame.path.split(f"{S3_BUCKET}/")[-1]
                    s3.download_file(S3_BUCKET, s3_key, tmp.name)
                    local_path = tmp.name

                img = cv2.imread(local_path)
                os.remove(local_path)
                if img is None:
                    continue

                # --- Preprocess ---
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                if np.mean(gray) < 127:
                    gray = cv2.bitwise_not(gray)

                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray = clahe.apply(gray)
                gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
                sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                gray = cv2.filter2D(gray, -1, sharpen_kernel)
                bw = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 17, 8
                )

                # --- Dual-pass OCR ---
                try:
                    text_gray = pytesseract.image_to_string(bw, lang="deu+eng", config=config)
                except pytesseract.TesseractError:
                    text_gray = pytesseract.image_to_string(bw, lang="eng", config=config)
                text_color = pytesseract.image_to_string(img, lang="eng", config=config)

                merged_text = (text_gray + " " + text_color).strip()
                merged_text = re.sub(r"\s+", " ", merged_text)

                frame.ocr_content = merged_text
                frame.greyscale_is_processed = True
                processed += 1

                if processed % 25 == 0 or processed == total:
                    print(f"[OCR] ✅ {processed}/{total} frames processed")

                # Yield control so FastAPI can handle other tasks
                await asyncio.sleep(0.001)

            except ClientError as e:
                print(f"[OCR] ⚠️ S3 error on frame {frame.frame_number}: {e}")
            except Exception as e:
                print(f"[OCR] ⚠️ OCR error on frame {frame.frame_number}: {e}")

        video.is_processed = True
        db.commit()
        print(f"[OCR] 🏁 OCR finished for {video.filename} ({processed}/{total})")

    finally:
        db.close()


# ---------- Start Background OCR ----------
@router.post("/")
async def ocr_process(
    video_id: str = Query(..., description="Video UUID"),
    background_tasks: BackgroundTasks = None,
):
    """Starts OCR in background and returns immediately."""
    try:
        # Schedule the OCR coroutine
        background_tasks.add_task(asyncio.run, run_ocr_task(video_id))
        return {
            "status": "queued",
            "video_id": video_id,
            "message": "OCR job started in background. Use /ocr/status/{video_id} to monitor progress."
        }
    except Exception as e:
        return JSONResponse(
            {"status": "error", "detail": f"Failed to queue OCR task: {str(e)}"},
            status_code=500
        )


# ---------- OCR Status Endpoint ----------
@router.get("/status/{video_id}")
def ocr_status(video_id: str, db: Session = Depends(get_db)):
    """Check OCR progress for a given video."""
    try:
        video = db.query(Video).filter_by(id=video_id).first()
        if not video:
            return JSONResponse(
                {"status": "error", "detail": "Video not found"},
                status_code=404,
            )

        total_frames = db.query(Frame).filter_by(video_id=video_id).count()
        processed_frames = (
            db.query(Frame)
            .filter_by(video_id=video_id, greyscale_is_processed=True)
            .count()
        )

        progress = round((processed_frames / total_frames) * 100, 2) if total_frames else 0

        return {
            "status": "success",
            "video_id": video_id,
            "video_name": video.filename,
            "processed_frames": processed_frames,
            "total_frames": total_frames,
            "progress_percent": progress,
            "is_completed": processed_frames == total_frames,
        }

    except Exception as e:
        return JSONResponse(
            {"status": "error", "detail": str(e)},
            status_code=500,
        )
