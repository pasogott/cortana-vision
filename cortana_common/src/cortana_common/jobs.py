"""Job queue helpers for database-driven job polling."""

import logging
import random
import time
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from cortana_common.config import get_settings
from cortana_common.db import get_db_connection
from cortana_common.models import Job, JobStatus, JobType

logger = logging.getLogger(__name__)


class JobPoller:
    """Base class for job polling workers."""

    def __init__(self, job_type: JobType):
        """Initialize job poller for a specific job type.
        
        Args:
            job_type: Type of jobs to poll for.
        """
        self.job_type = job_type
        self.settings = get_settings()
        logger.info(f"JobPoller initialized for job_type: {job_type.value}")

    def poll_next_job(self) -> Optional[Job]:
        """Poll for the next queued job using SELECT FOR UPDATE SKIP LOCKED.
        
        Returns:
            Job object if available, None otherwise.
        """
        return poll_next_job(self.job_type)

    def ack_job(self, job_id: UUID) -> None:
        """Mark a job as successfully completed.
        
        Args:
            job_id: ID of the job to acknowledge.
        """
        ack_job(job_id)

    def nack_job(self, job_id: UUID, error: str) -> None:
        """Mark a job as failed with error details.
        
        Args:
            job_id: ID of the job to mark as failed.
            error: Error message describing the failure.
        """
        nack_job(job_id, error)

    def enqueue_next_job(
        self,
        video_id: UUID,
        next_job_type: JobType,
        payload: dict[str, Any],
    ) -> UUID:
        """Enqueue the next job in the pipeline.
        
        Args:
            video_id: Video ID for the job.
            next_job_type: Type of the next job.
            payload: Job payload dictionary.
            
        Returns:
            UUID of the created job.
        """
        return enqueue_job(video_id, next_job_type, payload)

    def run_forever(self, process_func) -> None:
        """Run the job polling loop forever.
        
        Args:
            process_func: Function to process each job. Should accept a Job object.
                         Should raise exceptions on failure.
        """
        logger.info(f"Starting job polling loop for {self.job_type.value}")
        
        while True:
            try:
                job = self.poll_next_job()
                
                if job is None:
                    time.sleep(self.settings.job_poll_interval)
                    continue
                
                logger.info(f"Processing job {job.id} (type: {job.job_type.value})")
                
                try:
                    process_func(job)
                    
                    self.ack_job(job.id)
                    logger.info(f"Job {job.id} completed successfully")
                    
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    self.nack_job(job.id, error_msg)
                    logger.error(f"Job {job.id} failed: {error_msg}")
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
                time.sleep(self.settings.job_poll_interval)


def poll_next_job(job_type: JobType) -> Optional[Job]:
    """Poll for the next queued job of a specific type.
    
    Uses SELECT FOR UPDATE SKIP LOCKED to claim jobs atomically without race conditions.
    
    Args:
        job_type: Type of job to poll for.
        
    Returns:
        Job object if available, None otherwise.
        
    Example:
        >>> job = poll_next_job(JobType.TRANSCODE)
        >>> if job:
        ...     # Process job
        ...     ack_job(job.id)
    """
    query = """
        UPDATE jobs
        SET status = %s, started_at = %s, updated_at = %s
        WHERE id = (
            SELECT id FROM jobs
            WHERE status = %s
              AND job_type = %s
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *
    """
    
    now = datetime.now(UTC)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    JobStatus.PROCESSING.value,
                    now,
                    now,
                    JobStatus.QUEUED.value,
                    job_type.value,
                ),
            )
            
            row = cur.fetchone()
            
            if row is None:
                return None
            
            job = Job(**row)
            logger.debug(f"Polled job {job.id} (type: {job.job_type.value})")
            return job


def ack_job(job_id: UUID) -> None:
    """Mark a job as successfully completed.
    
    Args:
        job_id: ID of the job to acknowledge.
        
    Example:
        >>> ack_job(job.id)
    """
    query = """
        UPDATE jobs
        SET status = %s, finished_at = %s, updated_at = %s
        WHERE id = %s
    """
    
    now = datetime.now(UTC)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (JobStatus.DONE.value, now, now, job_id),
            )
            
    logger.info(f"Job {job_id} marked as done")


def nack_job(job_id: UUID, error: str) -> None:
    """Mark a job as failed with error details and retry logic.
    
    If retry_count < max_retries, the job is moved back to 'queued' status.
    Otherwise, it remains in 'failed' status.
    
    Args:
        job_id: ID of the job to mark as failed.
        error: Error message describing the failure.
        
    Example:
        >>> try:
        ...     process_job(job)
        ... except Exception as e:
        ...     nack_job(job.id, str(e))
    """
    settings = get_settings()
    
    query_get = "SELECT retry_count, payload FROM jobs WHERE id = %s"
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_get, (job_id,))
            row = cur.fetchone()
            
            if row is None:
                logger.error(f"Job {job_id} not found")
                return
            
            retry_count = row["retry_count"]
            payload = row["payload"] or {}
            
            if "errors" not in payload:
                payload["errors"] = []
            
            payload["errors"].append({
                "message": error,
                "timestamp": datetime.now(UTC).isoformat(),
                "retry_count": retry_count,
            })
            
            new_retry_count = retry_count + 1
            
            if new_retry_count < settings.job_max_retries:
                new_status = JobStatus.QUEUED.value
                logger.info(
                    f"Job {job_id} failed (retry {new_retry_count}/{settings.job_max_retries}), "
                    f"moving back to queued"
                )
            else:
                new_status = JobStatus.FAILED.value
                logger.warning(
                    f"Job {job_id} failed permanently after {new_retry_count} attempts"
                )
            
            query_update = """
                UPDATE jobs
                SET status = %s,
                    retry_count = %s,
                    payload = %s,
                    finished_at = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            now = datetime.now(UTC)
            finished_at = now if new_status == JobStatus.FAILED.value else None
            
            cur.execute(
                query_update,
                (new_status, new_retry_count, payload, finished_at, now, job_id),
            )


def enqueue_job(
    video_id: UUID,
    job_type: JobType,
    payload: dict[str, Any],
) -> UUID:
    """Create a new job in the queue.
    
    Args:
        video_id: Video ID for the job.
        job_type: Type of job to create.
        payload: Job payload dictionary.
        
    Returns:
        UUID of the created job.
        
    Example:
        >>> job_id = enqueue_job(
        ...     video_id=video.id,
        ...     job_type=JobType.TRANSCODE,
        ...     payload={"video_id": str(video.id), "s3_original_path": video.s3_original_path}
        ... )
    """
    query = """
        INSERT INTO jobs (video_id, job_type, status, payload)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (video_id, job_type.value, JobStatus.QUEUED.value, payload),
            )
            
            row = cur.fetchone()
            job_id = row["id"]
            
    logger.info(f"Enqueued job {job_id} (type: {job_type.value}, video: {video_id})")
    return job_id


def calculate_retry_delay(retry_count: int) -> int:
    """Calculate retry delay with exponential backoff and jitter.
    
    Args:
        retry_count: Current retry attempt number (0-indexed).
        
    Returns:
        Delay in seconds.
        
    Example:
        >>> delay = calculate_retry_delay(0)  # ~60 seconds
        >>> delay = calculate_retry_delay(1)  # ~180 seconds
        >>> delay = calculate_retry_delay(2)  # ~540 seconds
    """
    settings = get_settings()
    base_delay = settings.job_retry_base_delay
    jitter = random.uniform(0.8, 1.2)
    delay = base_delay * (3 ** retry_count) * jitter
    return int(delay)
