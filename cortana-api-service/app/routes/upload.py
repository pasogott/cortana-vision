from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from starlette.concurrency import run_in_threadpool
from app.utils.storage import save_upload
from app.utils.queue import publish_job
from app.utils.s3 import upload_to_s3
from app.database import SessionLocal
from app.models import Video
import os, uuid, time

router = APIRouter(prefix="/upload", tags=["upload"])

# -------------------------------------------------
# Background Pipeline
# -------------------------------------------------
def background_upload_pipeline(local_path: str, filename: str, video_id: str):
    """Runs in background: S3 upload → DB update → Redis publish → cleanup."""
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if not video:
            print(f"[UPLOAD][BG][ERR] Video not found: {video_id}")
            return

        # Update status → processing
        video.status = "processing"
        db.commit()
        print(f"[UPLOAD][BG] {video_id} → processing")

        # Upload to S3
        s3_key = f"videos/{video_id}/{filename}"
        s3_url = upload_to_s3(local_path, s3_key)
        video.path = s3_url
        db.commit()
        print(f"[UPLOAD][BG] S3 upload complete: {s3_url}")

        # Publish job to Redis (sampler stage)
        payload = {"video_id": video_id, "filename": filename}
        publish_job("make-samples-from-video", payload)
        print(f"[UPLOAD][BG] Job published → {payload}")

        # Update status → ready
        video.status = "ready"
        db.commit()
        print(f"[UPLOAD][BG] {video_id} → ready ✅")

    except Exception as e:
        db.rollback()
        print(f"[UPLOAD][BG][ERR] {e}")
        try:
            video.status = "failed"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                print(f"[UPLOAD][BG] Cleaned up {local_path}")
            except Exception as e:
                print(f"[UPLOAD][BG][WARN] Cleanup failed: {e}")


# -------------------------------------------------
# Upload Endpoint
# -------------------------------------------------
@router.post("/", status_code=202)
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Accept video, store locally, register DB entry, and queue background upload."""
    start = time.time()
    db = SessionLocal()
    try:
        # Save locally (off main thread)
        local_path = await run_in_threadpool(save_upload, file)
        size_mb = round(os.path.getsize(local_path) / (1024 * 1024), 2)

        # Create video entry (status = queued)
        video_id = str(uuid.uuid4())
        video = Video(id=video_id, filename=file.filename, status="queued")
        db.add(video)
        db.commit()

        # Queue background upload
        background_tasks.add_task(background_upload_pipeline, local_path, file.filename, video_id)

        elapsed = round(time.time() - start, 2)
        return {
            "status": "accepted",
            "message": "Video queued for background processing.",
            "video": {
                "id": video_id,
                "filename": file.filename,
                "size_mb": size_mb,
                "status": "queued",
                "elapsed_seconds": elapsed,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
