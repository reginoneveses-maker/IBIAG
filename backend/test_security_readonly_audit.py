"""Operational audit reports only booleans/counts and leaves source records intact."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
import security_readonly_audit as audit
import test_account_suspension as fixtures


class ReadOnlyAuditTests(unittest.IsolatedAsyncioTestCase):
    make_database = fixtures.AccountSuspensionTests.make_database
    asyncSetUp = fixtures.AccountSuspensionTests.asyncSetUp
    asyncTearDown = fixtures.AccountSuspensionTests.asyncTearDown
    headers = fixtures.AccountSuspensionTests.headers

    def config(self):
        return {"JWT_SECRET":"synthetic-audit-format-only-32-characters", "CORS_ORIGINS":"https://portal.example",
                "TRUSTED_PROXY_IPS":"127.0.0.1"}

    def authenticated(self, excessive=False):
        return {"authInfo":{"authenticatedUsers":[{"user":"private-canary-account","db":"private-canary-db"}],
                            "authenticatedUserPrivileges":[{"resource":{"db":self.db.name,"collection":""},
                                "actions":["find","update","createUser"] if excessive else ["find","update"]}]}}

    async def snapshot(self):
        return {name:await self.db[name].find({}).to_list(None) for name in await self.db.list_collection_names()}

    async def test_legacy_findings_are_counts_only_without_mutation_or_exfiltration(self):
        await self.db.users.insert_one({"id":"member","email":"MEMBER@example.com","role":"unexpected"})
        await self.db.leads.insert_many([{"id":"missing-owner","company":"private-canary-company"},
                                        {"id":"orphan-owner","owner_id":"absent"}])
        await self.db.tasks.insert_one({"id":"orphan-task","owner_id":"member","lead_id":"absent"})
        await self.db.documents.insert_one({"id":"orphan-doc","lead_id":"absent","file_path":"private-canary-object"})
        before = await self.snapshot()
        with patch.object(self.db,"command",new=AsyncMock(return_value=self.authenticated())):
            result = await audit.collect(self.db,self.config())
        self.assertEqual(await self.snapshot(),before)
        counts = result["finding_counts"]
        for key in ("users_duplicate_id_groups","users_duplicate_email_groups","users_unknown_role","leads_missing_owner",
                    "leads_orphan_owner","tasks_orphan_lead","documents_orphan_lead","documents_missing_gridfs_object"):
            self.assertEqual(counts[key],1,key)
        self.assertFalse(result["automated_checks_passed"])
        self.assertFalse(result["production_certified"])
        self.assertNotIn("private-canary",json.dumps(result))
        self.assertTrue(all(type(value) is int for value in counts.values()))

    async def test_matching_gridfs_objects_and_complete_owner_links_avoid_false_orphans(self):
        await self.db.leads.insert_one({"id":"lead","owner_id":"member"})
        await self.db.tasks.insert_one({"id":"task","owner_id":"member","lead_id":"lead"})
        await self.db.documents.insert_one({"id":"doc","lead_id":"lead","file_path":"fixture/object"})
        await self.db["ibiag_files.files"].insert_one({"filename":"fixture/object"})
        with patch.object(self.db,"command",new=AsyncMock(return_value=self.authenticated())):
            result = await audit.collect(self.db,self.config())
        self.assertTrue(result["automated_checks_passed"],result)
        self.assertFalse(result["production_certified"])
        self.assertTrue(result["manual_evidence_required"])

    async def test_unauthenticated_or_excessive_privileges_never_pass(self):
        for status in ({"authInfo":{}},self.authenticated(True),{"authInfo":{"authenticatedUsers":[{"user":"private-canary"}]}}):
            with patch.object(self.db,"command",new=AsyncMock(return_value=status)):
                result = await audit.collect(self.db,self.config())
            self.assertFalse(result["automated_checks_passed"])
            self.assertNotIn("private-canary",json.dumps(result))

    async def test_unknown_privilege_and_failed_query_are_not_reported_as_safe(self):
        with patch.object(self.db,"command",new=AsyncMock(side_effect=RuntimeError("private-canary-uri"))), \
             patch.object(type(self.db.users),"aggregate",side_effect=RuntimeError("private-canary-query")):
            result = await audit.collect(self.db,self.config())
        self.assertFalse(result["authentication"]["query_completed"])
        self.assertIn("users_identity",result["incomplete_checks"])
        self.assertFalse(result["automated_checks_passed"])
        self.assertNotIn("private-canary",json.dumps(result))

    async def test_s3_audit_does_not_contact_provider_or_assume_storage_private(self):
        with patch.object(self.db,"command",new=AsyncMock(return_value=self.authenticated())):
            result = await audit.collect(self.db,{**self.config(),"STORAGE_PROVIDER":"s3"})
        self.assertNotIn("documents_missing_gridfs_object",result["finding_counts"])
        self.assertFalse(result["production_certified"])
        self.assertIn("effective_storage_privacy_and_object_reference_coverage",result["manual_evidence_required"])


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class ReadOnlyAuditMongoTests(ReadOnlyAuditTests):
    make_database = fixtures.AccountSuspensionMongoTests.make_database
    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()


class AuditConfigurationTests(unittest.TestCase):
    def test_unsafe_flags_origins_secrets_and_proxy_fail_without_returning_values(self):
        result = audit.configuration_checks({"ALLOW_PUBLIC_REGISTRATION":"true", "ALLOW_PAID_DISCOVERY":"true",
                                            "ENABLE_API_DOCS":"true", "CORS_ORIGINS":"https://*.private-canary.example",
                                            "JWT_SECRET":"private-canary", "TRUSTED_PROXY_IPS":"*"})
        self.assertFalse(any(result.values()))
        self.assertNotIn("private-canary",json.dumps(result))
        self.assertFalse(audit.configuration_checks({})["proxy_trust_configured"])

    def test_cli_connection_failure_never_exposes_uri_or_exception(self):
        out,err=io.StringIO(),io.StringIO()
        with patch.object(audit,"execute",new=AsyncMock(side_effect=RuntimeError("private-canary-uri"))),redirect_stdout(out),redirect_stderr(err):
            code = audit.main()
        self.assertEqual(code,2)
        self.assertNotIn("private-canary",out.getvalue()+err.getvalue())
        self.assertFalse(json.loads(err.getvalue())["audit_completed"])
