"""Disposable Compose integration test. Never connects to Railway or real data."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8787"
PROJECT = "ibiag-local-ci-" + secrets.token_hex(5)


def main():
    with tempfile.TemporaryDirectory(prefix="ibiag-local-test-") as temporary:
        env_file = Path(temporary) / ".env.local"
        env_file.write_text(
            "LOCAL_MONGO_ROOT_PASSWORD=" + secrets.token_hex(32) + "\n"
            "LOCAL_DB_PASSWORD=" + secrets.token_hex(32) + "\n"
            "LOCAL_JWT_SECRET=" + secrets.token_hex(32) + "\n", encoding="ascii")
        compose = ["docker", "compose", "-p", PROJECT, "--project-directory", str(ROOT),
                   "--env-file", str(env_file), "-f", str(ROOT / "compose.local.yaml")]

        def run(*args, stdin=None):
            result = subprocess.run(compose + list(args), input=stdin, text=True,
                                    capture_output=True, timeout=1200)
            if result.returncode:
                # Do not dump rendered config, environment, Mongo URL or secrets.
                raise RuntimeError("Local CI command failed: " + args[0])
            return result.stdout

        def request(path, token="", body=None, method=None, content_type="application/json"):
            headers = {"Content-Type": content_type}
            if token:
                headers["Authorization"] = "Bearer " + token
            payload = json.dumps(body).encode() if isinstance(body, dict) else body
            req = urllib.request.Request(URL + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return response.status, response.read(), response.headers
            except urllib.error.HTTPError as error:
                return error.code, error.read(), error.headers

        def verify(condition, label):
            if not condition:
                raise AssertionError(label)
            print("PASS: " + label, flush=True)

        try:
            config = json.loads(run("config", "--format", "json"))
            for name, service in config["services"].items():
                ports = service.get("ports", [])
                verify(not ports if name != "web" else
                       len(ports) == 1 and ports[0]["host_ip"] == "127.0.0.1",
                       name + " publishes only permitted ports")
            verify(config["networks"]["database"]["internal"], "database network isolated")
            run("build")
            print("PASS: real API and web Docker builds", flush=True)
            run("up", "-d", "--wait", "--wait-timeout", "180")
            status, data, _ = request("/api/health")
            verify(status == 200 and json.loads(data)["database"] == "ok", "proxy reaches healthy database")
            status, page, _ = request("/")
            verify(status == 200 and b'<div id="root">' in page, "built interface served")
            status, page, _ = request("/gestao/operacao")
            verify(status == 200 and b'<div id="root">' in page, "SPA deep links work")
            verify(request("/api/leads")[0] == 401, "anonymous CRM blocked")
            verify(request("/api/auth/register", body={"email": "test@example.com",
                   "password": "Synthetic-password-123"})[0] == 403, "public registration blocked")
            verify(request("/docs")[1].find(b"swagger-ui") == -1, "API docs not exposed through SPA")
            verify(request("/api/openapi.json")[0] == 404, "API schema unavailable")

            password = secrets.token_urlsafe(24)
            email = "local-owner@example.com"
            # Exercise actual account creation helper without an interactive terminal.
            setup = (
                "import os\nfrom pymongo import MongoClient\nfrom local_admin import create_owner\n"
                "with MongoClient(os.environ['MONGO_URL']) as c:\n"
                " d=c['ibiag_local']\n"
                " assert create_owner(d," + repr(email) + "," + repr(password) + ")\n"
                " before=d.users.find_one({'_id':'local-bootstrap-owner'})\n"
                " assert not create_owner(d,'second@example.com','Another-test-password-123')\n"
                " assert d.users.find_one({'_id':'local-bootstrap-owner'})==before\n"
                " from pymongo.errors import OperationFailure\n"
                " try: c.admin.command('serverStatus')\n"
                " except OperationFailure as e: assert e.code==13\n"
                " else: raise AssertionError('application has excessive privilege')\n"
            )
            run("exec", "-T", "api", "python", "-", stdin=setup)
            print("PASS: owner created, existing account preserved, app lacks admin privileges", flush=True)
            anonymous = (
                "const c = new Mongo('mongodb://127.0.0.1:27017');"
                "try {c.getDB('ibiag_local').users.findOne({}); quit(1);}"
                "catch(e) {if(e.code !== 13) quit(2);}"
            )
            run("exec", "-T", "mongo", "mongosh", "--quiet", "--eval", anonymous)
            print("PASS: unauthenticated Mongo data read blocked", flush=True)

            status, data, _ = request("/api/auth/login", body={"email": email, "password": password})
            verify(status == 200, "real login")
            token = json.loads(data)["access_token"]
            status, data, _ = request("/api/leads", token, {"company": "Synthetic Local Persistence", "country": "Brazil"})
            verify(status == 200, "CRM record saved")
            lead = json.loads(data)
            boundary = "ibiag-local-" + secrets.token_hex(10)
            document = b"%PDF-1.4\n% synthetic local persistence fixture\n%%EOF\n"
            metadata = json.dumps({"title": "Synthetic local file", "category": "general",
                                   "folder_path": "Local CI", "lead_id": lead["id"]})
            body = (
                "--" + boundary + '\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n' +
                metadata + "\r\n--" + boundary +
                '\r\nContent-Disposition: form-data; name="file"; filename="local-test.pdf"\r\n'
                'Content-Type: application/pdf\r\n\r\n'
            ).encode() + document + ("\r\n--" + boundary + "--\r\n").encode()
            status, data, _ = request("/api/documents/upload", token, body,
                                     content_type="multipart/form-data; boundary=" + boundary)
            verify(status == 200, "document uploaded to local GridFS")
            saved = json.loads(data)
            file_path = "/api/files/" + saved["file_path"]
            verify(request(file_path)[0] == 401, "file download requires login")
            verify(request(file_path, token)[1] == document, "private download bytes match")

            # Remove containers/network, deliberately preserve volume. This is a fixture only.
            run("down")
            run("up", "-d", "--wait", "--wait-timeout", "180")
            status, data, _ = request("/api/auth/login", body={"email": email, "password": password})
            verify(status == 200, "owner survives container recreation")
            token = json.loads(data)["access_token"]
            status, data, _ = request("/api/leads", token)
            verify(status == 200 and any(item["id"] == lead["id"] for item in json.loads(data)),
                   "CRM survives container recreation")
            status, data, headers = request(file_path, token)
            verify(status == 200 and hashlib.sha256(data).digest() == hashlib.sha256(document).digest(),
                   "GridFS file survives container recreation")
            verify("no-store" in headers.get("Cache-Control", ""), "private download not cached")
            run("exec", "-T", "api", "python", "local_admin.py")
            verify(request("/api/auth/login", body={"email": email, "password": password})[0] == 200,
                   "subsequent start does not reset password")
        finally:
            # Scoped, randomly named CI fixture only. No real installation is used.
            subprocess.run(compose + ["down", "-v"], capture_output=True, timeout=120)


if __name__ == "__main__":
    main()
