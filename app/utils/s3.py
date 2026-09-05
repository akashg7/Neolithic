"""
S3-compatible file upload/download utility.
Uses boto3 with MinIO locally, AWS S3 in production.
"""
import boto3
from botocore.config import Config as BotoConfig

from app.config import settings


def get_s3_client():
    """Create an S3 client configured for MinIO (local) or AWS S3 (prod)."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


async def upload_file(file_bytes: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Upload a file to S3 and return the URL."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading a file."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
