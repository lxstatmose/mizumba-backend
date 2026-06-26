from pathlib import Path

from app.common.exceptions import bad_request
from app.core.config import get_settings


def upload_to_cloud_if_configured(*, local_path: Path, folder: str, stored_filename: str, mime_type: str) -> str | None:
    settings = get_settings()
    provider = settings.storage_provider.lower()
    if provider == "local":
        return None
    if provider == "s3":
        return _upload_to_s3(local_path=local_path, folder=folder, stored_filename=stored_filename, mime_type=mime_type)
    if provider == "cloudinary":
        return _upload_to_cloudinary(local_path=local_path, folder=folder)
    raise bad_request("Unsupported storage provider")


def _upload_to_s3(*, local_path: Path, folder: str, stored_filename: str, mime_type: str) -> str:
    settings = get_settings()
    if not settings.s3_bucket or not settings.s3_region:
        raise bad_request("S3 storage is not configured")

    import boto3

    client = boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    key = f"{folder}/{stored_filename}"
    client.upload_file(
        str(local_path),
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": mime_type},
    )
    return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"


def _upload_to_cloudinary(*, local_path: Path, folder: str) -> str:
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise bad_request("Cloudinary storage is not configured")

    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    result = cloudinary.uploader.upload(str(local_path), folder=f"mizumba/{folder}", resource_type="auto")
    return result["secure_url"]
