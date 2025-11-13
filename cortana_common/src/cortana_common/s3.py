"""S3 client utilities for object storage access."""

import logging
from typing import Optional
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from cortana_common.config import get_settings

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client wrapper with helper methods."""

    def __init__(self):
        """Initialize S3 client from settings."""
        settings = get_settings()
        
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        logger.info(f"S3 client initialized for bucket: {self.bucket}")

    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to S3.
        
        Args:
            file_path: Local file path to upload.
            s3_key: S3 object key (path in bucket).
            content_type: Optional content type (e.g., 'video/mp4').
            
        Returns:
            S3 key of uploaded object.
            
        Raises:
            ClientError: If upload fails.
        """
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
            
        try:
            self.client.upload_file(
                file_path,
                self.bucket,
                s3_key,
                ExtraArgs=extra_args if extra_args else None,
            )
            logger.info(f"Uploaded {file_path} to s3://{self.bucket}/{s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            raise

    def download_file(self, s3_key: str, local_path: str) -> str:
        """Download a file from S3.
        
        Args:
            s3_key: S3 object key to download.
            local_path: Local file path to save to.
            
        Returns:
            Local file path.
            
        Raises:
            ClientError: If download fails.
        """
        try:
            self.client.download_file(self.bucket, s3_key, local_path)
            logger.info(f"Downloaded s3://{self.bucket}/{s3_key} to {local_path}")
            return local_path
        except ClientError as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 900,  # 15 minutes
        http_method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access.
        
        Args:
            s3_key: S3 object key.
            expiration: URL expiration time in seconds (default: 15 minutes).
            http_method: HTTP method (GET, PUT, etc.).
            
        Returns:
            Presigned URL string.
            
        Raises:
            ClientError: If URL generation fails.
        """
        try:
            method_map = {
                "GET": "get_object",
                "PUT": "put_object",
            }
            
            url = self.client.generate_presigned_url(
                method_map.get(http_method, "get_object"),
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
            logger.debug(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

    def object_exists(self, s3_key: str) -> bool:
        """Check if an object exists in S3.
        
        Args:
            s3_key: S3 object key to check.
            
        Returns:
            True if object exists, False otherwise.
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking object existence for {s3_key}: {e}")
            raise

    def delete_object(self, s3_key: str) -> None:
        """Delete an object from S3.
        
        Args:
            s3_key: S3 object key to delete.
            
        Raises:
            ClientError: If deletion fails.
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted s3://{self.bucket}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to delete {s3_key}: {e}")
            raise

    def list_objects(self, prefix: str, max_keys: int = 1000) -> list[str]:
        """List objects with a given prefix.
        
        Args:
            prefix: S3 key prefix to filter by.
            max_keys: Maximum number of keys to return.
            
        Returns:
            List of S3 object keys.
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            
            if "Contents" not in response:
                return []
                
            keys = [obj["Key"] for obj in response["Contents"]]
            logger.debug(f"Listed {len(keys)} objects with prefix: {prefix}")
            return keys
        except ClientError as e:
            logger.error(f"Failed to list objects with prefix {prefix}: {e}")
            raise


@lru_cache
def get_s3_client() -> S3Client:
    """Get cached S3 client instance.
    
    Returns:
        S3Client: Cached S3 client object.
    """
    return S3Client()
