from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import sqlite3, re
from datetime import datetime
from app.config import settings

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['now'] = datetime.now

DB_PATH = settings.database_url.replace("sqlite:///", "")

# -------------------------------
# FTS Bootstrap (ensures table & triggers)
# -------------------------------
def ensure_fts_index():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index USING fts5(
            video_id, frame_path, ocr_text,
            content='ocr_frames', content_rowid='rowid'
        );

        CREATE TRIGGER IF NOT EXISTS ocr_ai AFTER INSERT ON ocr_frames BEGIN
            INSERT INTO ocr_index(rowid, video_id, frame_path, ocr_text)
            VALUES (new.rowid, new.video_id, new.frame_path, new.ocr_text);
        END;

        CREATE TRIGGER IF NOT EXISTS ocr_ad AFTER DELETE ON ocr_frames BEGIN
            DELETE FROM ocr_index WHERE rowid = old.rowid;
        END;

        CREATE TRIGGER IF NOT EXISTS ocr_au AFTER UPDATE ON ocr_frames BEGIN
            UPDATE ocr_index SET ocr_text = new.ocr_text WHERE rowid = old.rowid;
        END;
        """)
        conn.commit()
    except Exception as e:
        print(f"[SEARCH][FTS][WARN] could not ensure FTS index: {e}")
    finally:
        conn.close()

ensure_fts_index()

# -------------------------------
# Helpers
# -------------------------------
def s3_url_from_key(key: str) -> str:
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

# -------------------------------
# Summary & Progress
# -------------------------------
def get_summary():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM videos;")
    total_videos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM frames;")
    total_frames = cur.fetchone()[0]

    try:
        cur.execute("SELECT COUNT(*) FROM ocr_index;")
        indexed_frames = cur.fetchone()[0]
    except sqlite3.OperationalError as e:
        print(f"[SEARCH][WARN] FTS not ready: {e}")
        indexed_frames = 0

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
    out.sort(key=lambda x: (x["frame_number"] is None, x["frame_number"] or 0))
    return out

# -------------------------------
# Search (FTS + fallback)
# -------------------------------
def perform_search(q: str, page: int = 1, page_size: int = 12):
    offset = (page - 1) * page_size
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
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
        print(f"[SEARCH][FTS][WARN] {e}")

    if not results:
        cur.execute("""
            SELECT video_id, frame_path, substr(ocr_text, 1, 220) AS snippet
            FROM ocr_frames
            WHERE lower(ocr_text) LIKE ?
            LIMIT ? OFFSET ?;
        """, (f"%{q.lower()}%", page_size, offset))
        results = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM ocr_frames WHERE lower(ocr_text) LIKE ?;", (f"%{q.lower()}%",))
    total = cur.fetchone()[0]
    conn.close()

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
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "videos": videos,
        "query": "",
        "results": [],
        "page": 1,
        "page_size": 12,
        "total_pages": 0,
        "total": 0,
    })

@router.get("/dashboard/search", response_class=HTMLResponse)
def dashboard_search(request: Request,
                     q: str = Query(""),
                     page: int = Query(1, ge=1),
                     page_size: int = Query(12, ge=1, le=100)):
    stats = get_summary()
    videos = get_video_progress()
    results, total = perform_search(q, page, page_size) if q else ([], 0)
    total_pages = (total // page_size) + (1 if total % page_size else 0)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "videos": videos,
        "query": q,
        "results": results,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total": total,
    })

@router.get("/dashboard/video/{video_id}", response_class=HTMLResponse)
def video_detail(request: Request, video_id: str):
    stats = get_summary()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT v.id, v.filename,
               COUNT(f.id) AS total_frames,
               SUM(CASE WHEN f.greyscale_is_processed = 1 THEN 1 ELSE 0 END) AS processed_frames
        FROM videos v
        LEFT JOIN frames f ON v.id = f.video_id
        WHERE v.id = ?
        GROUP BY v.id, v.filename;
    """, (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video:
        return templates.TemplateResponse("video_detail.html", {
            "request": request,
            "video_id": video_id,
            "frames": [],
            "stats": stats,
            "video_info": None,
            "progress": 0,
        }, status_code=404)

    progress = round(
        100.0 * (video["processed_frames"] or 0) / video["total_frames"], 1
    ) if video["total_frames"] else 0
    frames = get_video_frames(video_id)

    return templates.TemplateResponse("video_detail.html", {
        "request": request,
        "stats": stats,
        "frames": frames,
        "video_id": video_id,
        "video_info": video,
        "progress": progress,
    })

@router.get("/dashboard/video/{video_id}/status", response_class=JSONResponse)
def video_status(video_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT v.id, v.filename,
               COUNT(f.id) AS total_frames,
               SUM(CASE WHEN f.greyscale_is_processed = 1 THEN 1 ELSE 0 END) AS processed_frames
        FROM videos v
        LEFT JOIN frames f ON v.id = f.video_id
        WHERE v.id = ?
        GROUP BY v.id, v.filename;
    """, (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video:
        return JSONResponse(content={"video_id": video_id, "status": "not_found"}, status_code=404)

    total = video["total_frames"] or 0
    processed = video["processed_frames"] or 0
    progress = round(100.0 * processed / total, 1) if total > 0 else 0

    status = "ready" if progress == 100 else "processing" if processed > 0 else "queued"

    return JSONResponse(content={
        "video_id": video_id,
        "filename": video["filename"],
        "progress": progress,
        "processed_frames": processed,
        "total_frames": total,
        "status": status,
    })
