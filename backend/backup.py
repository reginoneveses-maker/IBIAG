from __future__ import annotations
import gzip, json, os, shutil, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient
import boto3

def now_tag():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def json_default(value):
    if hasattr(value, "isoformat"): return value.isoformat()
    return str(value)

def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("BACKUP_S3_ENDPOINT") or None,
        region_name=os.environ.get("BACKUP_S3_REGION") or None,
        aws_access_key_id=os.environ.get("BACKUP_S3_ACCESS_KEY") or None,
        aws_secret_access_key=os.environ.get("BACKUP_S3_SECRET_KEY") or None,
    )

def create_backup(output_dir):
    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=30000)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"ibiag-mongodb-{now_tag()}.jsonl.gz"
    try:
        client.admin.command("ping")
        db = client[os.environ["DB_NAME"]]
        with gzip.open(archive, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps({"_backup_meta": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "database": db.name,
                "format": "jsonl.gz",
            }}) + "\n")
            for name in sorted(db.list_collection_names()):
                for document in db[name].find({}):
                    fh.write(json.dumps(
                        {"collection": name, "document": document},
                        default=json_default,
                        ensure_ascii=False,
                    ) + "\n")
    finally:
        client.close()
    return archive

def upload_s3(path):
    bucket = os.environ["BACKUP_S3_BUCKET"]
    prefix = os.environ.get("BACKUP_S3_PREFIX", "ibiag/database").strip("/")
    key = f"{prefix}/{path.name}"
    s3_client().upload_file(
        str(path), bucket, key,
        ExtraArgs={"ContentType": "application/gzip"},
    )
    return f"s3://{bucket}/{key}"

def prune_s3():
    keep = max(int(os.environ.get("BACKUP_RETENTION_DAYS", "30")), 1)
    bucket = os.environ["BACKUP_S3_BUCKET"]
    prefix = os.environ.get("BACKUP_S3_PREFIX", "ibiag/database").strip("/") + "/"
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep)
    s3 = s3_client()
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["LastModified"] < cutoff:
                s3.delete_object(Bucket=bucket, Key=obj["Key"])

def main():
    work = Path(tempfile.mkdtemp(prefix="ibiag-backup-"))
    try:
        archive = create_backup(work)
        destination = upload_s3(archive)
        prune_s3()
        print(f"Backup concluído: {destination} ({archive.stat().st_size} bytes)")
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
