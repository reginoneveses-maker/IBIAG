"""Recovery changes only its target, invalidates sessions and never exposes inputs."""
import asyncio
from contextlib import redirect_stdout, redirect_stderr
import io
import os
from types import SimpleNamespace
import unittest
import warnings
from pymongo.write_concern import WriteConcern
from unittest.mock import patch, AsyncMock, MagicMock
import recover_access as recovery
import test_account_suspension as fixtures


class AccessRecoveryTests(unittest.IsolatedAsyncioTestCase):
    make_database = fixtures.AccountSuspensionTests.make_database
    asyncSetUp = fixtures.AccountSuspensionTests.asyncSetUp
    asyncTearDown = fixtures.AccountSuspensionTests.asyncTearDown
    headers = fixtures.AccountSuspensionTests.headers

    async def target(self, uid="member", role="user"):
        return await recovery.recovery_target(self.db, uid, role, "lost-password", "CASE-TEST")

    async def apply(self, record, password="recovered-test-password", role="user"):
        return await recovery.recover(self.db, record, password, role, "lost-password", "CASE-TEST")

    async def test_recovery_revokes_old_sessions_without_changing_role_or_business_data(self):
        await self.db.leads.insert_one({"id":"keep", "owner_id":"member"})
        other = await self.db.users.find_one({"id":"admin"})
        record = await self.target()
        await self.apply(record)
        self.assertEqual((await self.client.get("/api/auth/me",headers=self.member)).status_code,401)
        self.assertEqual((await self.client.get("/api/auth/me",headers=self.admin)).status_code,200)
        for password, status in (("valid-test-password",401),("recovered-test-password",200)):
            response = await self.client.post("/api/auth/login",json={"email":"member@example.com","password":password})
            self.assertEqual(response.status_code,status)
        after = await self.db.users.find_one({"id":"member"})
        self.assertEqual(after["role"],"user")
        self.assertEqual(after["session_version"],1)
        self.assertEqual(after["access_recovery_audit"][0]["case_id"],"CASE-TEST")
        self.assertEqual(set(after["access_recovery_audit"][0]),{"id","at","actor","reason","case_id"})
        self.assertNotIn("recovered-test-password",str(after["access_recovery_audit"]))
        self.assertEqual(await self.db.users.find_one({"id":"admin"}),other)
        self.assertEqual(await self.db.leads.count_documents({"id":"keep","owner_id":"member"}),1)

    async def test_admin_emergency_preserves_admin_and_revokes_tokens(self):
        await self.db.users.update_one({"id":"admin"},{"$set":{"password_hash":fixtures.server.hash_pw("synthetic-old-admin")}})
        record = await recovery.recovery_target(self.db,"admin","admin","admin-emergency","CASE-ADMIN")
        await recovery.recover(self.db,record,"synthetic-new-admin","admin","admin-emergency","CASE-ADMIN")
        self.assertEqual((await self.client.get("/api/auth/me",headers=self.admin)).status_code,401)
        after = await self.db.users.find_one({"id":"admin"})
        self.assertEqual(after["role"],"admin")
        self.assertTrue(fixtures.server.verify_pw("synthetic-new-admin",after["password_hash"]))

    async def test_suspended_wrong_role_missing_and_duplicate_identity_are_refused(self):
        before = await self.db.users.find_one({"id":"member"})
        for uid, role in (("missing","user"),("member","admin"),("admin","user")):
            with self.assertRaises(recovery.RecoveryRefused): await self.target(uid,role)
        await self.db.users.update_one({"id":"member"},{"$set":{"active":False}})
        with self.assertRaises(recovery.RecoveryRefused): await self.target()
        await self.db.users.update_one({"id":"member"},{"$unset":{"active":""}})
        duplicate = {**before};duplicate.pop("_id")
        await self.db.users.insert_one(duplicate)
        with self.assertRaises(recovery.RecoveryRefused): await self.target()
        await self.db.users.delete_one({"_id":before["_id"]})
        await self.db.users.insert_one({"id":"duplicate-email","email":"member@example.com"})
        with self.assertRaises(recovery.RecoveryRefused): await self.target()

    async def test_password_policy_and_same_password_refused_without_mutation(self):
        record = await self.target()
        for password in ("short", "a"*73, "é"*37, "a\0long-value", "valid-test-password", 42, "\ud800abcdefgh"):
            with self.assertRaises(recovery.RecoveryRefused): await self.apply(record,password)
        self.assertEqual(await self.db.users.find_one({"id":"member"}),record)

    async def test_stale_recovery_cannot_override_rotation_suspension_or_identity_change(self):
        record = await self.target()
        for change in ({"session_version":1},{"active":False},{"role":"admin"},{"email":"changed@example.com"}):
            await self.db.users.update_one({"_id":record["_id"]},{"$set":change})
            with self.assertRaises(recovery.RecoveryRefused): await self.apply(record)
            await self.db.users.replace_one({"_id":record["_id"]},record)
        await self.db.users.update_one({"_id":record["_id"]},{"$set":{"password_hash":fixtures.server.hash_pw("other-password-test")}})
        with self.assertRaises(recovery.RecoveryRefused): await self.apply(record)

    async def test_competing_recoveries_have_only_one_winner_and_one_atomic_audit_event(self):
        record = await self.target()
        results = await asyncio.gather(self.apply(record,"synthetic-first-password"),self.apply(record,"synthetic-second-password"),return_exceptions=True)
        self.assertEqual(sum(result is None for result in results),1)
        self.assertTrue(any(isinstance(result,recovery.RecoveryRefused) for result in results))
        after = await self.db.users.find_one({"id":"member"})
        self.assertEqual(after["session_version"],1)
        self.assertEqual(len(after["access_recovery_audit"]),1)

    async def test_malformed_generation_or_full_audit_refused_without_deleting_history(self):
        for fields in ({"session_version":True},{"session_version":-1},{"access_recovery_audit":"invalid"},
                       {"access_recovery_audit":[{"id":str(i)} for i in range(100)]}):
            await self.db.users.update_one({"id":"member"},{"$set":fields})
            with self.assertRaises(recovery.RecoveryRefused): await self.target()
            await self.db.users.update_one({"id":"member"},{"$unset":{key:"" for key in fields}})


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class AccessRecoveryMongoTests(AccessRecoveryTests):
    def make_database(self):
        database = fixtures.AccountSuspensionMongoTests.make_database(self)
        return database.with_options(write_concern=WriteConcern(w="majority", j=True))

    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()


