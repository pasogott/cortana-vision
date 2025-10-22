# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from redis import Redis, ConnectionError
import threading, time, json

from app.database import init_db
from app.routes import search, dashboard   # ensure each file defines `router = APIRouter(...)`
from app.utils.indexer import ensure_fts, update_index, background_reindex
from app.config import settings

app = FastAPI(title="Cortana Search & UI")

@app.on_event("startup")
def startup():
    init_db()
    ensure_fts()
    print("[SEARCH] ✅ Database & FTS ready.")

    def redis_listener():
        """Auto-reconnecting Redis subscription loop on EVENTS_CHANNEL."""
        while True:
            try:
                redis = Redis.from_url(settings.redis_url, decode_responses=True)
                sub = redis.pubsub(ignore_subscribe_messages=True)
                sub.subscribe(settings.events_channel)
                print(f"[SEARCH][EVENT] 🧠 Listening for '{settings.event_ocr_update}' on {settings.events_channel}…")

                for msg in sub.listen():
                    if not msg or msg.get("type") != "message":
                        continue

                    raw = msg["data"]
                    event, key = None, None

                    # Prefer JSON; fallback to "event:key"
                    try:
                        payload = json.loads(raw)
                        event = payload.get("event")
                        key = payload.get("key")
                    except Exception:
                        if isinstance(raw, str) and ":" in raw:
                            event, key = raw.split(":", 1)

                    if event == settings.event_ocr_update and key:
                        print(f"[SEARCH][EVENT] 🧩 OCR update → {key}")
                        # Triggers already insert into FTS; no manual reindex needed.
                        pass

            except ConnectionError:
                print("[SEARCH][REDIS] ⚠️ Lost connection. Retrying in 3s…")
                time.sleep(3)
            except Exception as e:
                # ignore occasional idle/timeout messages; log the rest and continue
                if "Timeout" not in str(e):
                    print(f"[SEARCH][REDIS][ERR] {e}")
                time.sleep(2)

    threading.Thread(target=redis_listener, daemon=True).start()
    threading.Thread(target=background_reindex, daemon=True).start()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(search.router)
app.include_router(dashboard.router)
