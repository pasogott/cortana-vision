from fastapi import APIRouter, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import os, subprocess, cv2, asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Frame, Video
from app.utils.storage import upload_to_s3

router = APIRouter(prefix="/extract", tags=["extract"])


# ---------- DB Session ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Background Scene Extraction ----------
async def run_extract_task(filename: str, threshold: float = 0.08):
    """Background scene extraction task: FFmpeg + S3 + DB sync."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        base_name = os.path.splitext(filename)[0]
        upload_path = f"uploads/{filename}"
        output_dir = f"keyframes/{base_name}"
        os.makedirs(output_dir, exist_ok=True)
        log_path = os.path.join(output_dir, "scene_log.txt")

        # ✅ Ensure video record exists or create new
        video = db.query(Video).filter_by(filename=filename).first()
        if not video:
            video = Video(
                filename=filename,
                path=upload_path,
                is_processed=False,
                is_processed_datetime_utc=None
            )
            db.add(video)
            db.commit()
            db.refresh(video)

        print(f"[EXTRACT] 🚀 Starting scene extraction for '{filename}'...")

        # ---------- Run FFmpeg (non-blocking) ----------
        cmd = [
            "ffmpeg", "-i", upload_path,
            "-vf", f"select=gt(scene\\,{threshold}),showinfo",
            "-vsync", "vfr",
            os.path.join(output_dir, "frame_%04d.jpg"),
        ]
        with open(log_path, "w") as log_file:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=log_file
            )
            await process.wait()

        # ---------- Deduplicate via Histogram ----------
        frames = sorted([f for f in os.listdir(output_dir) if f.endswith(".jpg")])
        unique_frames = []
        prev_hist = None
        for f_name in frames:
            path = os.path.join(output_dir, f_name)
            img = cv2.imread(path)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if diff < 0.97:
                    unique_frames.append(f_name)
                    prev_hist = hist
            else:
                unique_frames.append(f_name)
                prev_hist = hist

        print(f"[EXTRACT] 🧠 {len(unique_frames)} unique keyframes kept (from {len(frames)}).")

        # ---------- Upload to S3 and update DB ----------
        uploaded = 0
        for idx, f_name in enumerate(unique_frames):
            try:
                local_frame = os.path.join(output_dir, f_name)
                s3_key = f"videos/{base_name}/frames/{f_name}"
                s3_url = upload_to_s3(local_frame, s3_key)

                frame_record = Frame(
                    video_id=video.id,
                    path=s3_url,
                    frame_number=idx + 1,
                    greyscale_is_processed=False,
                    frame_time=float(idx)
                )
                db.add(frame_record)
                uploaded += 1

                if uploaded % 25 == 0:
                    print(f"[EXTRACT] ✅ Uploaded {uploaded}/{len(unique_frames)} frames")
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"[EXTRACT] ⚠️ Upload error on {f_name}: {e}")
                continue

        # ✅ Finalize
        video.is_processed = True
        video.is_processed_datetime_utc = datetime.utcnow()
        db.commit()

        print(f"[EXTRACT] 🏁 Done. Uploaded {uploaded} frames for '{filename}'")

    except Exception as e:
        print(f"[EXTRACT] ❌ Error in extraction: {e}")
    finally:
        db.close()


# ---------- Trigger Extraction ----------
@router.post("/")
async def extract_scenes(
    filename: str = Query(..., description="Uploaded video filename"),
    threshold: float = 0.08,
    background_tasks: BackgroundTasks = None,
):
    """Triggers background video scene extraction."""
    try:
        background_tasks.add_task(asyncio.run, run_extract_task(filename, threshold))
        return {
            "status": "queued",
            "filename": filename,
            "threshold": threshold,
            "message": (
                f"Scene extraction started for '{filename}'. "
                "You can check /extract/status/{filename} for progress."
            )
        }
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# ---------- Progress Endpoint ----------
@router.get("/status/{filename}")
def extract_status(filename: str, db: Session = Depends(get_db)):
    """Check extraction progress for a video by filename."""
    try:
        video = db.query(Video).filter_by(filename=filename).first()
        if not video:
            return JSONResponse(
                {"status": "error", "detail": "Video not found"},
                status_code=404,
            )

        total_frames = db.query(Frame).filter_by(video_id=video.id).count()
        processed_frames = (
            db.query(Frame)
            .filter_by(video_id=video.id, greyscale_is_processed=True)
            .count()
        )

        progress = round((processed_frames / total_frames) * 100, 2) if total_frames else 0

        return {
            "status": "success",
            "filename": filename,
            "video_id": video.id,
            "frames_extracted": total_frames,
            "frames_processed": processed_frames,
            "progress_percent": progress,
            "is_completed": video.is_processed,
            "is_ready_for_ocr": total_frames > 0,
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
