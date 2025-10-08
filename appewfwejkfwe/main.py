# app/main.py
from fastapi import FastAPI
from app.database import init_db
from app.routes import upload, extract, ocr, search, debug_db, ui
app = FastAPI(title="Snapshot API – Eagle Vision")

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(ocr.router)
app.include_router(search.router)
app.include_router(debug_db.router)
app.include_router(ui.router)


@app.get("/")
def home():
    return {"status": "ok", "message": "Eagle Vision API running"}

@app.get("/debug/s3")
def debug_s3():
    from app.utils.storage import s3, S3_BUCKET
    try:
        result = s3.list_buckets()
        return {"status": "ok", "buckets": [b["Name"] for b in result["Buckets"]]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
