import asyncio
import logging
import os
import boto3
from botocore.client import Config

# Add parent directory to path to import config if run directly
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (  # noqa: E402
    HF_S3_ENDPOINT, HF_ACCESS_KEY_ID, HF_SECRET_ACCESS_KEY, HF_BUCKET_NAME
)

logger = logging.getLogger(__name__)


def _get_s3_client():
    if not all([HF_ACCESS_KEY_ID, HF_SECRET_ACCESS_KEY]):
        logger.warning("HF S3 credentials are not configured in environment variables.")
        return None

    # Connect to Hugging Face or standard S3 endpoint
    return boto3.client(
        "s3",
        endpoint_url=HF_S3_ENDPOINT,
        aws_access_key_id=HF_ACCESS_KEY_ID,
        aws_secret_access_key=HF_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4")
    )


def upload_file_to_s3_sync(local_file_path: str, s3_key: str) -> str:
    """Synchronously uploads a file to S3 and returns the public URL or S3 key if successful."""
    client = _get_s3_client()
    if not client:
        return ""

    if not os.path.exists(local_file_path):
        logger.error(f"Local file not found: {local_file_path}")
        return ""

    try:
        logger.info(f"Uploading {local_file_path} to HF bucket '{HF_BUCKET_NAME}' key '{s3_key}'...")
        client.upload_file(
            Filename=local_file_path,
            Bucket=HF_BUCKET_NAME,
            Key=s3_key
        )
        logger.info("Upload completed successfully.")
        # Construct public URL (this depends on endpoint but a standard key reference works)
        return f"{HF_S3_ENDPOINT}/{HF_BUCKET_NAME}/{s3_key}"
    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}")
        return ""


async def upload_file_to_s3(local_file_path: str, s3_key: str) -> str:
    """Asynchronously uploads a file to S3 by running in a separate executor thread."""
    return await asyncio.to_thread(upload_file_to_s3_sync, local_file_path, s3_key)


if __name__ == "__main__":
    # Test upload if run as a script
    logging.basicConfig(level=logging.INFO)
    print("Testing S3 Storage Connection...")
    # Create a dummy file
    test_file = "test_s3.txt"
    with open(test_file, "w") as f:
        f.write("Hello UZSL S3 Storage")

    loop = asyncio.get_event_loop()
    url = loop.run_until_complete(upload_file_to_s3(test_file, "test/test_s3.txt"))
    print(f"Result URL: {url}")

    if os.path.exists(test_file):
        os.remove(test_file)
