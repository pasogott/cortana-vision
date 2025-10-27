import re
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List
from app.config import settings
from app.utils.s3_utils import presign_get_url

DB_PATH = settings.database_url.replace("sqlite:///", "")

# ---------------------------------------------------------
# DB Connection Helpers
# ---------------------------------------------------------
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def _frame_no(key: str):
    m = re.search(r"frame_(\d+)\.(jpg|png|jpeg)$", key)
    return int(m.group(1)) if m else None

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------
def get_summary() -> Dict[str, Any]:
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM videos")
    total_videos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM frames")
    total_frames = cur.fetchone()[0]
    try:
        cur.execute("SELECT COUNT(*) FROM ocr_index")
        indexed_frames = cur.fetchone()[0]
    except sqlite3.OperationalError:
        indexed_frames = 0
    con.close()
    return {
        "total_videos": int(total_videos or 0),
        "total_frames": int(total_frames or 0),
        "indexed_frames": int(indexed_frames or 0),
        "ts": datetime.utcnow().isoformat()
    }

# ---------------------------------------------------------
# Videos
# ---------------------------------------------------------
def list_videos() -> List[Dict[str, Any]]:
    q = """
    WITH base AS (
      SELECT v.id, v.filename, v.path, COUNT(f.id) AS total_frames
      FROM videos v
      LEFT JOIN frames f ON v.id = f.video_id
      GROUP BY v.id, v.filename, v.path
    )
    SELECT
      b.id, b.filename, b.path,
      b.total_frames,
      (SELECT COUNT(*) FROM ocr_frames ofr WHERE ofr.video_id = b.id) AS ocr_frames
    FROM base b
    ORDER BY b.id DESC
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(q)
    rows = cur.fetchall()
    con.close()

    out = []
    for r in rows:
        total = int(r["total_frames"] or 0)
        ocr = int(r["ocr_frames"] or 0)
        prog = round(100.0 * ocr / total, 1) if total else 0.0
        status = "ready" if total and ocr >= total else ("processing" if ocr > 0 else "queued")
        out.append({
            "id": r["id"],
            "filename": r["filename"],
            "video_url": r["path"],
            "total_frames": total,
            "processed_frames": ocr,
            "progress": prog,
            "status": status
        })
    return out

# ---------------------------------------------------------
# Video Details
# ---------------------------------------------------------
def get_video(video_id: str) -> Dict[str, Any] | None:
    q = """
    WITH base AS (
      SELECT v.id, v.filename, v.path, v.created_at, v.is_processed_datetime_utc, v.status,
             COUNT(f.id) AS total_frames
      FROM videos v
      LEFT JOIN frames f ON v.id = f.video_id
      WHERE v.id = ?
      GROUP BY v.id, v.filename, v.path, v.created_at, v.is_processed_datetime_utc, v.status
    )
    SELECT
      b.*,
      (SELECT COUNT(*) FROM ocr_frames ofr WHERE ofr.video_id = b.id) AS ocr_frames
    FROM base b
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(q, (video_id,))
    r = cur.fetchone()
    con.close()

    if not r:
        return None

    total = int(r["total_frames"] or 0)
    ocr = int(r["ocr_frames"] or 0)
    prog = round(100.0 * ocr / total, 1) if total else 0.0
    status = r["status"] or ("ready" if total and ocr >= total else ("processing" if ocr > 0 else "queued"))
    return {
        "id": r["id"],
        "filename": r["filename"],
        "video_url": r["path"],
        "created_at": r["created_at"],
        "processed_at": r["is_processed_datetime_utc"],
        "total_frames": total,
        "processed_frames": ocr,
        "progress": prog,
        "status": status
    }

# ---------------------------------------------------------
# Frames of a Video
# ---------------------------------------------------------
def list_video_frames(video_id: str, limit: int, offset: int, expires_in: int) -> Dict[str, Any]:
    q = """
    SELECT frame_path, ocr_text
    FROM ocr_frames
    WHERE video_id = ?
    ORDER BY frame_path ASC
    LIMIT ? OFFSET ?
    """
    con = _conn()
    cur = con.cursor()
    cur.execute(q, (video_id, limit, offset))
    rows = cur.fetchall()
    con.close()

    items = []
    for r in rows:
        key = r["frame_path"]
        items.append({
            "frame_number": _frame_no(key),
            "key": key,
            "url": presign_get_url(key, expires_in),
            "expires_in": expires_in,
            "ocr_text": (r["ocr_text"] or "")[:1000]
        })
    return {"items": items, "limit": limit, "offset": offset}

# ---------------------------------------------------------
# OCR Search
# ---------------------------------------------------------
def search_ocr(q: str, page: int, page_size: int, expires_in: int) -> Dict[str, Any]:
    off = (page - 1) * page_size
    con = _conn()
    cur = con.cursor()

    # Try FTS (Fast full-text search)
    try:
        cur.execute("""
            SELECT f.video_id, f.frame_path, f.ocr_text,
                   snippet(ocr_index, -1, '<mark>', '</mark>', '...', 10) AS snippet
            FROM ocr_frames f
            LEFT JOIN ocr_index ON ocr_index.frame_path = f.frame_path
            WHERE ocr_index MATCH ?
            LIMIT ? OFFSET ?
        """, (q, page_size, off))
        results = cur.fetchall()
    except Exception:
        results = []

    # Fallback to LIKE search
    if not results:
        cur.execute("""
            SELECT video_id, frame_path, ocr_text, substr(ocr_text, 1, 220) AS snippet
            FROM ocr_frames
            WHERE lower(ocr_text) LIKE ?
            LIMIT ? OFFSET ?
        """, (f"%{q.lower()}%", page_size, off))
        results = cur.fetchall()

    # Count total matches
    cur.execute("SELECT COUNT(*) FROM ocr_frames WHERE lower(ocr_text) LIKE ?", (f"%{q.lower()}%",))
    total = int(cur.fetchone()[0] or 0)

    items = []
    for r in results:
        key = r["frame_path"]
        items.append({
            "video_id": r["video_id"],
            "key": key,
            "filename": key.split("/")[-1],
            "frame_number": _frame_no(key),
            "snippet": r["snippet"] or "",
            "ocr_text": (r["ocr_text"] or "")[:8000],  # ✅ include full text safely trimmed
            "url": presign_get_url(key, expires_in),
            "expires_in": expires_in
        })

    con.close()

    total_pages = (total // page_size) + (1 if total % page_size else 0)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }
