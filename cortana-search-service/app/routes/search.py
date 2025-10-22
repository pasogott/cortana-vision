from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime
from app.config import settings

router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['now'] = datetime.now

DB_PATH = settings.database_url.replace("sqlite:///", "")


# -------------------------------
# Helpers
# -------------------------------
def query_db(query, params=()):
    """Generic DB query helper."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_videos():
    """Return all video IDs and filenames."""
    q = "SELECT id, filename FROM videos ORDER BY filename ASC;"
    return query_db(q)


def search_in_video(video_id: str, q: str, limit: int = 50):
    """Search OCR text inside a specific video."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    results = []

    try:
        cur.execute("""
            SELECT video_id, frame_path,
                   snippet(ocr_index, -1, '<mark>', '</mark>', '...', 10) AS snippet
            FROM ocr_index
            WHERE video_id = ? AND ocr_index MATCH ?
            LIMIT ?;
        """, (video_id, q, limit))
        results = cur.fetchall()
    except Exception as e:
        print(f"[SEARCH][FTS FAIL] {e}")
        # fallback LIKE if FTS missing or corrupt
        cur.execute("""
            SELECT video_id, frame_path, substr(ocr_text, 1, 250) AS snippet
            FROM ocr_frames
            WHERE video_id = ? AND lower(ocr_text) LIKE ?
            LIMIT ?;
        """, (video_id, f"%{q.lower()}%", limit))
        results = cur.fetchall()

    conn.close()
    return results


# -------------------------------
# Routes
# -------------------------------
@router.get("/", response_class=HTMLResponse)
def search_page(
    request: Request,
    video_id: str = Query("", description="Video ID to filter by"),
    q: str = Query("", description="Search text"),
):
    """Render search UI with dropdown + results."""
    videos = list_videos()
    results = []
    selected_video = None

    if video_id:
        selected_video = next((v for v in videos if v["id"] == video_id), None)
        if q:
            results = search_in_video(video_id, q)

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "videos": videos,
            "selected_video": selected_video,
            "video_id": video_id,
            "query": q,
            "results": results,
        },
    )


@router.get("/api", response_class=JSONResponse)
def api_search(video_id: str = Query(...), q: str = Query(...)):
    """Return JSON results for API consumers."""
    try:
        rows = search_in_video(video_id, q)
        return JSONResponse(content={
            "video_id": video_id,
            "query": q,
            "count": len(rows),
            "results": [dict(r) for r in rows]
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
