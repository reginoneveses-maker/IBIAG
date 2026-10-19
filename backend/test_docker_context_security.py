"""Use Docker's real matcher/COPY, not a home-grown dockerignore interpretation."""
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("docker"), "Docker is required; executed by the CI backend runner")
class DockerContextSecurityTests(unittest.TestCase):
    def test_copy_excludes_synthetic_secrets_but_retains_required_application_sources(self):
        suffix = uuid.uuid4().hex
        image = "ibiag-context-security-test:" + suffix
        container = "ibiag-context-security-test-" + suffix
        created = False
        # Only synthetic private files in a temporary context. Never read/copy a
        # developer's real .env, credentials, node_modules or Git configuration.
        required = ["backend/serve.py", "backend/requirements.txt", "backend/recover_access.py",
                    "backend/security_readonly_audit.py", "backend/Dockerfile", "frontend/Dockerfile",
                    "frontend/package.json", "frontend/src/App.js", "frontend/public/index.html",
                    "frontend/nginx.conf"]
        forbidden = [".env", ".env.production", "backend/.env", "frontend/.env.local",
                     "frontend/public/.env", "backend/service.env", "backend/private.key",
                     "backend/client.pem", "backend/credentials.json", "backend/auth-token.json",
                     "backend/production-secrets.json", ".npmrc", "frontend/.npmrc", ".git/config",
                     "backend/.aws/credentials", "backups/snapshot.json", "backend/backups/snapshot.json",
                     "database-dump.sql", "private-data.tar.gz", "backend/runtime.log",
                     "backend/__pycache__/cached.pyc", "frontend/node_modules/package/index.js",
                     "backend/browser_fixture.py", "backend/test_synthetic.py",
                     "frontend/src/pages/synthetic.test.jsx", "frontend/e2e/synthetic.cjs"]
        try:
            with tempfile.TemporaryDirectory(prefix="ibiag-docker-context-") as folder:
                context = Path(folder)
                shutil.copyfile(ROOT / ".dockerignore", context / ".dockerignore")
                (context / "Dockerfile").write_text("FROM scratch\nCOPY . /context\n")
                for name in required:
                    target = context / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((ROOT / name).read_bytes())
                for name in forbidden:
                    target = context / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("offline-synthetic-private-canary\n")
                subprocess.run(["docker","build","--network=none","--quiet","--tag",image,str(context)],
                               check=True, capture_output=True, timeout=60)
                subprocess.run(["docker","create","--network=none","--name",container,image,"/unused"],
                               check=True, capture_output=True, timeout=30)
                created = True
                export = subprocess.run(["docker","export",container],check=True,capture_output=True,timeout=30)
                with tarfile.open(fileobj=io.BytesIO(export.stdout),mode="r:*") as archive:
                    names = {member.name.lstrip("./") for member in archive.getmembers()}
                for name in required: self.assertIn("context/"+name,names,name)
                for name in forbidden: self.assertNotIn("context/"+name,names,name)
        finally:
            if created:
                subprocess.run(["docker","rm","--force",container],capture_output=True,timeout=30)
            subprocess.run(["docker","image","rm","--force",image],capture_output=True,timeout=30)
