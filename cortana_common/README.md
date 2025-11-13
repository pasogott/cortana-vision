# cortana_common

Shared utilities package for cortana-vision services providing common functionality for database access, S3 operations, configuration management, and job queue processing.

## Features

- **Configuration Management**: Type-safe settings loaded from environment variables using pydantic-settings
- **Database Access**: PostgreSQL/Supabase connection utilities with automatic cleanup
- **S3 Operations**: Boto3 wrapper for object storage with presigned URLs
- **Job Queue**: Database-driven job polling with retry logic and state management
- **Pydantic Models**: Type-safe models matching database schema

## Installation

Add as a path dependency in your service's `pyproject.toml`:

```toml
[project]
dependencies = [
    "cortana-common @ {path = '../../cortana_common', editable = true}",
]
```

Then install with uv:

```bash
uv sync
```

## Usage

### Configuration

```python
from cortana_common import get_settings

settings = get_settings()
print(settings.supabase_url)
print(settings.s3_bucket)
```

Required environment variables:

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# S3
S3_ENDPOINT=https://your-region.digitaloceanspaces.com
S3_BUCKET=cortana-vision-prod
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...

# Optional
JOB_POLL_INTERVAL=5
JOB_MAX_RETRIES=3
LOG_LEVEL=INFO
```

### Database Access

```python
from cortana_common import get_db_connection, execute_query

# Using context manager
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
        video = cur.fetchone()

# Using helper function
video = execute_query(
    "SELECT * FROM videos WHERE id = %s",
    (video_id,),
    fetch_one=True
)
```

### S3 Operations

```python
from cortana_common import get_s3_client

s3 = get_s3_client()

# Upload file
s3.upload_file(
    "/tmp/video.mp4",
    "videos/original/abc-123/master.mp4",
    content_type="video/mp4"
)

# Download file
s3.download_file(
    "videos/original/abc-123/master.mp4",
    "/tmp/downloaded.mp4"
)

# Generate presigned URL (15 min expiry)
url = s3.generate_presigned_url(
    "videos/proxy/abc-123/index.m3u8",
    expiration=900
)

# Check if object exists
if s3.object_exists("videos/original/abc-123/master.mp4"):
    print("Video exists!")

# List objects with prefix
frames = s3.list_objects("frames/abc-123/")
```

### Job Queue Processing

```python
from cortana_common import JobPoller, JobType, enqueue_job
from uuid import UUID

# Create a job poller
poller = JobPoller(JobType.TRANSCODE)

# Define processing function
def process_transcode_job(job):
    print(f"Processing job {job.id}")
    video_id = UUID(job.payload["video_id"])
    
    # Do work...
    
    # Enqueue next job
    poller.enqueue_next_job(
        video_id=video_id,
        next_job_type=JobType.SAMPLE,
        payload={"video_id": str(video_id), "target_fps": 10}
    )

# Run polling loop
poller.run_forever(process_transcode_job)
```

Manual job operations:

```python
from cortana_common import poll_next_job, ack_job, nack_job, enqueue_job
from cortana_common import JobType
from uuid import UUID

# Poll for next job
job = poll_next_job(JobType.TRANSCODE)

if job:
    try:
        # Process job
        process_job(job)
        
        # Mark as successful
        ack_job(job.id)
        
    except Exception as e:
        # Mark as failed (will retry if under max_retries)
        nack_job(job.id, str(e))

# Enqueue new job
job_id = enqueue_job(
    video_id=UUID("abc-123"),
    job_type=JobType.TRANSCODE,
    payload={"video_id": "abc-123", "s3_original_path": "videos/original/abc-123/master.mp4"}
)
```

### Pydantic Models

```python
from cortana_common import Job, Video, JobType, JobStatus, VideoStatus

# Models automatically validate and convert database rows
job = Job(
    id=UUID("..."),
    video_id=UUID("..."),
    job_type=JobType.TRANSCODE,
    status=JobStatus.QUEUED,
    retry_count=0,
    payload={"video_id": "..."},
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Access with type safety
print(job.job_type.value)  # "transcode"
print(job.status.value)    # "queued"
```

## Development

Install with dev dependencies:

```bash
cd cortana_common
uv sync --extra dev
```

Run tests:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest --cov=cortana_common --cov-report=html
```

## Architecture

The package follows these design principles:

- **Singleton pattern**: Settings and S3 client are cached using `@lru_cache`
- **Context managers**: Database connections use context managers for automatic cleanup
- **Type safety**: All functions use type hints and pydantic models
- **Error handling**: Comprehensive logging and error propagation
- **Testability**: All components can be mocked for testing

## Dependencies

- `psycopg[binary]>=3.2.0` - PostgreSQL adapter with binary support
- `boto3>=1.34.0` - AWS SDK for S3 operations
- `pydantic>=2.0.0` - Data validation and settings management
- `pydantic-settings>=2.0.0` - Settings management from environment

## License

Internal package for cortana-vision project.
