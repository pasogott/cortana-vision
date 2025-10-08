from fastapi import FastAPI
from app.database import init_db
from app.routes import upload  # ✅ re-import the upload router

app = FastAPI(title="Cortana API Service")

@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup"""
    init_db()

@app.get("/")
async def root():
    return {"message": "Cortana API is running!"}

# ✅ Include the upload router back
app.include_router(upload.router)
