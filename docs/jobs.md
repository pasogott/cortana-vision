# Job Queue Contract – cortana-vision

## Purpose

This document defines the job queue contract for cortana-vision's processing pipeline. It specifies all job types, their payload schemas, state transitions, retry policies, and idempotency guarantees. All workers must adhere to this contract to ensure reliable, predictable pipeline execution.

---

## Job Queue Mechanics

### Database-Driven Polling

cortana-vision uses **PostgreSQL-based job polling** rather than an external message queue. Workers poll the `jobs` table using `SELECT FOR UPDATE SKIP LOCKED` to claim jobs atomically without race conditions.

**Benefits:**
- Single source of truth (no queue/DB sync issues)
- ACID guarantees for job state transitions
- Simplified infrastructure (no separate queue service)
- Built-in persistence and audit trail

**Implementation Pattern:**
```sql
SELECT * FROM jobs
WHERE status = 'queued'
  AND job_type = 'transcode'
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

### Job Leasing (Future Enhancement)

The current schema supports basic retry counting. For production deployments with multiple worker replicas, consider adding lease fields in a future migration:

```sql
ALTER TABLE jobs ADD COLUMN locked_by TEXT;
ALTER TABLE jobs ADD COLUMN locked_until TIMESTAMPTZ;
```

This prevents job abandonment if a worker crashes mid-processing. Workers would refresh `locked_until` via heartbeat and other workers can reclaim expired leases.

---

## Job Types and Payloads

All job types are defined in the database enum `job_type`:

```sql
CREATE TYPE job_type AS ENUM (
  'transcode',
  'sample',
  'ocr',
  'segment_index',
  'clip_generate'
);
```

### 1. transcode

**Triggered by:** s3-cron-scanner after detecting new video upload

**Purpose:** Convert original high-resolution video to HLS streaming format and generate thumbnail

**Payload Schema:**
```json
{
  "video_id": "uuid",
  "s3_original_path": "videos/original/{video_id}/master.mp4"
}
```

**Example:**
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "s3_original_path": "videos/original/a1b2c3d4-e5f6-7890-abcd-ef1234567890/master.mp4"
}
```

**Worker Responsibilities:**
1. Read original video from S3 using `s3_original_path`
2. Generate HLS playlist and segments at `videos/proxy/{video_id}/index.m3u8`
3. Extract poster frame and upload to `thumbs/{video_id}/poster.jpg`
4. Update `videos` table with `s3_proxy_path` and `s3_thumb_path`
5. Mark job as `done`
6. Enqueue `sample` job for next pipeline stage

**Output Artifacts:**
- `videos/proxy/{video_id}/index.m3u8` (HLS playlist)
- `videos/proxy/{video_id}/segment_*.ts` (HLS segments)
- `thumbs/{video_id}/poster.jpg` (thumbnail)

---

### 2. sample

**Triggered by:** transcode-worker after successful HLS generation

**Purpose:** Extract keyframes from original video for OCR processing using perceptual hashing to eliminate duplicates

**Payload Schema:**
```json
{
  "video_id": "uuid",
  "s3_original_path": "videos/original/{video_id}/master.mp4",
  "target_fps": 10,
  "dedupe_threshold": 0.95
}
```

