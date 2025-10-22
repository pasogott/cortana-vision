from fastapi import FastAPI
from app.database import init_db
from app.routes import upload
from app.utils.db_integrity import ensure_integrity
from app.utils.db_selfheal import self_heal_database


app = FastAPI(title="Cortana API Service")

@app.on_event("startup")
async def startup_event():
    init_db()
    ensure_integrity() 
    self_heal_database()

@app.get("/")
async def root():
    return {"message": "Cortana API is running!"}

app.include_router(upload.router)
