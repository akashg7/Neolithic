"""
S3-compatible file upload/download utility.
Uses boto3 with MinIO locally, AWS S3 in production.
"""
import asyncio
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    """Create an S3 client configured for MinIO (local) or AWS S3 (prod)."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4", connect_timeout=2, read_timeout=5),
        region_name="us-east-1",
    )


def _upload_sync(file_bytes: bytes, key: str, content_type: str) -> str:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.S3_BUCKET)
        except ClientError:
            pass
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"


def _download_sync(key: str) -> bytes | None:
    client = get_s3_client()
    try:
        obj = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        return obj["Body"].read()
    except Exception:
        return None


async def upload_file(file_bytes: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Upload a file to S3/MinIO and return its object URL."""
    return await asyncio.to_thread(_upload_sync, file_bytes, key, content_type)


async def download_file(key: str) -> bytes | None:
    """Fetch raw bytes for a stored S3/MinIO key, returning None if absent/unreachable."""
    return await asyncio.to_thread(_download_sync, key)


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading a file."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
