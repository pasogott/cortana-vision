import asyncio
import json
import signal
import sys
from redis import Redis
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models import Base
from app.database import engine
from app.worker import make_samples_from_video


print("[INIT] Ensuring database and tables exist …")
Base.metadata.create_all(bind=engine, checkfirst=True)


def _redis_client() -> Redis:
    """Return a Redis connection using the configured URL."""
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def handle_message(msg: dict, redis: Redis):
    """Process a single Redis pub/sub message safely."""
    if msg.get("type") != "message":
        return

    raw = msg.get("data")
    if not raw:
        print("[SAMPLER][WARN] Empty message received — ignoring.")
        return

    # Handle both JSON and raw string events
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[SAMPLER][WARN] Non-JSON payload: {raw}")
        return

    event = data.get("event")
    payload = data.get("payload") or {}

    if not event:
        print(f"[SAMPLER][WARN] Missing event field in message: {data}")
        return

    try:
        if event == settings.event_samples:
            await make_samples_from_video(payload, redis)
        else:
            print(f"[SAMPLER] Ignored event: {event}")
    except Exception as e:
        print(f"[SAMPLER][ERR] Error handling event '{event}': {e}")


async def run():
    """Main async loop for listening to Redis events."""
    try:
        print("[SAMPLER] Ensuring database tables exist …")
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except SQLAlchemyError as e:
        print(f"[SAMPLER][DB ERR] {e}")
        sys.exit(1)

    redis = _redis_client()
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(settings.jobs_channel)

    print(f"[SAMPLER] 🧠 Listening on '{settings.jobs_channel}' for events…")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown():
        print("\n[SAMPLER] 📴 Shutting down gracefully …")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    try:
        while not stop_event.is_set():
            msg = pubsub.get_message(timeout=1.0)
            if msg:
                await handle_message(msg, redis)
            await asyncio.sleep(0.1)
    finally:
        pubsub.close()
        redis.close()
        print("[SAMPLER] Redis connection closed. Bye 👋")


if __name__ == "__main__":
    asyncio.run(run())
