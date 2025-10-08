print("[GREYSCALE] 🧩 Boot sequence starting…")
import sys
sys.stdout.flush()

import asyncio
import json
import time
from redis import Redis, ConnectionError
from app.config import settings
from app.worker import make_greyscale_from_samples


async def run_worker():
    print("[GREYSCALE] 🚀 Booting up worker …")

    # Retry Redis connection
    for attempt in range(10):
        try:
            redis = Redis.from_url(settings.redis_url, decode_responses=True)
            redis.ping()
            print(f"[GREYSCALE] ✅ Connected to Redis at {settings.redis_url}")
            break
        except ConnectionError:
            print(f"[GREYSCALE] ⏳ Waiting for Redis ({attempt+1}/10)…")
            time.sleep(2)
    else:
        print("[GREYSCALE][ERR] ❌ Could not connect to Redis. Exiting.")
        return

    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(settings.jobs_channel)
    print(f"[GREYSCALE] 🧠 Listening on {settings.jobs_channel} for '{settings.event_greyscale}' events…")

    # Persistent listen loop
    try:
        while True:
            msg = pubsub.get_message(timeout=1.0)
            if not msg:
                await asyncio.sleep(0.5)
                continue

            if msg["type"] != "message":
                continue

            try:
                data = json.loads(msg["data"])
                event = data.get("event")
                payload = data.get("payload", {})
                if event == settings.event_greyscale:
                    print(f"[GREYSCALE] 🔔 Received event for {payload.get('frame_s3_key')}")
                    await make_greyscale_from_samples(payload, redis)
                else:
                    print(f"[GREYSCALE] Ignored event: {event}")
            except Exception as e:
                print(f"[GREYSCALE][ERR] Error handling message: {e}")
    except KeyboardInterrupt:
        print("\n[GREYSCALE] 🛑 Shutdown signal received.")
    finally:
        pubsub.close()
        redis.close()
        print("[GREYSCALE] 🧹 Closed Redis connection. Bye!")

if __name__ == "__main__":
    asyncio.run(run_worker())
