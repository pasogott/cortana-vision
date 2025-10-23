# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis, ConnectionError
import threading, time, json

from app.database import init_db
from app.utils.indexer import ensure_fts, background_reindex
from app.config import settings
from app.routes.api import router as api_router

app = FastAPI(title="Cortana Search & UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://167.235.203.43:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()
    ensure_fts()
    def redis_listener():
        while True:
            try:
                redis = Redis.from_url(settings.redis_url, decode_responses=True)
                sub = redis.pubsub(ignore_subscribe_messages=True)
                sub.subscribe(settings.events_channel)
                for msg in sub.listen():
                    if not msg or msg.get("type") != "message":
                        continue
            except ConnectionError:
                time.sleep(3)
            except Exception:
                time.sleep(2)

    threading.Thread(target=redis_listener, daemon=True).start()
    threading.Thread(target=background_reindex, daemon=True).start()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router)
