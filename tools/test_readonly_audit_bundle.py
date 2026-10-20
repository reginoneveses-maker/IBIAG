"""Standalone operator-bundle checks; no live DB/SSH/configuration access."""
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch

BUNDLE=Path(__file__).with_name('readonly_audit_bundle.py')
class ReadonlyAuditBundleTests(unittest.TestCase):
    def setUp(self): self.module=runpy.run_path(str(BUNDLE))
    def test_embedded_modules_match_reviewed_digests_and_require_no_remote_download(self):
        sources=self.module['reviewed_sources']()
        self.assertEqual(set(sources),{'api_security.py','serve.py','security_readonly_audit.py'})
        for name,data in sources.items(): self.assertEqual(hashlib.sha256(data).hexdigest(),self.module['MODULES'][name])
        self.assertNotIn('urlopen',BUNDLE.read_text())
    def test_tampered_module_is_refused_before_execution(self):
        self.module['BUNDLED_SOURCES']['api_security.py']=base64.b64encode(b'print("DO NOT EXECUTE")').decode()
        with self.assertRaises(ValueError): self.module['reviewed_sources']()
    def test_missing_target_fails_closed_with_static_message(self):
        out=io.StringIO();err=io.StringIO()
        with patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err): result=self.module['main']()
        self.assertEqual(result,2);self.assertEqual(out.getvalue(),'')
        report=json.loads(err.getvalue());self.assertFalse(report['audit_completed']);self.assertFalse(report['production_certified'])
    def test_confirmed_target_without_db_configuration_never_prints_connection_details(self):
        env={'PATH':os.environ['PATH'],**self.module['EXPECTED_ENVIRONMENT']}
        result=subprocess.run([sys.executable,"-I","-B","-"],input=BUNDLE.read_text(),env=env,capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,'')
        report=json.loads(result.stderr);self.assertFalse(report['production_certified']);self.assertFalse(report['audit_completed'])
    def test_summary_only_contains_flags_without_record_counts_or_arbitrary_names(self):
        report={'configuration_checks':{key:False for key in self.module['CONFIG_KEYS']},'authentication':{key:None for key in self.module['AUTH_KEYS']},
            'finding_counts':{'users_missing_id':123456789},'incomplete_checks':[],
            'manual_evidence_required':list(self.module['MANUAL_KEYS']),'automated_checks_passed':False}
        summary=self.module['safe_summary'](report)
        self.assertEqual(summary['finding_flags'],{'users_missing_id':True});self.assertNotIn('finding_counts',summary)
        self.assertNotIn('123456789',json.dumps(summary));self.assertFalse(summary['production_certified'])
        report['finding_counts']={'PRIVATE-CANARY':1}
        with self.assertRaises(ValueError): self.module['safe_summary'](report)
if __name__=='__main__': unittest.main()
