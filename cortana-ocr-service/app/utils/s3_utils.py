import boto3
from botocore.exceptions import ClientError
from app.config import settings

s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.region,
)

def download_from_s3(key: str, local_path: str):
    try:
        s3.download_file(settings.s3_bucket, key, local_path)
        print(f"[S3] ✅ Downloaded s3://{settings.s3_bucket}/{key}")
    except ClientError as e:
        print(f"[S3][ERR] Download failed: {e}")
        raise
