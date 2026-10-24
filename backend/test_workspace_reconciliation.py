"""Offline planning and byte-for-byte recovery; no production destination accepted."""
import asyncio
import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
from mongomock_motor import AsyncMongoMockClient
from workspace_reconciliation import (CHUNK, sha, plan_reconciliation, stage_synthetic_archive,
    recover_synthetic_archive, read_manifest_files, main)

def fixture(large=False):
    spec=b"%PDF-synthetic-original-attachment\x00"+(b"x"*(CHUNK*2+21) if large else b"untouched")
    files={"spec:spec1":spec,"crm-file:crm1":b"synthetic commercial attachment","sector-file:sector1":b"synthetic document attachment"}
    source={"format":"exporthub-v1","exportedAt":"2026-10-24T00:00:00.000Z","crmInterchange":"embedded-origins-v1","crmOriginCount":0,
      "documentVersioning":"spec-revisions-v1","products":[{"id":"p","name":"Synthetic ingredient","extraLegacyField":{"keep":True}}],
      "records":[
        {"name":"commercial","revision":9,"updated_at":"2026-10-24","payload":{
          "companies":[{"id":"c","name":"Synthetic Buyer","country":"Portugal","notes":"PRESERVE"}],
          "contacts":[{"id":"person","companyId":"c","name":"Second contact","email":"person@example.test"}],
          "ops":[{"id":"o","companyId":"c","company":"Synthetic Buyer","contactIds":["person"]}],
          "quotes":[{"id":"q","opportunityId":"o","product":"Synthetic ingredient","supplier":"Synthetic Supplier",
                     "quantity":1000,"unitPrice":1.23456789,"total":1234.56789,"currency":"USD","approvedLegacyNote":"DO NOT REPRICE"}],
          "quoteDrafts":[{"id":"draft","kind":"completion","data":{"fields":{"cost":""}}}],
          "interchangeLinks":[],"unknownCommercialField":{"keep":"exactly"}}},
        {"name":"products","revision":2,"payload":[{"id":"p","supplier":"Synthetic Supplier","cost":"17.50","logistics":"LEGACY TEXT"}]},
        {"name":"shipments","revision":3,"payload":[{"id":"ship","quoteId":"q","opportunityId":"o","productId":"p","status":"Pendente"}]},
        {"name":"documents","revision":1,"payload":[{"id":"doc","shipmentId":"ship","type":"Invoice"}]},
        {"name":"tasks","revision":1,"payload":[{"id":"task","opportunityId":"o","recordId":"sector"}]},
        {"name":"sectorRecords","revision":5,"payload":[{"id":"sector","sectorId":"qualidade","productId":"p","shipmentId":"ship","opportunityId":"o","fields":{"custom":"KEEP"},"history":[{"at":"2026-10-01","action":"Created"}]}]},
        {"name":"unknownFutureModule","revision":1,"payload":{"nested":["keep all unknown fields"]}}],
      "specs":[{"id":"spec1","product_id":"p","kind":"original","filename":"original.pdf","size":len(spec)}],
      "crmFiles":[{"id":"crm1","opportunity_id":"o","filename":"commercial.pdf","size":len(files["crm-file:crm1"])}],
      "sectorFiles":[{"id":"sector1","record_id":"sector","filename":"document.pdf","size":len(files["sector-file:sector1"])}],
      "specRevisions":[{"spec_id":"spec1","root_id":"spec1","revision":1,"sha256":sha(spec),"issued_on":"","valid_until":"","change_note":"Original preserved"}],
      "unknownBackupField":{"also":"preserved"}}
    raw=json.dumps(source,ensure_ascii=False,indent=3).encode()
    native={"leads":[{"id":"buyer1","company":"Synthetic Buyer","country":"Portugal","contact_name":"Primary contact KEEP"},
                     {"id":"buyer2","company":"Synthetic Buyer","country":"Portugal"}],
            "products":[{"id":"native-product","name":"Existing ingredient"}],
            "product_offers":[{"id":"native-offer","product_id":"native-product","supplier_price":99}],
            "quotations":[{"id":"native-quote","status":"approved","total_usd":999}]}
    return source,raw,files,native

