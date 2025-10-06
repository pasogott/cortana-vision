from fastapi import APIRouter, Query
from app.database import SessionLocal
from app.models import Video, Frame
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/db")
def debug_db():
    db = SessionLocal()
    videos = db.query(Video).all()
    frames = db.query(Frame).all()
    out = []
    for v in videos:
        frame_count = db.query(Frame).filter(Frame.video_id == v.id).count()
        out.append({
            "video_id": str(v.id),
            "filename": v.filename,
            "frames": frame_count
        })
    db.close()
    return {"status": "ok", "videos": out, "total_frames": len(frames)}


@router.post("/reset-ocr")
def reset_ocr(video_id: str = Query(..., description="UUID of the video to reset")):
    """
    ⚙️ Debug endpoint — resets OCR results for a given video.
    Clears all ocr_content and sets greyscale_is_processed=False.
    """
    try:
        db = SessionLocal()
        video = db.query(Video).filter_by(id=video_id).first()
        if not video:
            return JSONResponse(
                {"status": "error", "detail": "Video not found"}, status_code=404
            )

        frames = db.query(Frame).filter(Frame.video_id == video_id).all()
        if not frames:
            return JSONResponse(
                {"status": "error", "detail": "No frames found for this video"},
                status_code=404,
            )

        reset_count = 0
        for f in frames:
            f.ocr_content = None
            f.greyscale_is_processed = False
            reset_count += 1

        video.is_processed = False
        db.commit()

        return {
            "status": "success",
            "video_id": video_id,
            "frames_reset": reset_count,
            "message": "OCR content cleared and flags reset.",
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
    finally:
        db.close()
