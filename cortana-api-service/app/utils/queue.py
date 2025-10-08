import json
import redis
from app.config import settings

def get_redis_client():
    """Create and return a Redis client instance."""
    return redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)

def publish_job(event: str, payload: dict):
    """
    Publish a message to Redis for downstream workers.
    Example:
      publish_job("video.uploaded", {"file": "/app/uploads/xyz.mov"})
    """
    client = get_redis_client()
    message = json.dumps({"event": event, "payload": payload})
    client.publish("cortana-jobs", message)
    return {"status": "queued", "event": event}
