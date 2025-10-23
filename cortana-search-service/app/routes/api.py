from fastapi import APIRouter, Query, HTTPException
from app.services.data_service import (
    get_summary,
    list_videos,
    get_video,
    list_video_frames,
    search_ocr,
)

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/summary")
def summary():
    return get_summary()

@router.get("/videos")
def videos():
    return {"items": list_videos()}

@router.get("/videos/{video_id}")
def video(video_id: str):
    v = get_video(video_id)
    if not v:
        raise HTTPException(404, "not found")
    return v

@router.get("/videos/{video_id}/frames")
def video_frames(
    video_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    expires_in: int = Query(900, ge=60, le=86400),
):
    return list_video_frames(video_id, limit, offset, expires_in)

@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    expires_in: int = Query(900, ge=60, le=86400),
):
    return search_ocr(q, page, page_size, expires_in)
