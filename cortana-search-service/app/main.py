from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routes import search, dashboard
from app.utils.indexer import ensure_fts

app = FastAPI(title="Cortana Search & UI")

@app.on_event("startup")
def startup():
    init_db()
    ensure_fts()
    print("[SEARCH] ✅ Database & FTS ready.")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(search.router)
app.include_router(dashboard.router)
