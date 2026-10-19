"""Run the reviewed read-only audit in the existing IBIAG backend; no deploy/startup."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

REVIEWED_COMMIT = "883e063a760d5b2ceb15f91a37fcea24acdae783"
EXPECTED_ENVIRONMENT = {
    "RAILWAY_PROJECT_ID":"c1a9635c-789b-4e42-ac9b-cca4326fab9a",
    "RAILWAY_SERVICE_ID":"ecbfc64a-75d8-47b2-9b25-b2f7467e77e6",
    "RAILWAY_ENVIRONMENT_ID":"fcab95f8-3e30-4da9-8e0b-d9b7f94747ce",
}
MODULES = {
    "api_security.py":"1c543635d512699a2b5d7d0f4f01383f20892edcedef20c02cf5f6e597a6cc3b",
    "serve.py":"1560fb9dcada02ccaa76e28d72efac6f06c0e25d5e7a5fa83857d13dc5894082",
    "security_readonly_audit.py":"8e2c7acb526ea82ddff23c374ffe068ed177ff3f8070719b461087bd3c8c2b59",
}


def reviewed_sources():
    sources={}
    for name, digest in MODULES.items():
        url="https://raw.githubusercontent.com/reginoneveses-maker/IBIAG/"+REVIEWED_COMMIT+"/backend/"+name
        with urlopen(url,timeout=10) as response:
            data=response.read(128*1024+1)
        if len(data)>128*1024 or hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError("Reviewed source verification failed")
        sources[name]=data
    return sources


def run():
    if any(os.environ.get(key)!=value for key,value in EXPECTED_ENVIRONMENT.items()):
        raise ValueError("Target environment not confirmed")
    sources=reviewed_sources()  # Verify every module before importing any of them.
    with tempfile.TemporaryDirectory(prefix="ibiag-readonly-verified-") as directory:
        os.chmod(directory,0o700)
        for name,data in sources.items():
            target=Path(directory,name);target.write_bytes(data);target.chmod(0o600)
        command="import sys;sys.path.insert(0,sys.argv[1]);import security_readonly_audit;raise SystemExit(security_readonly_audit.main())"
        result=subprocess.run([sys.executable,"-I","-B","-c",command,directory],
                              capture_output=True,text=True,timeout=180)
        if result.returncode not in (0,1) or len(result.stdout)>65536:
            raise ValueError("Audit execution not confirmed")
        report=json.loads(result.stdout)
        if report.get("read_only") is not True or report.get("production_certified") is not False:
            raise ValueError("Unexpected audit output")
        print(json.dumps(report,ensure_ascii=False,sort_keys=True))
        return result.returncode


def main():
    try: return run()
    except (Exception,KeyboardInterrupt):
        print(json.dumps({"audit_completed":False,"production_certified":False,
                          "error":"Auditoria nao confirmada. Verifique sessao/alvo/rede; detalhes nao sao exibidos."},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
