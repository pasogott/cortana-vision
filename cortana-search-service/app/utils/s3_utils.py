import boto3
from botocore.exceptions import ClientError
import os

S3_URL = os.getenv("S3_URL")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
REGION = os.getenv("REGION")

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=REGION,
)

def list_ocr_files(prefix="videos/"):
    try:
        objs = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if "Contents" not in objs:
            return []
        return [obj["Key"] for obj in objs["Contents"] if obj["Key"].endswith(".txt")]
    except ClientError as e:
        print(f"[S3][ERR] {e}")
        return []

def download_from_s3(key: str, local_path: str):
    try:
        s3.download_file(S3_BUCKET, key, local_path)
        print(f"[S3] ✅ {key} → {local_path}")
    except ClientError as e:
        print(f"[S3][ERR] {e}")
