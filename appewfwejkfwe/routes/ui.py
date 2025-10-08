from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx, os

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

API_BASE = "http://localhost:8000"  # adjust if running behind proxy or container


# ---------- HOME ----------
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page (upload form)."""
    return templates.TemplateResponse("index.html", {"request": request})


# ---------- UPLOAD ----------
@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile):
    """
    Upload video to backend and trigger extraction.
    Then redirects to progress page.
    """
    try:
        upload_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(upload_path, "wb") as f:
            f.write(await file.read())

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/extract/",
                params={"filename": file.filename, "threshold": 0.08},
                timeout=180
            )
        data = resp.json()
        video_id = data.get("video_id", "")

        return templates.TemplateResponse(
            "progress.html",
            {
                "request": request,
                "filename": file.filename,
                "video_id": video_id,
                "stage": "extract",
                "data": data,
            },
        )

    except Exception as e:
        return HTMLResponse(f"<h3>Error: {str(e)}</h3>", status_code=500)


# ---------- EXTRACTION STATUS ----------
@router.get("/status/extract/{filename}", response_class=HTMLResponse)
async def extract_status(request: Request, filename: str):
    """Poll scene extraction progress (uses debug DB or summary endpoint)."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE}/debug/db")
    data = res.json()
    video = next((v for v in data.get("videos", []) if v["filename"] == filename), None)

    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "filename": filename,
            "data": video or {},
            "stage": "extract",
        },
    )


# ---------- START OCR ----------
@router.post("/ocr/start", response_class=HTMLResponse)
async def start_ocr(request: Request, video_id: str = Form(...)):
    """Trigger background OCR task for a specific video."""
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{API_BASE}/ocr/", params={"video_id": video_id})
    data = res.json()

    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "video_id": video_id,
            "data": data,
            "stage": "ocr",
        },
    )


# ---------- OCR STATUS ----------
@router.get("/status/ocr/{video_id}", response_class=HTMLResponse)
async def ocr_status(request: Request, video_id: str):
    """Poll OCR progress and show progress bar."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE}/ocr/status/{video_id}")
    data = res.json()

    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "video_id": video_id,
            "data": data,
            "stage": "ocr",
        },
    )


# ---------- SEARCH ----------
@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Render search page."""
    return templates.TemplateResponse("search.html", {"request": request})


@router.post("/search", response_class=HTMLResponse)
async def search_text(request: Request, query: str = Form(...), video_id: str = Form(...)):
    """Perform OCR text search."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE}/search", params={"q": query, "video_id": video_id})
    data = res.json()
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "query": query,
            "video_id": video_id,
            "data": data,
        },
    )


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(request: Request, video_id: str = None, filename: str = None):
    """Progress dashboard for extract + OCR status."""
    async with httpx.AsyncClient() as client:
        extract_data, ocr_data = None, None

        if filename:
            res = await client.get(f"{API_BASE}/extract/status/{filename}")
            extract_data = res.json()

        if video_id:
            res = await client.get(f"{API_BASE}/ocr/status/{video_id}")
            ocr_data = res.json()

    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "filename": filename,
            "video_id": video_id,
            "extract": extract_data,
            "ocr": ocr_data,
        },
    )


@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, q: str = "", video_id: str = ""):
    """
    Displays OCR search results visually using results.html.
    Accepts query parameters:
    - q: search query (e.g. tanja1976)
    - video_id: video UUID
    """
    try:
        data = {"status": "pending", "matches": []}

        # Only fetch if both q and video_id are provided
        if q and video_id:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{API_BASE}/search", params={"q": q, "video_id": video_id})
                data = res.json()

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "query": q,
                "video_id": video_id,
                "data": data,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "query": q,
                "video_id": video_id,
                "data": {"status": "error", "detail": str(e), "matches": []},
            },
        )