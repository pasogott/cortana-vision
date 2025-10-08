import boto3
from botocore.config import Config
import os

from app.config import settings

# ------------------------------------------------------------
#  S3 CLIENT
# ------------------------------------------------------------
s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.region,
    config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
)


# ------------------------------------------------------------
#  UPLOAD / DOWNLOAD HELPERS
# ------------------------------------------------------------
def upload_to_s3(local_path: str, remote_path: str) -> str:
    """Uploads a local file to S3 and returns the full public URL."""
    s3.upload_file(local_path, settings.s3_bucket, remote_path)
    return f"{settings.s3_url}/{settings.s3_bucket}/{remote_path}"


def download_from_s3(object_key: str, out_path: str) -> None:
    """Downloads a file from S3 to local filesystem."""
    s3.download_file(settings.s3_bucket, object_key, out_path)