**Example:**
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "s3_original_path": "videos/original/a1b2c3d4-e5f6-7890-abcd-ef1234567890/master.mp4",
  "target_fps": 10,
  "dedupe_threshold": 0.95
}
```

**Worker Responsibilities:**
1. **CRITICAL:** Read from ORIGINAL high-resolution video (not proxy) for maximum OCR accuracy
2. Down-sample video from source FPS (e.g., 120fps) to `target_fps` (default: 10fps)
3. Apply perceptual hashing (pHash/dHash) to detect duplicate frames
4. Skip frames with similarity above `dedupe_threshold` (default: 0.95)
5. Upload unique keyframes to `frames/{video_id}/{timestamp_ms}.jpg`
6. Mark job as `done`
7. Enqueue `ocr` job with list of frame paths

**Output Artifacts:**
- `frames/{video_id}/{timestamp_ms}.jpg` (one per unique keyframe)

**Configuration Defaults:**
- `target_fps`: 10 (balance between coverage and processing cost)
- `dedupe_threshold`: 0.95 (skip frames >95% similar to previous)

---

### 3. ocr

**Triggered by:** sampler-worker after keyframe extraction

**Purpose:** Detect and extract text from keyframes using Tesseract OCR

**Payload Schema:**
```json
{
  "video_id": "uuid",
  "frame_paths": ["frames/{video_id}/{timestamp_ms}.jpg", ...],
  "languages": ["eng", "deu", "fra"],
  "min_confidence": 0.6
}
```

**Example:**
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "frame_paths": [
    "frames/a1b2c3d4-e5f6-7890-abcd-ef1234567890/1500.jpg",
    "frames/a1b2c3d4-e5f6-7890-abcd-ef1234567890/1600.jpg",
    "frames/a1b2c3d4-e5f6-7890-abcd-ef1234567890/1700.jpg"
  ],
  "languages": ["eng"],
  "min_confidence": 0.6
}
```

**Worker Responsibilities:**
1. Read each keyframe from S3 using `frame_paths`
2. Run Tesseract OCR with specified `languages`
3. Extract text, bounding boxes, confidence scores, and detected language
4. Filter results below `min_confidence` threshold
5. Insert raw detections into `segments` table with:
   - `text`: raw OCR output
   - `normalized_text`: lowercased, whitespace-normalized
   - `text_hash`: hash for deduplication
   - `t_start`, `t_end`: derived from frame timestamp
   - `confidence`: OCR confidence score
   - `bounding_box`: JSONB with {x, y, width, height}
   - `language`: detected language code
   - `owner_id`, `team_id`: copied from parent video
6. Mark job as `done`
7. Enqueue `segment_index` job for text merging and entity extraction

**Output Artifacts:**
- Rows in `segments` table (one per detected text region per frame)

**Configuration Defaults:**
- `languages`: ["eng"] (English only; expand as needed)
- `min_confidence`: 0.6 (filter low-quality detections)

---

### 4. segment_index

**Triggered by:** ocr-worker after text extraction

**Purpose:** Merge consecutive identical text detections, extract structured entities, and refresh search indexes

**Payload Schema:**
```json
{
  "video_id": "uuid"
}
```

**Example:**
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Worker Responsibilities:**
1. Query all `segments` for `video_id` ordered by `t_start`
2. **Merge identical text:** Consolidate consecutive segments with same `text_hash` into continuous time ranges
3. **Extract entities:** Parse `normalized_text` for:
   - `@mentions`: Twitter/Instagram handles
   - `#hashtags`: Social media tags
   - `url`: HTTP/HTTPS links
   - `emoji`: Unicode emoji characters
   - `number`: Numeric values (phone numbers, prices, counts)
4. Insert extracted entities into `entities` table with:
   - `segment_id`: FK to parent segment
   - `entity_type`: enum value
   - `value`: raw extracted string
   - `normalized_value`: cleaned/lowercased version
5. Refresh `search_materialized` view via `SELECT refresh_search_materialized();`
6. Update `videos.status` to `'ready'` to mark video as searchable
7. Mark job as `done`

**Output Artifacts:**
- Updated `segments` table (merged time ranges)
- Rows in `entities` table
- Refreshed `search_materialized` view
- `videos.status = 'ready'`

**Entity Extraction Patterns:**
- Mentions: `@[a-zA-Z0-9_]+`
- Hashtags: `#[a-zA-Z0-9_]+`
- URLs: Standard URL regex
- Emojis: Unicode emoji ranges
- Numbers: `\d+` with context (currency symbols, units)

---

### 5. clip_generate

**Triggered by:** api-gateway on user request (not part of automatic pipeline)

**Purpose:** Generate on-demand video clip from original video for search result playback

**Payload Schema:**
```json
{
  "video_id": "uuid",
  "clip_id": "uuid",
  "t_start": 1500,
  "t_end": 3000,
  "padding_ms": 2000,
  "s3_original_path": "videos/original/{video_id}/master.mp4"
}
```

