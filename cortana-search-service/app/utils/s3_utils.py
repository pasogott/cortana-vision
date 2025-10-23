import os
import boto3
from botocore.config import Config
from typing import Optional

S3_URL = os.getenv("S3_URL")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
REGION = os.getenv("REGION") or "us-east-1"

_session = boto3.session.Session()
s3 = _session.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=REGION,
    endpoint_url=S3_URL or None,
    config=Config(s3={"addressing_style": "virtual"}) if S3_URL else None,
)

def presign_get_url(key: str, expires_in: int = 3600, content_type: Optional[str] = None) -> str:
    params = {"Bucket": S3_BUCKET, "Key": key}
    if content_type:
        params["ResponseContentType"] = content_type
    return s3.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)

def presign_put_url(key: str, expires_in: int = 3600, content_type: Optional[str] = None) -> str:
    params = {"Bucket": S3_BUCKET, "Key": key}
    if content_type:
        params["ContentType"] = content_type
    return s3.generate_presigned_url("put_object", Params=params, ExpiresIn=expires_in)