class ReconciliationPlanTests(unittest.TestCase):
    def test_real_export_shape_preserves_unknown_modules_and_never_autowrites_a_match(self):
        source,raw,files,native=fixture()
        before=copy.deepcopy((source,native,files))
        plan=plan_reconciliation(raw,native,files=files)
        self.assertTrue(plan["canStageSyntheticArchive"])
        self.assertFalse(plan["businessReady"]);self.assertFalse(plan["businessWrites"]);self.assertFalse(plan["identityWrites"])
        self.assertIn("unknownFutureModule",plan["sourceCollections"])
        self.assertEqual(plan["suggestions"][0]["candidates"],["buyer1","buyer2"])
        self.assertFalse(plan["suggestions"][0]["automaticWriteAllowed"])
        self.assertTrue(next(f for f in plan["attachments"] if f["source"]=="spec:spec1")["versionDigestChecked"])
        self.assertFalse(next(f for f in plan["attachments"] if f["source"]=="crm-file:crm1")["versionDigestChecked"])
        self.assertEqual((source,native,files),before)
    def test_checked_in_synthetic_plan_matches_original_fixture_bytes(self):
        root=Path(__file__).resolve().parents[1]/"demo"/"workspace-reconciliation"
        load=lambda name: json.loads((root/name).read_text(encoding="utf-8"))
        files=read_manifest_files(root/"files",load("files-manifest.json"))
        plan=plan_reconciliation((root/"exporthub.json").read_bytes(),load("native-inventory.json"),load("reviewed-links.json"),files)
        self.assertEqual(plan,load("example-plan.json"))

    def test_metadata_export_is_not_a_complete_pdf_package(self):
        _,raw,_,native=fixture()
        plan=plan_reconciliation(raw,native)
        self.assertFalse(plan["canStageSyntheticArchive"])
        self.assertEqual(sum(p["code"]=="missing-private-file" for p in plan["blockers"]),3)
    def test_version_hash_size_and_unindexed_bytes_are_checked(self):
        source,raw,files,native=fixture()
        files["spec:spec1"]=b"z"*len(files["spec:spec1"])
        files["unindexed:x"]=b"unknown"
        plan=plan_reconciliation(raw,native,files=files)
        codes={b["code"] for b in plan["blockers"]}
        self.assertIn("file-version-digest-mismatch",codes);self.assertIn("unindexed-file",codes)
        files["spec:spec1"]=b"short"
        self.assertIn("file-size-mismatch",{b["code"] for b in plan_reconciliation(raw,native,files=files)["blockers"]})
    def test_ambiguous_ids_broken_links_and_duplicate_json_never_become_mappings(self):
        source,_,files,native=fixture()
        source["records"][0]["payload"]["companies"].append(copy.deepcopy(source["records"][0]["payload"]["companies"][0]))
        source["records"][0]["payload"]["contacts"][0]["companyId"]="missing"
        raw=json.dumps(source).encode()
        plan=plan_reconciliation(raw,native,links=[{"source":"company:c","collection":"leads","target":"buyer1"}],files=files)
        codes={b["code"] for b in plan["blockers"]}
        self.assertTrue({"duplicate-source-id","unresolved-source-link","ambiguous-reviewed-source"}<=codes)
        self.assertEqual(plan["reviewedLinks"],[])
        with self.assertRaises(ValueError): plan_reconciliation(b'{"format":"exporthub-v1","format":"other"}')
        with self.assertRaises(ValueError): plan_reconciliation(b'{"format":"exporthub-v1","value":NaN}')
    def test_explicit_mapping_requires_unique_native_target_and_cannot_import_users(self):
        _,raw,files,native=fixture()
        links=[{"source":"company:c","collection":"leads","target":"buyer1"}]
        self.assertEqual(plan_reconciliation(raw,native,links,files)["reviewedLinks"],links)
        native["leads"].append(copy.deepcopy(native["leads"][0]))
        self.assertFalse(plan_reconciliation(raw,native,links,files)["canStageSyntheticArchive"])
        self.assertIn("invalid-reviewed-link",{b["code"] for b in plan_reconciliation(raw,{},[{"source":"company:c","collection":{},"target":"u"}],files)["blockers"]})
        with self.assertRaises(ValueError): plan_reconciliation(raw,{"users":[{"id":"u","role":"admin"}]},files=files)
    def test_revision_and_origin_registry_duplicates_are_reported(self):
        source,_,files,native=fixture()
        source["specRevisions"].append(copy.deepcopy(source["specRevisions"][0]))
        source["crmOriginCount"]=1
        codes={b["code"] for b in plan_reconciliation(json.dumps(source).encode(),native,files=files)["blockers"]}
        self.assertTrue({"invalid-spec-revision-link","duplicate-spec-revision","invalid-crm-origin-registry"}<=codes)
    def test_cli_is_offline_no_overwrite_and_attachment_paths_are_confined(self):
        source,raw,files,native=fixture()
        with tempfile.TemporaryDirectory() as work:
            root=Path(work);folder=root/"files";folder.mkdir()
            backup=root/"export.json";backup.write_bytes(raw)
            attachment_map={}
            for index,(key,value) in enumerate(files.items()):
                name=str(index)+".bin";(folder/name).write_bytes(value);attachment_map[key]=name
            mapping=root/"files.json";mapping.write_text(json.dumps(attachment_map),encoding="utf-8")
            output=root/"plan.json"
            args=["planner","--backup",str(backup),"--files-manifest",str(mapping),"--files-root",str(folder),"--output",str(output)]
            with patch("sys.argv",args): self.assertEqual(main(),0)
            self.assertEqual(backup.read_bytes(),raw)
            with patch("sys.argv",args):
                with self.assertRaises(FileExistsError): main()
            (root/"outside.bin").write_bytes(b"do not read")
            with self.assertRaises(ValueError): read_manifest_files(folder,{"spec:x":"../outside.bin"})
            with self.assertRaises(ValueError): read_manifest_files(folder,{"spec:x":str(root/"outside.bin")})

class ReconciliationArchiveTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    async def asyncSetUp(self):
        self.db_name="ibiag_rehearsal_"+uuid.uuid4().hex
        if self.real_mongo:
            from motor.motor_asyncio import AsyncIOMotorClient
            url=os.environ["TEST_MONGO_URL"]
            if urlparse(url).hostname not in {"localhost","127.0.0.1","mongo"}: raise ValueError("Disposable local Mongo only")
            self.client=AsyncIOMotorClient(url,serverSelectionTimeoutMS=5000)
        else: self.client=AsyncMongoMockClient()
        self.db=self.client[self.db_name]
        await self.db.workspace_rehearsal_control.insert_one({"_id":"synthetic-only","synthetic":True})
        self.source,self.raw,self.files,self.native=fixture(large=True)
        for collection,rows in self.native.items(): await self.db[collection].insert_many(copy.deepcopy(rows))
    async def asyncTearDown(self):
        await self.client.drop_database(self.db_name)
        if self.real_mongo: self.client.close()
    async def native_snapshot(self):
        return {name:await self.db[name].find({},{"_id":0}).to_list(100) for name in self.native}
    async def test_exact_bytes_snapshots_all_modules_and_idempotent_publication(self):
        before=await self.native_snapshot()
        result=await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        self.assertFalse(result["businessReady"])
        restored=await recover_synthetic_archive(self.db,result["archiveId"])
        self.assertEqual(restored["original-export.json"],self.raw)
        for key,value in self.files.items(): self.assertEqual(restored[key],value)
        decoded=json.loads(restored["original-export.json"])
        self.assertEqual(decoded["records"][0]["payload"]["quotes"][0]["total"],1234.56789)
        self.assertEqual(decoded["unknownBackupField"],{"also":"preserved"})
        self.assertEqual(before,await self.native_snapshot())
        count=await self.db.workspace_rehearsal_blobs.count_documents({})
        self.assertEqual(await stage_synthetic_archive(self.db,self.raw,self.files,self.native),result)
        self.assertEqual(await self.db.workspace_rehearsal_blobs.count_documents({}),count)
        self.assertEqual(await self.db.workspace_rehearsal_archives.count_documents({}),1)
    async def test_partial_interruption_never_publishes_and_resume_never_overwrites(self):
        import workspace_reconciliation as module
        original=module.insert_immutable
        attempts=0
        async def interrupt(collection,record):
            nonlocal attempts
            attempts+=1
            if attempts==3: raise OSError("Synthetic interruption")
            return await original(collection,record)
        with patch.object(module,"insert_immutable",interrupt):
            with self.assertRaises(OSError): await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        self.assertEqual(await self.db.workspace_rehearsal_archives.count_documents({}),0)
        self.assertGreater(await self.db.workspace_rehearsal_blobs.count_documents({}),0)
        before=await self.native_snapshot()
        result=await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        self.assertEqual((await recover_synthetic_archive(self.db,result["archiveId"]))["original-export.json"],self.raw)
        self.assertEqual(before,await self.native_snapshot())
    async def test_altered_archive_is_detected_without_automatic_deletion_or_repair(self):
        result=await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        record=await self.db.workspace_rehearsal_blobs.find_one({})
        await self.db.workspace_rehearsal_blobs.update_one({"_id":record["_id"]},{"$set":{"bytes":b"altered"}})
        with self.assertRaises(ValueError): await recover_synthetic_archive(self.db,result["archiveId"])
        with self.assertRaises(ValueError): await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        self.assertEqual((await self.db.workspace_rehearsal_blobs.find_one({"_id":record["_id"]}))["bytes"],b"altered")
        self.assertEqual(await self.db.workspace_rehearsal_archives.count_documents({}),1)
    async def test_storage_budget_is_checked_before_writing_any_chunk(self):
        with patch("workspace_reconciliation.MAX_MANIFEST",1):
            with self.assertRaises(ValueError): await stage_synthetic_archive(self.db,self.raw,self.files,self.native)
        self.assertEqual(await self.db.workspace_rehearsal_blobs.count_documents({}),0)
        self.assertEqual(await self.db.workspace_rehearsal_archives.count_documents({}),0)

    async def test_destination_guard_prevents_any_business_or_identity_write(self):
        other=self.client["production_destination"]
        before=await other.list_collection_names()
        with self.assertRaises(ValueError): await stage_synthetic_archive(other,self.raw,self.files,self.native)
        self.assertEqual(before,await other.list_collection_names())
        unmarked=self.client["ibiag_rehearsal_unmarked_"+uuid.uuid4().hex]
        with self.assertRaises(ValueError): await stage_synthetic_archive(unmarked,self.raw,self.files,self.native)
        self.assertEqual(await unmarked.list_collection_names(),[])
        await self.client.drop_database(unmarked.name)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Requires disposable MongoDB")
class RealMongoReconciliationArchiveTests(ReconciliationArchiveTests):
    real_mongo=True
