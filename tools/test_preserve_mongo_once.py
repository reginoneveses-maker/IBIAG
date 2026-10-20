"""Fault-injection checks: synthetic files and fake Mongo only, never production."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / 'preserve_mongo_once.sh').read_text()
FAKE_MONGO = r'''#!/usr/bin/env python3
import fcntl,json,os,sys
from pathlib import Path
p=Path(os.environ['FAKE_STATE']);f=p.open('a+');fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);s=json.load(f)
# A child must never consume its parent's bash -s input.
assert sys.stdin.read() == '', 'Mongo stdin must be detached'
q=sys.argv[-1];result='';code=0
assert q.startswith('(async()=>{'), 'Mongo commands require an explicit async context'
if 'LOCK_STATUS_' in q:result='LOCK_STATUS_LOCKED' if s['locked'] and not os.environ.get('FALSE_STATUS') else 'LOCK_STATUS_UNLOCKED'
elif 'PREFLIGHT_OK' in q:
 result='PREFLIGHT_OK' if not s['locked'] else '';code=0 if result else 2
elif 'fsyncUnlock' in q:
 if os.environ.get('FAIL_UNLOCK'):code=2
 else:s['locked']=False;s['unlocks']+=1;result='UNLOCKED'
elif 'fsync:1' in q:
 s['locked']=True;s['locks']+=1;result='OWNED_LOCK_1'
f.seek(0);f.truncate();json.dump(s,f);f.flush()
if code: print('CONFIDENTIAL-EXCEPTION-CANARY',file=sys.stderr)
if result: print(result)
sys.exit(code)
'''
FAKE_TAR = r'''#!/usr/bin/env python3
import os,sys,time
if '-czf' in sys.argv:
 if os.environ.get('SLOW_TAR'):time.sleep(2)
 if os.environ.get('FAIL_TAR'):
  print('CONFIDENTIAL-RECORD-CANARY',file=sys.stderr);sys.exit(2)
os.execv(os.environ['REAL_TAR'],[os.environ['REAL_TAR'],*sys.argv[1:]])
'''

class PreservationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  data=self.root/'data';data.mkdir();(data/'WiredTiger').write_bytes(b'synthetic-only')
  (data/'payload').write_bytes(bytes(range(256))*200)
  self.coord=self.root/'coord';self.state=self.root/'state.json';self.state.write_text(json.dumps({'locked':False,'locks':0,'unlocks':0}))
  bindir=self.root/'bin';bindir.mkdir()
  for name,content in [('mongosh',FAKE_MONGO),('tar',FAKE_TAR),('df','#!/bin/sh\nprintf "Filesystem 1024-blocks Used Available Capacity Mounted\\nfixture 99999999 1 99999998 1%% /\\n"\n')]:
   p=bindir/name;p.write_text(content);p.chmod(0o700)
  # Only the synthetic copy changes locations/deadlines. The reviewed production source stays fixed.
  self.script=self.root/'run.sh'
  self.script.write_text(SOURCE.replace('DATA_PATH=/data/db','DATA_PATH='+str(data)).replace('/tmp/ibiag-preserve-active',str(self.coord)).replace('/tmp/ibiag-preserve-XXXXXXXX',str(self.root/'copy-XXXXXXXX')).replace('sleep 150','sleep 0.6'))
  self.env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'FAKE_STATE':str(self.state),'REAL_TAR':shutil.which('tar'),
   'RAILWAY_PROJECT_ID':'c1a9635c-789b-4e42-ac9b-cca4326fab9a','RAILWAY_ENVIRONMENT_ID':'fcab95f8-3e30-4da9-8e0b-d9b7f94747ce','RAILWAY_SERVICE_ID':'9cc0395c-7601-451b-a6fa-1511ab168158'}
 def run_copy(self,**changes):
  return subprocess.run(['bash',str(self.script),'--approved-one-off'],env={**self.env,**changes},text=True,capture_output=True,timeout=12)
 def status(self):return json.loads(self.state.read_text())
 def test_inline_mongo_commands_parse_inside_async_context(self):
  import re
  for name in ('PREFLIGHT','STATUS_JS','JS','LOCK'):
   code=re.search(r"^"+name+r"='([^']*)'",SOURCE,re.M).group(1)
   r=subprocess.run(['node','--check'],input='(async()=>{'+code+'})().catch(()=>quit(2));',text=True,capture_output=True)
   self.assertEqual(r.returncode,0,r.stderr)
 def test_success_archive_matches_source_and_unlocks_exactly_once(self):
  r=self.run_copy();self.assertEqual(r.returncode,0,r.stderr);report=json.loads(r.stdout)
  self.assertTrue(report['writes_unlocked']);self.assertFalse(report['restoration_proven'])
  import tarfile,hashlib
  archive=Path(report['archive']);self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),report['sha256'])
  with tarfile.open(archive) as t:self.assertEqual(t.extractfile('./payload').read(),(self.root/'data/payload').read_bytes())
  self.assertEqual(self.status(),{'locked':False,'locks':1,'unlocks':1});self.assertFalse(self.coord.exists())
 def test_archive_error_unlocks_and_never_reports_success_or_record_names(self):
  r=self.run_copy(FAIL_TAR='1');self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'')
  self.assertIn('phase=ARCHIVE code=2',r.stderr);self.assertIn('cleanup=returned',r.stderr)
  self.assertNotIn('CANARY',r.stderr);self.assertFalse(self.status()['locked']);self.assertEqual(self.status()['unlocks'],1)
  self.assertFalse(list(self.root.glob('copy-*/data.tar.gz*')))
 def test_confirmed_own_lock_requires_unlock_even_if_status_helper_would_say_false(self):
  r=self.run_copy(FALSE_STATUS='1');self.assertEqual(r.returncode,0,r.stderr)
  self.assertFalse(self.status()['locked']);self.assertEqual(self.status()['unlocks'],1)
 def test_target_mismatch_never_locks_or_creates_copy(self):
  r=self.run_copy(RAILWAY_SERVICE_ID='wrong');self.assertNotEqual(r.returncode,0);self.assertEqual(self.status()['locks'],0);self.assertFalse(self.coord.exists())
 def test_windows_raw_stdin_trailing_crlf_is_accepted_without_false_failure(self):
  r=subprocess.run(['bash','-s','--','--approved-one-off'],input=self.script.read_text()+'\r\n',env=self.env,text=True,capture_output=True,timeout=12)
  self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['writes_unlocked']);self.assertFalse(self.coord.exists())
 def test_explicit_one_off_ack_required_before_any_side_effect(self):
  r=subprocess.run(['bash',str(self.script)],env=self.env,capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertEqual(self.status()['locks'],0)
 def test_existing_lock_is_preserved_and_copy_refused(self):
  self.state.write_text(json.dumps({'locked':True,'locks':1,'unlocks':0}));r=self.run_copy();self.assertNotEqual(r.returncode,0);self.assertTrue(self.status()['locked']);self.assertEqual(self.status()['unlocks'],0)
 def test_failed_unlock_keeps_recovery_marker_and_refuses_new_copy(self):
  r=self.run_copy(FAIL_UNLOCK='1',FAIL_TAR='1');self.assertEqual(r.returncode,3);self.assertIn('MANUAL_UNLOCK_REQUIRED',r.stderr);self.assertNotIn('CANARY',r.stderr)
  self.assertTrue((self.coord/'armed').exists());self.assertTrue(self.status()['locked'])
 def test_deadline_guard_releases_after_parent_is_killed(self):
  p=subprocess.Popen(['bash',str(self.script),'--approved-one-off'],env={**self.env,'SLOW_TAR':'1'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  deadline=time.monotonic()+3
  while time.monotonic()<deadline and not self.status()['locked']:time.sleep(.01)
  self.assertTrue(self.status()['locked']);p.kill();p.wait(timeout=3)
  deadline=time.monotonic()+3
  while time.monotonic()<deadline and self.status()['locked']:time.sleep(.05)
  self.assertFalse(self.status()['locked']);self.assertEqual(self.status()['unlocks'],1)
  self.assertFalse(list(self.root.glob('copy-*/data.tar.gz')))
 def test_expired_guard_never_releases_a_later_copy(self):
  first=self.run_copy();self.assertEqual(first.returncode,0,first.stderr)
  # The earlier detached guard wakes with its old token while a newer owner occupies the same path.
  self.coord.mkdir();(self.coord/'owner').write_text('different-owner');(self.coord/'armed').touch()
  self.state.write_text(json.dumps({'locked':True,'locks':2,'unlocks':1}))
  time.sleep(.8);self.assertTrue(self.status()['locked']);self.assertEqual(self.status()['unlocks'],1)

if __name__=='__main__':unittest.main()
