import os
import unittest
from unittest.mock import patch
from pydantic import ValidationError
import httpx
from mongomock_motor import AsyncMongoMockClient
from password_inputs import password_bytes

with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"password_test",
                             "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class PasswordValidationTests(unittest.TestCase):
    def test_byte_limit_including_multibyte_characters(self):
        for value in ("a"*72,"é"*36):
            self.assertEqual(len(password_bytes(value)),72)
            self.assertEqual(server.LoginBody(email="u@example.com",password=value).password,value)
        for value in ("a"*73,"é"*37,"a\x00b",""):
            with self.subTest(length=len(value)),self.assertRaises(ValidationError):
                server.LoginBody(email="u@example.com",password=value)

    def test_registration_paths_share_minimum_and_preserve_legacy_login(self):
        for model in (server.RegisterBody,server.UserCreateBody):
            with self.assertRaises(ValidationError): model(email="u@example.com",password="short")
            self.assertEqual(model(email="u@example.com",password="eight123").password,"eight123")
        self.assertEqual(server.LoginBody(email="u@example.com",password="short").password,"short")

    def test_hash_and_verification_never_truncate(self):
        value="a"*72
        hashed=server.hash_pw(value)
        self.assertTrue(server.verify_pw(value,hashed))
        self.assertFalse(server.verify_pw(value+"different-suffix",hashed))
        with self.assertRaises(ValueError): server.hash_pw(value+"suffix")
        with self.assertRaises(ValueError): server.hash_pw("short")
        self.assertFalse(server.verify_pw("invalid\x00password",hashed))

    def test_password_is_not_normalized(self):
        password="  eight123  "
        self.assertEqual(server.RegisterBody(email="u@example.com",password=password).password,password)
        self.assertFalse(server.verify_pw(password.strip(),server.hash_pw(password)))


class PasswordHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=AsyncMongoMockClient()["isolated"]
        await self.db.users.insert_one({"id":"admin","email":"admin@example.com","role":"admin"})
        self.db_patch=patch.object(server,"db",self.db)
        self.db_patch.start()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()

    async def test_invalid_auth_inputs_are_redacted_before_hashing_or_writes(self):
        token=server.create_token("admin","admin@example.com")
        canary="private-password-canary-"+"a"*72
        with patch.dict(os.environ,{"ALLOW_PUBLIC_REGISTRATION":"true"}), \
             patch.object(server,"hash_pw",side_effect=AssertionError("must not hash invalid inputs")):
            for path in ("/api/auth/login","/api/auth/register","/api/auth/users"):
                response=await self.client.post(path,headers={"Authorization":"Bearer "+token},
                                               json={"email":"new@example.com","password":canary})
                self.assertEqual(response.status_code,422,response.text)
                self.assertNotIn(canary,response.text)
                self.assertEqual(response.json(),{"detail":"Dados de autenticação inválidos."})
                self.assertEqual(response.headers["cache-control"],"no-store")
        self.assertEqual(await self.db.users.count_documents({}),1)
        self.assertEqual(await self.db.login_attempts.count_documents({}),0)

    async def test_valid_account_creation_and_login_still_work(self):
        token=server.create_token("admin","admin@example.com")
        created=await self.client.post("/api/auth/users",headers={"Authorization":"Bearer "+token},
                                       json={"email":"new@example.com","password":"valid-password"})
        self.assertEqual(created.status_code,200,created.text)
        self.assertNotIn("password_hash",created.json())
        response=await self.client.post("/api/auth/login",json={"email":"new@example.com","password":"valid-password"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertIn("access_token",response.json())

    async def test_existing_short_password_can_login_without_forcing_a_reset(self):
        # Existing bcrypt hashes remain usable; new registrations require 8 chars.
        hashed=server.bcrypt.hashpw(b"short",server.bcrypt.gensalt()).decode()
        await self.db.users.insert_one({"id":"legacy","email":"legacy@example.com","role":"user","password_hash":hashed})
        response=await self.client.post("/api/auth/login",json={"email":"legacy@example.com","password":"short"})
        self.assertEqual(response.status_code,200,response.text)
