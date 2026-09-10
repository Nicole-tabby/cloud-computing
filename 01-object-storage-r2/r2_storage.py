import os
import boto3
from botocore.client import Config

# ---------------------------------------------------------------------------
# Config -- load from environment variables instead of hardcoding secrets
# ---------------------------------------------------------------------------
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "your-account-id")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "your-access-key")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "your-secret-key")
BUCKET_NAME = "nicole-cricket-data-analysis"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",  # R2 uses "auto" instead of an AWS region
)


def upload_file(local_path: str, key: str) -> None:
    s3.upload_file(local_path, BUCKET_NAME, key)
    print(f"[Upload] {local_path} -> r2://{BUCKET_NAME}/{key}")


def download_file(key: str, save_as: str) -> None:
    s3.download_file(BUCKET_NAME, key, save_as)
    print(f"[Download] r2://{BUCKET_NAME}/{key} -> {save_as}")


def list_files() -> None:
    res = s3.list_objects_v2(Bucket=BUCKET_NAME)
    contents = res.get("Contents", [])
    print(f"[List] {len(contents)} file(s) in bucket '{BUCKET_NAME}':")
    for obj in contents:
        print(f"   - {obj['Key']} ({obj['Size']} bytes)")


def delete_file(key: str) -> None:
    s3.delete_object(Bucket=BUCKET_NAME, Key=key)
    print(f"[Delete] r2://{BUCKET_NAME}/{key}")


if __name__ == "__main__":
    upload_file("match1.json", "match1.json")
    upload_file("match2.json", "match2.json")

    list_files()

    download_file("match1.json", "r2_downloaded_match1.json")
