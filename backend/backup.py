"""Typed MongoDB backups, including GridFS bytes, and non-destructive restore."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import math
import os
import shutil
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bson import json_util
from pymongo import MongoClient
import boto3

FORMAT = "mongodb-extended-jsonl-v2"

def now_tag():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def required(name):
    value = os.environ.get(name, "").strip()
    if not value: raise RuntimeError(f"Configuração obrigatória ausente: {name}")
    return value

def s3_client():
    return boto3.client("s3", endpoint_url=os.environ.get("BACKUP_S3_ENDPOINT") or None,
        region_name=os.environ.get("BACKUP_S3_REGION") or None,
        aws_access_key_id=required("BACKUP_S3_ACCESS_KEY"),
        aws_secret_access_key=required("BACKUP_S3_SECRET_KEY"))

def dump_record(record):
    return json_util.dumps(record, json_options=json_util.CANONICAL_JSON_OPTIONS, ensure_ascii=False)

def write_archive(db, archive):
    """Preserve BSON ObjectId, dates and binary data; old str(value) broke GridFS."""
    counts = Counter()
    names = sorted(name for name in db.list_collection_names() if name != "workflow_locks" and not name.startswith("system."))
    indexes = {name: list(db[name].list_indexes()) for name in names}
    with gzip.open(archive, "wt", encoding="utf-8") as fh:
        fh.write(dump_record({"_backup_meta": {"created_at": datetime.now(timezone.utc), "database": db.name,
                                               "format": FORMAT, "indexes": indexes}})+"\n")
        for name in names:
            for document in db[name].find({}):
                fh.write(dump_record({"collection": name, "document": document})+"\n")
                counts[name] += 1
        fh.write(dump_record({"_backup_manifest": {"counts": dict(counts), "complete": True}})+"\n")
    return verify_backup(archive)

def verify_backup(archive):
    counts = Counter()
    files = {}
    chunks = defaultdict(dict)
    meta = manifest = None
    with gzip.open(archive, "rt", encoding="utf-8") as fh:
        for line in fh:
            record = json_util.loads(line)
            if "_backup_meta" in record:
                if meta is not None: raise ValueError("Metadados de backup duplicados")
                meta = record["_backup_meta"]
                if meta.get("format") != FORMAT: raise ValueError("Formato antigo não garante restauração de BSON/GridFS")
                continue
            if "_backup_manifest" in record:
                if manifest is not None: raise ValueError("Manifesto de backup duplicado")
                manifest = record["_backup_manifest"]
                continue
            if not meta or manifest: raise ValueError("Estrutura do backup inválida")
            name, doc = record["collection"], record["document"]
            counts[name] += 1
            if name.endswith(".files") and "length" in doc and "chunkSize" in doc:
                files[(name[:-6], doc["_id"])] = (int(doc["length"]), int(doc["chunkSize"]))
            if name.endswith(".chunks") and "files_id" in doc:
                if not isinstance(doc.get("data"), bytes): raise ValueError("Bloco de arquivo sem bytes restauráveis")
                key = (name[:-7], doc["files_id"])
                if doc["n"] in chunks[key]: raise ValueError("Bloco de arquivo duplicado")
                chunks[key][int(doc["n"])] = len(doc["data"])
    if not meta or not manifest or not manifest.get("complete") or dict(counts) != manifest.get("counts"):
        raise ValueError("Backup incompleto ou contagens divergentes")
    for key, (length, chunk_size) in files.items():
        parts = chunks.get(key, {})
        if chunk_size <= 0 or sorted(parts) != list(range(math.ceil(length/chunk_size))) or sum(parts.values()) != length:
            raise ValueError("Arquivo GridFS incompleto")
    if any(key not in files for key in chunks): raise ValueError("Blocos de arquivo sem metadados")
    return {"format": FORMAT, "database": meta["database"], "counts": dict(counts), "gridfs_files": len(files)}

def create_backup(output_dir):
    client = MongoClient(required("MONGO_URL"), serverSelectionTimeoutMS=30000)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    archive = out / f"ibiag-mongodb-{now_tag()}-{uuid.uuid4().hex[:8]}.jsonl.gz"
    try:
        client.admin.command("ping")
        write_archive(client[required("DB_NAME")], archive)
    finally:
        client.close()
    return archive

def restore_backup(archive, target_name, execute=False):
    info = verify_backup(archive)
    if not target_name or target_name == info["database"] or target_name == os.environ.get("DB_NAME"):
        raise ValueError("Escolha um banco de recuperação diferente do banco de origem")
    if not execute: return {**info, "target_database": target_name, "dry_run": True}
    client = MongoClient(required("RESTORE_MONGO_URL"), serverSelectionTimeoutMS=30000)
    try:
        client.admin.command("ping")
        target = client[target_name]
        if target.list_collection_names(): raise ValueError("O banco de recuperação deve estar vazio; nenhum dado será apagado")
        indexes = {}
        with gzip.open(archive, "rt", encoding="utf-8") as fh:
            for line in fh:
                record = json_util.loads(line)
                if "_backup_meta" in record:
                    indexes = record["_backup_meta"].get("indexes", {})
                elif "collection" in record:
                    target[record["collection"]].insert_one(record["document"])
        for name, specs in indexes.items():
            # Preserve empty collections and their indexes as well.
            if name not in target.list_collection_names(): target.create_collection(name)
            for spec in specs:
                if spec.get("name") == "_id_": continue
                options = {key: value for key, value in spec.items() if key not in {"key", "v", "ns", "background"}}
                target[name].create_index(list(spec["key"].items()), **options)
        for name, count in info["counts"].items():
            if target[name].count_documents({}) != count: raise ValueError("Contagem restaurada divergente")
        return {**info, "target_database": target_name, "restored": True}
    finally:
        client.close()

def upload_s3(path):
    bucket = required("BACKUP_S3_BUCKET")
    prefix = (os.environ.get("BACKUP_S3_PREFIX") or "ibiag/database").strip("/")
    key = f"{prefix}/{path.name}"
    with path.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    s3 = s3_client()
    s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "application/gzip", "Metadata": {"sha256": digest, "backup-format": FORMAT}})
    head = s3.head_object(Bucket=bucket, Key=key)
    if head["ContentLength"] != path.stat().st_size or head.get("Metadata", {}).get("sha256") != digest:
        raise RuntimeError("Arquivo remoto de backup não passou na verificação")
    return f"s3://{bucket}/{key}"

def prune_s3():
    """Retention deletion is explicitly enabled; creating a backup never requires it."""
    if os.environ.get("BACKUP_PRUNE_ENABLED", "false").lower() != "true": return
    keep = max(int(os.environ.get("BACKUP_RETENTION_DAYS") or "30"), 1)
    bucket = required("BACKUP_S3_BUCKET")
    prefix = (os.environ.get("BACKUP_S3_PREFIX") or "ibiag/database").strip("/") + "/"
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep)
    s3 = s3_client()
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["LastModified"] < cutoff: s3.delete_object(Bucket=bucket, Key=obj["Key"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--target-db")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(verify_backup(args.verify)); return
    if args.restore:
        print(restore_backup(args.restore, args.target_db, args.execute)); return
    work = Path(tempfile.mkdtemp(prefix="ibiag-backup-"))
    try:
        archive = create_backup(work)
        destination = upload_s3(archive)
        prune_s3()
        print(f"Backup verificado e enviado: {destination} ({archive.stat().st_size} bytes)")
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__": main()