**Example:**
```json
{
  "video_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "clip_id": "clip-xyz-123",
  "t_start": 1500,
  "t_end": 3000,
  "padding_ms": 2000,
  "s3_original_path": "videos/original/a1b2c3d4-e5f6-7890-abcd-ef1234567890/master.mp4"
}
```

**Worker Responsibilities:**
1. Read original video from S3
2. Calculate clip range: `[t_start - padding_ms, t_end + padding_ms]`
3. Extract clip using FFmpeg with precise timestamps
4. Upload clip to `videos/clips/{video_id}/{clip_id}.mp4`
5. Mark job as `done`
6. Return S3 path to api-gateway (via job result or separate table)

**Output Artifacts:**
- `videos/clips/{video_id}/{clip_id}.mp4` (auto-deleted after 30 days via S3 lifecycle)

**Configuration Defaults:**
- `padding_ms`: 2000 (2 seconds before/after for context)

---

## Job State Machine

### States

```sql
CREATE TYPE job_status AS ENUM (
  'queued',
  'processing',
  'done',
  'failed'
);
```

### State Transitions

```
queued ──────────> processing ──────────> done
                        │
                        └──────────> failed
                                        │
                                        └──> queued (if retry_count < max_retries)
```

**Valid Transitions:**
- `queued` → `processing`: Worker claims job via `SELECT FOR UPDATE SKIP LOCKED`
- `processing` → `done`: Worker completes successfully
- `processing` → `failed`: Worker encounters unrecoverable error
- `failed` → `queued`: Automatic retry if `retry_count < 3`

**Forbidden Transitions:**
- `done` → any other state (jobs are immutable once completed)
- `queued` → `failed` (must pass through `processing`)

---

## Retry Policy

### Automatic Retries

- **Max retries:** 3 attempts
- **Backoff strategy:** Exponential with jitter
  - Retry 1: ~1 minute delay
  - Retry 2: ~5 minutes delay
  - Retry 3: ~15 minutes delay
- **Implementation:** Workers check `retry_count` before claiming jobs and skip jobs exceeding max retries

### Retry Logic

```python
def should_retry(job):
    return job.retry_count < 3 and job.status == 'failed'

def calculate_retry_delay(retry_count):
    base_delay = 60  # 1 minute
    jitter = random.uniform(0.8, 1.2)
    return base_delay * (3 ** retry_count) * jitter
```

### Non-Retryable Errors

Workers should mark jobs as `failed` without retry for:
- Invalid payload schema
- Missing required S3 objects (original video deleted)
- Database constraint violations
- Authentication/authorization failures

For retryable errors (network timeouts, temporary S3 issues), increment `retry_count` and transition back to `queued`.

---

## Idempotency Guarantees

### Pipeline Jobs (transcode, sample, ocr, segment_index)

**Constraint:** Only ONE job of each type per video can be `queued` or `processing` at a time.

**Implementation:** Add unique partial index in future migration:
```sql
CREATE UNIQUE INDEX idx_jobs_video_pipeline_active
ON jobs (video_id, job_type)
WHERE status IN ('queued', 'processing');
```

This prevents duplicate pipeline jobs from being enqueued if a worker crashes and restarts.

### On-Demand Jobs (clip_generate)

**Constraint:** Multiple clip jobs for the same video are allowed (different time ranges).

**Idempotency:** Workers should check if output artifact already exists in S3 before processing:
- If `videos/clips/{video_id}/{clip_id}.mp4` exists, skip processing and mark `done`
- This handles duplicate API requests gracefully

---

## Error Handling

### Error Message Storage

When a job fails, workers must populate `jobs.payload` with error details:

```json
{
  "error": {
    "type": "S3ObjectNotFound",
    "message": "Original video not found at videos/original/abc-123/master.mp4",
    "timestamp": "2025-11-13T15:42:00Z",
    "retry_count": 2
  },
  "original_payload": { ... }
}
```

### Logging Strategy

- **Structured logs:** JSON format with `job_id`, `video_id`, `job_type`, `status`
- **External logs:** Optional upload to `logs/pipeline/{job_id}.json` in S3
- **Monitoring:** Track job duration, failure rates, retry rates per job type

### Dead Letter Queue

