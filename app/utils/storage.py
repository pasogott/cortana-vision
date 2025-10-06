import boto3
import os
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, EndpointConnectionError

# ---- Load from environment ----
S3_URL = os.getenv("S3_URL", "https://nbg1.your-objectstorage.com")
S3_BUCKET = os.getenv("S3_BUCKET", "cyberheld")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
REGION = os.getenv("REGION", "nbg1")

# ---- Create S3 client (Hetzner-compatible) ----
# Hetzner requires path-style URLs: https://nbg1.your-objectstorage.com/bucket/object
s3 = boto3.client(
    "s3",
    endpoint_url=S3_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=REGION,
    config=Config(s3={"addressing_style": "path"}, signature_version="s3v4")
)

# ---- Upload helper ----
def upload_to_s3(local_path: str, remote_path: str) -> str:
    """
    Uploads file to Hetzner S3 bucket and returns a direct access URL.
    """
    try:
        s3.upload_file(local_path, S3_BUCKET, remote_path)
        # Build correct public URL pattern for Hetzner
        url = f"{S3_URL}/{S3_BUCKET}/{remote_path}"
        return url

    except NoCredentialsError:
        raise RuntimeError("❌ Missing or invalid S3 credentials.")
    except EndpointConnectionError:
        raise RuntimeError(f"❌ Could not connect to S3 endpoint: {S3_URL}")
    except Exception as e:
        raise RuntimeError(f"❌ S3 upload failed: {str(e)}")


# ---- Optional: connectivity test (used by /debug/s3) ----
def check_s3_connection() -> dict:
    try:
        s3.list_buckets()
        return {"status": "ok", "endpoint": S3_URL, "bucket": S3_BUCKET}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
