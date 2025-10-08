import os
import shutil
from uuid import uuid4
from fastapi import UploadFile
import boto3
from botocore.config import Config
from app.config import settings

# ---------- Local storage helpers ----------
def ensure_upload_dir() -> str:
    """Ensure upload directory exists and return its path."""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_upload(file: UploadFile) -> str:
    """
    Save uploaded file locally and return its absolute path.
    """
    upload_dir = ensure_upload_dir()
    filename = f"{uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path


# ---------- Hetzner S3 / Object Storage ----------
def get_s3_client():
    """Return a configured boto3 S3 client compatible with Hetzner."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.REGION,
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def upload_to_s3(local_path: str, remote_path: str) -> str:
    """
    Upload a local file to Hetzner S3-compatible storage.
    Returns the full public URL of the uploaded object.
    """
    s3 = get_s3_client()
    s3.upload_file(local_path, settings.S3_BUCKET, remote_path)
    return f"{settings.S3_URL}/{settings.S3_BUCKET}/{remote_path}"


def download_from_s3(remote_path: str, local_path: str) -> str:
    """
    Download a file from S3 to a given local path.
    """
    s3 = get_s3_client()
    s3.download_file(settings.S3_BUCKET, remote_path, local_path)
    return local_path
