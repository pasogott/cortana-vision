import boto3
import os
from botocore.config import Config
from app.config import settings

# Initialize S3 client
s3 = boto3.client(
    "s3",
    endpoint_url=settings.S3_URL,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=settings.REGION,
    config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
)

def upload_to_s3(local_path: str, remote_path: str) -> str:
    """Upload a local file to S3 and return its HTTPS URL."""
    s3.upload_file(local_path, settings.S3_BUCKET, remote_path)
    return f"{settings.S3_URL}/{settings.S3_BUCKET}/{remote_path}"
