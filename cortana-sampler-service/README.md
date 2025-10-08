# cortana-sampler-service

Watches Redis for `make-samples-from-video` jobs, extracts scene samples with FFmpeg, uploads them to S3, saves rows to DB, and publishes `make-greyscale-from-samples` jobs.

## Env

See `.env` for all vars. Important:

- `DATABASE_URL`
- `REDIS_URL`
- `JOBS_CHANNEL`
- `EVENT_SAMPLES`
- `EVENT_GREYSCALE`
- `S3_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `REGION`
- `SAMPLE_THRESHOLD` (default `0.08`)

## Run (Docker)

This service is started by `docker-compose` alongside Redis.

## Message format

### In (from API service)

```json
{
  "event": "make-samples-from-video",
  "payload": { "video_id": "<uuid>", "filename": "<original filename>" }
}
```
