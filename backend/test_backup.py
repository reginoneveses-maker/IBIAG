import gzip
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from bson import ObjectId, Int64, json_util
from backup import write_archive, verify_backup, restore_backup, dump_record


class Collection:
    def __init__(self, docs=()): self.docs=list(docs); self.indexes=[]
    def list_indexes(self): return [{"key":{"_id":1},"name":"_id_","v":2}]
    def find(self, query): return iter(self.docs)
    def insert_one(self, doc): self.docs.append(doc)
    def create_index(self, keys, **options): self.indexes.append((keys,options))
    def count_documents(self, query): return len(self.docs)

class Database:
    def __init__(self, name, collections=None): self.name=name; self.collections=collections or {}
    def list_collection_names(self): return list(self.collections)
    def __getitem__(self,name): return self.collections.setdefault(name, Collection())
    def create_collection(self,name): self.collections[name]=Collection()

class Client:
    def __init__(self,db): self.db=db; self.admin=self
    def command(self,c): return {"ok":1}
    def __getitem__(self,name): return self.db
    def close(self): pass

class BackupTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.path=Path(self.work.name)/"backup.jsonl.gz"
        oid=ObjectId()
        self.db=Database("source",{
            "users":Collection([{"_id":ObjectId(),"created_at":datetime(2026,10,2),"n":Int64(2)}]),
            "ibiag_files.files":Collection([{"_id":oid,"filename":"proof.pdf","length":Int64(7),"chunkSize":4}]),
            "ibiag_files.chunks":Collection([{"_id":ObjectId(),"files_id":oid,"n":0,"data":b"\x00\xffAB"},{"_id":ObjectId(),"files_id":oid,"n":1,"data":b"CDE"}]),
            "workflow_locks":Collection([{"_id":"lease","locked_until":"future"}]),
            "empty":Collection(),
        })

    def test_typed_roundtrip_includes_original_file_bytes(self):
        info=write_archive(self.db,self.path)
        self.assertEqual(info["gridfs_files"],1)
        records=[json_util.loads(line) for line in gzip.open(self.path,"rt")]
        docs=[r["document"] for r in records if r.get("collection")=="ibiag_files.chunks"]
        self.assertEqual(b"".join(d["data"] for d in docs),b"\x00\xffABCDE")
        self.assertIsInstance(docs[0]["files_id"],ObjectId)
        users=[r["document"] for r in records if r.get("collection")=="users"]
        self.assertEqual(users,self.db["users"].docs)
        self.assertNotIn("workflow_locks",info["counts"])

    def test_missing_chunk_and_incomplete_manifest_rejected(self):
        self.db["ibiag_files.chunks"].docs.pop()
        with self.assertRaisesRegex(ValueError,"GridFS incompleto"): write_archive(self.db,self.path)
        with gzip.open(self.path,"wt") as fh: fh.write(dump_record({"_backup_meta":{"format":"mongodb-extended-jsonl-v2","database":"source"}})+"\n")
        with self.assertRaisesRegex(ValueError,"incompleto"): verify_backup(self.path)

    def test_dry_run_never_connects_and_source_restore_refused(self):
        write_archive(self.db,self.path)
        with patch("backup.MongoClient") as client:
            self.assertTrue(restore_backup(self.path,"isolated")["dry_run"])
            client.assert_not_called()
            with self.assertRaises(ValueError): restore_backup(self.path,"source",True)

    def test_restore_to_empty_target_preserves_bytes_types_and_empty_collection(self):
        write_archive(self.db,self.path)
        target=Database("isolated")
        with patch("backup.MongoClient",return_value=Client(target)), patch.dict("os.environ",{"RESTORE_MONGO_URL":"mongodb://unused"}):
            result=restore_backup(self.path,"isolated",True)
        self.assertTrue(result["restored"])
        self.assertEqual(target["ibiag_files.chunks"].docs,self.db["ibiag_files.chunks"].docs)
        self.assertEqual(target["users"].docs,self.db["users"].docs)
        self.assertIn("empty",target.collections)
        with patch("backup.MongoClient",return_value=Client(target)), patch.dict("os.environ",{"RESTORE_MONGO_URL":"mongodb://unused"}):
            with self.assertRaisesRegex(ValueError,"vazio"): restore_backup(self.path,"isolated",True)

    def test_old_string_format_refused(self):
        with gzip.open(self.path,"wt") as fh: fh.write('{"_backup_meta":{"format":"jsonl.gz"}}\n')
        with self.assertRaisesRegex(ValueError,"Formato antigo"): verify_backup(self.path)