Jobs exceeding max retries remain in `failed` state for manual investigation. Consider:
- Alerting on high failure rates
- Dashboard showing failed jobs by type
- Manual retry mechanism via admin API

---

## Worker Authentication

### Supabase Service Role

Workers authenticate to Supabase using the **service role key** which bypasses RLS for writes while respecting RLS for reads.

**Environment Variables:**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Service role JWT
```

**RLS Behavior:**
- **Writes:** Service role can insert/update `jobs`, `segments`, `entities`, `videos`
- **Reads:** Service role respects RLS policies (reads only data for authenticated user)

### S3 Authentication

Workers use shared S3 credentials stored in Kubernetes Secrets:

```bash
S3_ENDPOINT=https://your-region.digitaloceanspaces.com
S3_BUCKET=cortana-vision-prod
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

---

## Job Enqueueing Patterns

### Pipeline Jobs

Each worker enqueues the next pipeline stage upon successful completion:

```python
# transcode-worker after completion
create_job(
    video_id=video_id,
    job_type='sample',
    payload={
        'video_id': video_id,
        's3_original_path': original_path,
        'target_fps': 10,
        'dedupe_threshold': 0.95
    }
)
```

### On-Demand Jobs

api-gateway creates `clip_generate` jobs in response to user requests:

```python
# api-gateway endpoint
@app.post("/clips")
def create_clip(video_id: UUID, t_start: int, t_end: int):
    clip_id = uuid4()
    create_job(
        video_id=video_id,
        job_type='clip_generate',
        payload={
            'video_id': video_id,
            'clip_id': clip_id,
            't_start': t_start,
            't_end': t_end,
            'padding_ms': 2000,
            's3_original_path': f'videos/original/{video_id}/master.mp4'
        }
    )
    return {'clip_id': clip_id, 'status': 'queued'}
```

---

## Performance Considerations

### Batch Processing

For OCR jobs with many frames, consider batching:
- Process frames in chunks of 50-100
- Commit segments to DB in batches
- Reduces transaction overhead

### Concurrent Workers

Multiple worker replicas can process jobs in parallel:
- `SELECT FOR UPDATE SKIP LOCKED` prevents double-processing
- Each worker type (transcode, ocr, etc.) can scale independently
- Monitor queue depth and scale workers accordingly

### Database Load

- Use connection pooling (e.g., pgBouncer)
- Index `jobs(status, job_type, created_at)` for efficient polling
- Partition `segments` table by `video_id` if table grows very large

---

## Future Enhancements

### Job Leasing

Add lease fields to prevent abandoned jobs:
```sql
ALTER TABLE jobs ADD COLUMN locked_by TEXT;
ALTER TABLE jobs ADD COLUMN locked_until TIMESTAMPTZ;
```

Workers would:
1. Claim job and set `locked_by` to worker ID
2. Set `locked_until` to `now() + 5 minutes`
3. Refresh `locked_until` via heartbeat every 2 minutes
4. Other workers can reclaim jobs where `locked_until < now()`

### Priority Queues

Add `priority` field to jobs table:
```sql
ALTER TABLE jobs ADD COLUMN priority INTEGER DEFAULT 0;
```

Workers poll with `ORDER BY priority DESC, created_at ASC` to process high-priority jobs first.

### Job Dependencies

For complex workflows, add `depends_on` field:
```sql
ALTER TABLE jobs ADD COLUMN depends_on UUID REFERENCES jobs(id);
```

Workers only claim jobs where dependent job is `done`.

---

## Summary

This job contract establishes:

1. **Five job types** with clear responsibilities and payload schemas
2. **Database-driven polling** using `SELECT FOR UPDATE SKIP LOCKED`
3. **Four-state machine** with automatic retry logic (max 3 attempts)
4. **Idempotency guarantees** via unique constraints on pipeline jobs
5. **Structured error handling** with error details in payload
6. **Service role authentication** for workers to bypass RLS on writes
7. **Clear enqueueing patterns** for pipeline progression and on-demand jobs

All workers must implement this contract to ensure reliable, predictable pipeline execution. Deviations should be documented as ADRs and reflected in schema migrations.
