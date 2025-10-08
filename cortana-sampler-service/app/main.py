# app/main.py
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
    """Process a single message from Redis pub/sub."""
    if msg.get("type") != "message":
        return

    try:
        data = json.loads(msg["data"])
        event = data.get("event")
        payload = data.get("payload") or {}

        if event == settings.event_samples:
            await make_samples_from_video(payload, redis)
        else:
            print(f"[SAMPLER] Ignored event: {event}")

    except Exception as e:
        print(f"[SAMPLER] Error handling message: {e}")


async def run():
    """Main event loop for the sampler."""
    try:
        print("[SAMPLER] Ensuring database tables exist …")
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except SQLAlchemyError as e:
        print(f"[SAMPLER] Database init error: {e}")
        sys.exit(1)

    redis = _redis_client()
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(settings.jobs_channel)

    print(f"[SAMPLER] Listening on channel '{settings.jobs_channel}' …")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown():
        print("\n[SAMPLER] Shutting down …")
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
        print("[SAMPLER] Closed Redis connection. Bye!")


if __name__ == "__main__":
    asyncio.run(run())
