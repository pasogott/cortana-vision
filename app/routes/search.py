from fastapi import APIRouter, Query, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from difflib import SequenceMatcher
import re
from app.database import SessionLocal
from app.models import Frame

router = APIRouter(prefix="/search", tags=["search"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def search_text(
    q: str = Query(..., description="Search query text"),
    video_id: str = Query(..., description="Video UUID"),
    db: Session = Depends(get_db),
):
    """Search OCR text (case-insensitive, fuzzy match for usernames/handles)."""
    try:
        frames = db.query(Frame).filter(Frame.video_id == video_id).all()
        if not frames:
            return JSONResponse({"status": "error", "detail": "No OCR data found"}, status_code=404)

        query = q.lower().strip()
        norm_query = re.sub(r"[^a-z0-9@._-]", "", query)

        matches = []
        for f in frames:
            if not f.ocr_content:
                continue
            text = f.ocr_content.lower()
            norm_text = re.sub(r"[^a-z0-9@._-]", "", text)
            if query in text or norm_query in norm_text:
                matches.append(f)
            else:
                ratio = SequenceMatcher(None, norm_query, norm_text).ratio()
                if ratio > 0.7:
                    matches.append(f)

        result = [{
            "frame_number": f.frame_number,
            "frame_time": f.frame_time,
            "snippet": f.ocr_content[:200],
            "s3_url": f.path
        } for f in matches[:10]]

        return {"status": "success", "query": q, "matches_found": len(result), "matches": result}

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
