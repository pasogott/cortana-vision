from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3, re
from app.config import settings

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")

DB_PATH = settings.database_url.replace("sqlite:///", "")

# -------------------------------
# Helpers
# -------------------------------
def s3_url_from_key(key: str) -> str:
    """Convert an S3 object key to a public URL."""
    base = settings.s3_url.rstrip("/")
    bucket = settings.s3_bucket
    return f"{base}/{bucket}/{key.lstrip('/')}"

def parse_frame_number_from_key(key: str) -> int | None:
    m = re.search(r"frame_(\d+)\.(jpg|png|jpeg)$", key)
    return int(m.group(1)) if m else None

def query_db(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_summary():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM videos;")
    total_videos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM frames;")
    total_frames = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ocr_index;")
    indexed_frames = cur.fetchone()[0]
    conn.close()
    return {
        "total_videos": total_videos,
        "total_frames": total_frames,
        "indexed_frames": indexed_frames,
    }

def get_video_progress():
    q = """
    SELECT
        v.id AS video_id,
        v.filename,
        COUNT(f.id) AS total_frames,
        SUM(CASE WHEN f.greyscale_is_processed = 1 THEN 1 ELSE 0 END) AS processed_frames,
        ROUND(100.0 * SUM(CASE WHEN f.greyscale_is_processed = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(f.id),0), 1) AS progress
    FROM videos v
    LEFT JOIN frames f ON v.id = f.video_id
    GROUP BY v.id, v.filename
    ORDER BY v.filename ASC;
    """
    return query_db(q)

def get_video_frames(video_id: str):
    """
    Show frames using OCR records (they reliably store S3 keys).
    """
    rows = query_db("""
        SELECT frame_path, ocr_text
        FROM ocr_frames
        WHERE video_id = ?
        ORDER BY frame_path ASC;
    """, (video_id,))
    out = []
    for r in rows:
        key = r["frame_path"]
        out.append({
            "frame_number": parse_frame_number_from_key(key),
            "frame_url": s3_url_from_key(key),
            "ocr_text": r["ocr_text"] or "",
        })
    # sort by parsed number if available
    out.sort(key=lambda x: (x["frame_number"] is None, x["frame_number"] or 0))
    return out

# -------------------------------
# Search (FTS + LIKE fallback)
# -------------------------------
def perform_search(q: str, page: int = 1, page_size: int = 12):
    offset = (page - 1) * page_size
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Try FTS first
    results = []
    try:
        cur.execute("""
            SELECT video_id, frame_path,
                   snippet(ocr_index, -1, '<mark>', '</mark>', '...', 10) AS snippet
            FROM ocr_index
            WHERE ocr_index MATCH ?
            LIMIT ? OFFSET ?;
        """, (q, page_size, offset))
        results = cur.fetchall()
    except Exception as e:
        print(f"[SEARCH][FTS] {e}")

    # Fallback LIKE if FTS empty/fails
    if not results:
        cur.execute("""
            SELECT video_id, frame_path, substr(ocr_text, 1, 220) AS snippet
            FROM ocr_frames
            WHERE lower(ocr_text) LIKE ?
            LIMIT ? OFFSET ?;
        """, (f"%{q.lower()}%", page_size, offset))
        results = cur.fetchall()

    # total (LIKE is a superset for pagination)
    cur.execute("SELECT COUNT(*) FROM ocr_frames WHERE lower(ocr_text) LIKE ?;", (f"%{q.lower()}%",))
    total = cur.fetchone()[0]

    conn.close()

    # decorate with proper URLs + filename
    decorated = []
    for r in results:
        key = r["frame_path"]
        decorated.append({
            "video_id": r["video_id"],
            "frame_path": key,
            "frame_url": s3_url_from_key(key),
            "filename": key.split("/")[-1],
            "snippet": r["snippet"] or "",
        })
    return decorated, total

# -------------------------------
# Routes
# -------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    stats = get_summary()
    videos = get_video_progress()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "videos": videos,
            "query": "",
            "results": [],
            "page": 1,
            "page_size": 12,
            "total_pages": 0,
            "total": 0,
        },
    )

@router.get("/dashboard/search", response_class=HTMLResponse)
def dashboard_search(request: Request,
                     q: str = Query(""),
                     page: int = Query(1, ge=1),
                     page_size: int = Query(12, ge=1, le=100)):
    stats = get_summary()
    videos = get_video_progress()

    results, total = perform_search(q, page, page_size) if q else ([], 0)
    total_pages = (total // page_size) + (1 if total % page_size else 0)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "videos": videos,
            "query": q,
            "results": results,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total": total,
        },
    )

@router.get("/dashboard/video/{video_id}", response_class=HTMLResponse)
def video_detail(request: Request, video_id: str):
    stats = get_summary()
    frames = get_video_frames(video_id)
    return templates.TemplateResponse(
        "video_detail.html",
        {"request": request, "stats": stats, "frames": frames, "video_id": video_id},
    )
