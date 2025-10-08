import boto3
import os
from botocore.exceptions import ClientError
from app.config import settings

def get_s3_client():
    """Initialize and return a properly configured S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_url,  # ✅ Explicitly point to Hetzner
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.region,
    )

def upload_to_s3(local_path: str, key: str) -> str:
    """Upload a local file to S3 and return its public URL."""
    s3 = get_s3_client()
    bucket = settings.s3_bucket
    try:
        s3.upload_file(local_path, bucket, key)
        public_url = f"{settings.s3_url.rstrip('/')}/{bucket}/{key}"
        print(f"[S3] ✅ Uploaded {local_path} → {public_url}")
        return public_url
    except ClientError as e:
        print(f"[S3][ERR] Upload failed for {local_path}: {e}")
        raise

def download_from_s3(key: str, local_path: str):
    """Download a file from S3 to a local path."""
    s3 = get_s3_client()
    bucket = settings.s3_bucket
    try:
        s3.download_file(bucket, key, local_path)
        print(f"[S3] ✅ Downloaded s3://{bucket}/{key} → {local_path}")
    except ClientError as e:
        print(f"[S3][ERR] Download failed for {key}: {e}")
        raise
