"""CI-only: restore a physical copy into a different disposable MongoDB8 container.

No Railway CLI, credentials, production endpoints or artifact upload.
"""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parent
IMAGE='mongo:8'
ENV=['-e','RAILWAY_PROJECT_ID=c1a9635c-789b-4e42-ac9b-cca4326fab9a',
     '-e','RAILWAY_ENVIRONMENT_ID=fcab95f8-3e30-4da9-8e0b-d9b7f94747ce',
     '-e','RAILWAY_SERVICE_ID=9cc0395c-7601-451b-a6fa-1511ab168158']

def run(*args,check=True,timeout=120):
 return subprocess.run(list(args),capture_output=True,text=True,check=check,timeout=timeout)
def js(container,code):
 return run('docker','exec',container,'mongosh','--quiet','--norc','--eval',code).stdout.strip()
def ready(container):
 for _ in range(80):
  r=run('docker','exec',container,'mongosh','--quiet','--norc','--eval','print(db.adminCommand({ping:1}).ok)',check=False,timeout=8)
  if r.returncode==0 and r.stdout.strip()=='1':return
  time.sleep(.25)
 raise RuntimeError('Synthetic fixture did not start')

def main():
 suffix=uuid.uuid4().hex[:12];source='ibiag-preserve-source-'+suffix;clone='ibiag-preserve-clone-'+suffix
 try:
  run('docker','run','-d','--name',source,'--network','none',IMAGE)
  ready(source)
  js(source,'const d=db.getSiblingDB("preservation_fixture");d.items.insertOne({_id:"synthetic",quantity:NumberDecimal("123.450"),at:ISODate("2026-01-02T03:04:05Z"),payload:BinData(0,"AAECAwQF"),before:true});d.items.createIndex({before:1},{unique:true});d.getCollection("fs.files").insertOne({_id:ObjectId("650000000000000000000001"),length:6,chunkSize:255,uploadDate:new Date(),filename:"synthetic.bin"});d.getCollection("fs.chunks").insertOne({files_id:ObjectId("650000000000000000000001"),n:0,data:BinData(0,"AAECAwQF")});')
  run('docker','cp',str(ROOT/'preserve_mongo_once.sh'),source+':/tmp/preserve.sh')
  result=run('docker','exec',*ENV,source,'bash','/tmp/preserve.sh','--approved-one-off',timeout=220)
  info=json.loads(result.stdout);assert info['copy_created'] and info['writes_unlocked'] and not info['restoration_proven']
  assert js(source,'print(db.getSiblingDB("admin").currentOp().fsyncLock===true)')=='false'
  js(source,'db.getSiblingDB("preservation_fixture").items.updateOne({_id:"synthetic"},{$set:{after:true}});')
  with tempfile.TemporaryDirectory(prefix='ibiag-synthetic-restore-') as directory:
   folder=Path(directory);archive=folder/'synthetic.tar.gz';data=folder/'data';data.mkdir()
   run('docker','cp',source+':'+info['archive'],str(archive))
   import hashlib
   assert hashlib.sha256(archive.read_bytes()).hexdigest()==info['sha256']
   with tarfile.open(archive) as value:
    members=value.getmembers();assert sum(m.size for m in members)<2*1024**3
    assert all(not m.name.startswith('/') and '..' not in Path(m.name).parts and (m.isfile() or m.isdir()) for m in members)
    value.extractall(data,members=members)
   # Remove only the copied process lock, never the live source's lock file.
   (data/'mongod.lock').unlink(missing_ok=True)
   run('docker','run','-d','--name',clone,'--network','none','-v',str(data)+':/data/db',IMAGE)
   ready(clone)
   verified=js(clone,'const d=db.getSiblingDB("preservation_fixture");const x=d.items.findOne({_id:"synthetic"});print(Boolean(x&&x.before===true&&!x.after&&x.quantity.toString()==="123.450"&&x.at.toISOString()==="2026-01-02T03:04:05.000Z"&&x.payload.base64()==="AAECAwQF"&&d.items.getIndexes().some(i=>i.unique&&i.key.before===1)&&d.getCollection("fs.files").countDocuments({filename:"synthetic.bin"})===1&&d.getCollection("fs.chunks").findOne({n:0}).data.base64()==="AAECAwQF"));')
   assert verified=='true','Synthetic restored data/index/types/GridFS did not match'
   js(clone,'db.getSiblingDB("preservation_fixture").items.updateOne({_id:"synthetic"},{$set:{clone_writable:true}})')
   assert js(clone,'print(db.getSiblingDB("preservation_fixture").items.findOne({_id:"synthetic"}).clone_writable===true)')=='true'
   run('docker','rm','-fv',clone)
  # Fault injection into a disposable container: archive failure must unlock live Mongo.
  run('docker','exec',source,'mkdir','-p','/tmp/fail-bin')
  with tempfile.TemporaryDirectory() as d:
   stub=Path(d)/'tar';stub.write_text('#!/bin/sh\nexit 2\n');stub.chmod(0o755)
   run('docker','cp',str(stub),source+':/tmp/fail-bin/tar')
  failed=run('docker','exec',*ENV,'-e','PATH=/tmp/fail-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',source,'bash','/tmp/preserve.sh','--approved-one-off',check=False,timeout=90)
  assert failed.returncode!=0 and 'copy_created' not in failed.stdout
  assert js(source,'print(db.getSiblingDB("admin").currentOp().fsyncLock===true)')=='false'
  js(source,'db.getSiblingDB("preservation_fixture").items.updateOne({_id:"synthetic"},{$set:{source_writable:true}})')
  # A pre-existing lock belongs to another operation and must not be released.
  js(source,'db.getSiblingDB("admin").runCommand({fsync:1,lock:true})')
  refused=run('docker','exec',*ENV,source,'bash','/tmp/preserve.sh','--approved-one-off',check=False,timeout=90)
  assert refused.returncode!=0 and js(source,'print(db.getSiblingDB("admin").currentOp().fsyncLock===true)')=='true'
  js(source,'db.getSiblingDB("admin").runCommand({fsyncUnlock:1})')
  print('PASS: synthetic MongoDB8 copy/restored data, BSON types, unique index, GridFS bytes; independent clone writable; archive failure unlocked; existing lock preserved')
 finally:
  for name in (clone,source):run('docker','rm','-fv',name,check=False)

if __name__=='__main__':main()
