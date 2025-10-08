from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import sqlite3, os
from app.config import settings

router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory="app/templates")

DB_PATH = settings.database_url.replace("sqlite:///", "")

@router.get("/", response_class=HTMLResponse)
def search_page(request: Request, q: str = Query("", description="Search text")):
    """Serve search UI with optional query results."""
    results = []
    if q:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT video_id, frame_path,
                    snippet(ocr_index, 2, '<mark>', '</mark>', '...', 10) AS snippet
                FROM ocr_index
                WHERE ocr_index MATCH ?
                LIMIT 50;
            """, (q,))
            results = cur.fetchall()
            conn.close()
        except Exception as e:
            print(f"[SEARCH][ERR] Query failed → {e}")
    return templates.TemplateResponse("search.html", {"request": request, "query": q, "results": results})

@router.get("/api", response_class=JSONResponse)
def api_search(q: str = Query(..., description="Search text")):
    """JSON search endpoint."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT video_id, frame_path, snippet(ocr_index, 2, '', '', '...', 10) AS snippet
            FROM ocr_index
            WHERE ocr_index MATCH ?
            LIMIT 50;
        """, (q,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"query": q, "count": len(rows), "results": rows}
    except Exception as e:
        return {"error": str(e)}
