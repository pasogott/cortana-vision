# app/utils/pubsub_utils.py
import json
from redis import Redis

def publish_event(redis: Redis, channel: str, event: str, key: str):
    """Publish events in JSON format so all services can decode safely."""
    payload = json.dumps({"event": event, "key": key})
    redis.publish(channel, payload)