class RecoveryCommandTests(unittest.TestCase):
    def args(self, apply=False):
        return SimpleNamespace(account_id="member", expected_role="user", reason="lost-password",case_id="CASE-TEST",apply=apply)

    def test_apply_requires_tty_before_connecting_or_prompting(self):
        with patch.object(recovery.sys.stdin,"isatty",return_value=False),patch.object(recovery,"AsyncIOMotorClient") as connect:
            with self.assertRaises(recovery.RecoveryRefused): asyncio.run(recovery.execute(self.args(True)))
        connect.assert_not_called()

    def test_invalid_requests_rejected_without_db_and_cli_errors_hide_secrets(self):
        for values in (("$ne","user","lost-password","CASE"),("member","user","admin-emergency","CASE"),
                       ("member","user","lost-password","secret with spaces")):
            with self.assertRaises(recovery.RecoveryRefused): recovery.validate_request(*values)
        out,err=io.StringIO(),io.StringIO()
        with patch.object(recovery,"execute",side_effect=RuntimeError("credential-canary-private")),redirect_stdout(out),redirect_stderr(err):
            code = recovery.main(["--account-id","member","--expected-role","user","--reason","lost-password","--case-id","CASE"])
        self.assertEqual(code,1)
        self.assertNotIn("credential-canary-private",out.getvalue()+err.getvalue())
        self.assertNotIn("Traceback",err.getvalue())

    def test_dry_run_closes_client_without_prompt_or_write(self):
        connection=MagicMock()
        with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"recovery_test"}), \
             patch.object(recovery,"AsyncIOMotorClient",return_value=connection), \
             patch.object(recovery,"recovery_target",new_callable=AsyncMock,return_value={"id":"member"}), \
             patch.object(recovery,"recover",new_callable=AsyncMock) as apply, \
             patch("builtins.input") as confirm, patch.object(recovery.getpass,"getpass") as password,redirect_stdout(io.StringIO()):
            asyncio.run(recovery.execute(self.args()))
        confirm.assert_not_called();password.assert_not_called();apply.assert_not_called();connection.close.assert_called_once()

    def test_apply_confirmation_and_secret_confirmation_precede_single_write(self):
        for confirm_value, passwords, expected in (("WRONG",[],False),("RECUPERAR member",["synthetic-new-one","synthetic-new-two"],False),
                                                   ("RECUPERAR member",["synthetic-new-one","synthetic-new-one"],True)):
            connection=MagicMock();out=io.StringIO()
            with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"recovery_test"}), \
                 patch.object(recovery,"AsyncIOMotorClient",return_value=connection), \
                 patch.object(recovery,"recovery_target",new_callable=AsyncMock,return_value={"id":"member"}), \
                 patch.object(recovery,"recover",new_callable=AsyncMock) as apply, \
                 patch("builtins.input",return_value=confirm_value), patch.object(recovery.getpass,"getpass",side_effect=passwords), \
                 patch.object(recovery.sys.stdin,"isatty",return_value=True), \
                 patch.object(recovery.sys.stderr,"isatty",return_value=True),redirect_stdout(out):
                with patch.object(out,"isatty",return_value=True):
                    if expected: asyncio.run(recovery.execute(self.args(True)))
                    else:
                        with self.assertRaises(recovery.RecoveryRefused): asyncio.run(recovery.execute(self.args(True)))
            self.assertEqual(apply.await_count,1 if expected else 0)
            self.assertNotIn("synthetic-new-one",out.getvalue())
            connection.close.assert_called_once()

    def test_unknown_cli_option_never_echoes_its_value(self):
        err=io.StringIO()
        with redirect_stderr(err),self.assertRaises(SystemExit):
            recovery.main(["--password","credential-canary-private"])
        self.assertNotIn("credential-canary-private",err.getvalue())

    def test_getpass_echo_warning_aborts_without_reading_or_writing_secret(self):
        connection=MagicMock();out=io.StringIO();echo_read=MagicMock()
        def unsafe_fallback(*args):
            warnings.warn("echo disabled",recovery.getpass.GetPassWarning)
            return echo_read()
        with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"recovery_test"}), \
             patch.object(recovery,"AsyncIOMotorClient",return_value=connection), \
             patch.object(recovery,"recovery_target",new_callable=AsyncMock,return_value={"id":"member"}), \
             patch.object(recovery,"recover",new_callable=AsyncMock) as apply, \
             patch("builtins.input",return_value="RECUPERAR member"), \
             patch.object(recovery.getpass,"getpass",side_effect=unsafe_fallback), \
             patch.object(recovery.sys.stdin,"isatty",return_value=True), \
             patch.object(recovery.sys.stderr,"isatty",return_value=True),redirect_stdout(out):
            with patch.object(out,"isatty",return_value=True),self.assertRaises(recovery.getpass.GetPassWarning):
                asyncio.run(recovery.execute(self.args(True)))
        apply.assert_not_called();connection.close.assert_called_once();echo_read.assert_not_called()
