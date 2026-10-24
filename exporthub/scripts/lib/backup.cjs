// Verificação e restauração do "Backup com PDFs" (formato exporthub-complete-v1).
// A restauração só grava em um ambiente local VAZIO; nunca sobrescreve dados existentes.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),zlib=require('node:zlib'),crypto=require('node:crypto');
const {load,root}=require('./ts-loader.cjs');

/** Leitor mínimo de ZIP pelo diretório central (stored/deflate), conferindo CRC32 e tamanho de cada arquivo. */
function crc32(buffer){let c,crc=0xffffffff;for(let i=0;i<buffer.length;i++){c=(crc^buffer[i])&255;for(let k=0;k<8;k++)c=c&1?0xedb88320^(c>>>1):c>>>1;crc=(crc>>>8)^c}return(crc^0xffffffff)>>>0}
function readZip(buffer){
 let end=-1;for(let i=buffer.length-22;i>=Math.max(0,buffer.length-65557);i--)if(buffer.readUInt32LE(i)===0x06054b50){end=i;break}
 if(end<0)throw new Error('Arquivo ZIP inválido ou incompleto (fim do diretório não encontrado).');
 const count=buffer.readUInt16LE(end+10);let p=buffer.readUInt32LE(end+16);const entries=new Map(),problems=[];
 for(let n=0;n<count;n++){
  if(buffer.readUInt32LE(p)!==0x02014b50)throw new Error('Diretório do ZIP corrompido.');
  const method=buffer.readUInt16LE(p+10),crc=buffer.readUInt32LE(p+16),csize=buffer.readUInt32LE(p+20),size=buffer.readUInt32LE(p+24),nameLen=buffer.readUInt16LE(p+28),extraLen=buffer.readUInt16LE(p+30),commentLen=buffer.readUInt16LE(p+32),offset=buffer.readUInt32LE(p+42),name=buffer.toString('utf8',p+46,p+46+nameLen);
  p+=46+nameLen+extraLen+commentLen;
  if(entries.has(name)){problems.push('Nome repetido no ZIP: '+name);continue}
  const lh=offset+30+buffer.readUInt16LE(offset+26)+buffer.readUInt16LE(offset+28);
  if(buffer.readUInt32LE(offset)!==0x04034b50){problems.push('Cabeçalho inválido: '+name);continue}
  let data;try{data=method===0?buffer.subarray(lh,lh+csize):method===8?zlib.inflateRawSync(buffer.subarray(lh,lh+csize)):null}catch{data=null}
  if(!data){problems.push('Não foi possível ler: '+name);continue}
  if(data.length!==size)problems.push(`Tamanho divergente em ${name}: esperado ${size}, lido ${data.length}`);
  else if(crc32(data)!==crc)problems.push('Conteúdo corrompido (CRC): '+name);
  entries.set(name,data);
 }
 return {entries,problems};
}

const collectionNames=['tasks','commercial','activities','products','shipments','sectorRecords'];
const prefixOf={specs:'specs/',crmFiles:'crm/',sectorFiles:'sector/'};
function verifyBackup(zipBuffer){
 const errors=[],warnings=[];let manifest,zip;
 try{zip=readZip(zipBuffer)}catch(e){return {errors:[e.message],warnings,summary:null}}
 errors.push(...zip.problems);
 const raw=zip.entries.get('ExportHub_backup.json');
 if(!raw)return {errors:[...errors,'ExportHub_backup.json não encontrado no ZIP.'],warnings,summary:null};
 try{manifest=JSON.parse(raw.toString('utf8'))}catch{return {errors:[...errors,'ExportHub_backup.json não é um JSON válido.'],warnings,summary:null}}
 if(manifest.format!=='exporthub-complete-v1')errors.push('Formato desconhecido: '+manifest.format);
 const {recordSchemas}=load(root+'/db/validation.ts');
 const records=Array.isArray(manifest.records)?manifest.records:[];if(!Array.isArray(manifest.records))errors.push('Lista de coleções ausente.');
 const byName={};
 for(const r of records){
  if(!collectionNames.includes(r.name)){warnings.push('Coleção desconhecida ignorada: '+r.name);continue}
  if(!Number.isSafeInteger(r.revision)||r.revision<0)errors.push('Revisão inválida em '+r.name);
  if(!recordSchemas[r.name].safeParse(r.payload).success)errors.push('Dados da coleção '+r.name+' não passam na validação do sistema.');
  byName[r.name]=r.payload;
 }
 for(const name of ['commercial','products'])if(!byName[name])warnings.push('Coleção sem dados no backup: '+name);
 const files=Array.isArray(manifest.files)?manifest.files:(errors.push('Lista de PDFs ausente.'),[]),paths=new Set(),byId=new Map();
 for(const f of files){
  if(paths.has(f.zipPath))errors.push('Caminho repetido no manifesto: '+f.zipPath);paths.add(f.zipPath);if(byId.has(f.id))errors.push('Identificador de arquivo repetido: '+f.id);byId.set(f.id,f);
  const data=zip.entries.get(f.zipPath);
  if(!data)errors.push('PDF listado e ausente no ZIP: '+f.zipPath);
  else if(data.length!==f.size)errors.push(`Tamanho diferente do cadastro em ${f.zipPath}: ${data.length} ≠ ${f.size}`);
  else if(data.subarray(0,5).toString('latin1')!=='%PDF-')warnings.push('Arquivo sem assinatura PDF: '+f.zipPath);
 }
 for(const name of zip.entries.keys())if(name!=='ExportHub_backup.json'&&!paths.has(name))warnings.push('Arquivo no ZIP que não consta no manifesto: '+name);
 const list=v=>Array.isArray(v)?v:[],productIds=new Set(list(manifest.products).map(p=>p?.id)),opIds=new Set(list(byName.commercial?.ops).map(o=>o?.id)),processIds=new Set(list(byName.sectorRecords).map(r=>r?.id));
 for(const [key,label,ref,ok] of [['specs','spec','product_id',productIds],['crmFiles','anexo de negociação','opportunity_id',opIds],['sectorFiles','anexo de processo','record_id',processIds]]){
  const rows=list(manifest[key]);if(!Array.isArray(manifest[key]))errors.push('Lista ausente: '+key);
  for(const row of rows){if(!byId.has(row.id))errors.push(`Sem arquivo no manifesto para ${label} ${row.id}`);if(!ok.has(row[ref]))warnings.push(`${label} ${row.id} aponta para ${ref} inexistente: ${row[ref]}`)}
 }
 const revisions=manifest.specRevisions||[];
 if(manifest.documentVersioning&&manifest.documentVersioning!=='spec-revisions-v1')errors.push('Versionamento documental desconhecido.');
 if((manifest.specRevisions&&!manifest.documentVersioning)||!Array.isArray(revisions))errors.push('Índice de versões documentais inválido.');
 else try{
  load(root+'/services/spec-revisions.ts').validateRevisionIndex(revisions,list(manifest.specs));
  for(const r of revisions){const f=byId.get(r.spec_id),bytes=f&&zip.entries.get(f.zipPath);if(r.sha256&&(!bytes||sha(bytes)!==r.sha256))errors.push('Hash divergente na versão documental '+r.spec_id);}
 }catch{errors.push('Histórico de versões documentais inconsistente.');}
 const summary={exportedAt:manifest.exportedAt,collections:records.length,specs:list(manifest.specs).length,crmFiles:list(manifest.crmFiles).length,sectorFiles:list(manifest.sectorFiles).length,files:files.length,bytes:files.reduce((s,f)=>s+(f.size||0),0)};
 return {errors,warnings,summary,manifest,zip};
}

async function openProxy(stateDir){
 const {getPlatformProxy}=await import('wrangler');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'restore-cfg-')),config=path.join(dir,'wrangler.toml');
 fs.writeFileSync(config,'name = "exporthub-restore"\ncompatibility_date = "2025-01-01"\n[[d1_databases]]\nbinding = "DB"\ndatabase_name = "site-creator-d1"\ndatabase_id = "00000000-0000-4000-8000-000000000000"\n[[r2_buckets]]\nbinding = "BUCKET"\nbucket_name = "site-creator-r2"\n');
 const proxy=await getPlatformProxy({configPath:config,persist:{path:stateDir}});
 return {env:proxy.env,dispose:async()=>{await proxy.dispose();fs.rmSync(dir,{recursive:true,force:true})}};
}
async function applyMigrations(db){
 for(const file of fs.readdirSync(path.join(root,'drizzle')).filter(f=>f.endsWith('.sql')).sort())
  for(const sql of fs.readFileSync(path.join(root,'drizzle',file),'utf8').split('--> statement-breakpoint').map(s=>s.trim()).filter(Boolean))await db.exec(sql.replace(/\s*\n\s*/g,' '));
}
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');

/** Restaura em um estado local (Miniflare/Wrangler) vazio. Retorna o relatório de conferência. */
async function restoreBackup(zipBuffer,stateDir){
 const check=verifyBackup(zipBuffer);if(check.errors.length)throw new Error('Backup com problemas; nada foi restaurado:\n- '+check.errors.join('\n- '));
 const {manifest,zip}=check,{writeCollection}=load(root+'/db/collections.ts'),handle=await openProxy(stateDir);
 try{
  const db=handle.env.DB,bucket=handle.env.BUCKET;
  const existing=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='collections'").first();
  if(!existing)await applyMigrations(db);
  const used=await Promise.all(['collections','specs','crm_files','sector_files','spec_revisions'].map(t=>db.prepare(`SELECT COUNT(*) n FROM ${t}`).first()));
  const listed=await bucket.list({limit:1});
  if(used.some(r=>r.n>0)||listed.objects.length)throw new Error('O destino não está vazio. Use uma pasta de estado nova: a restauração nunca sobrescreve dados existentes.');
  const now=new Date().toISOString();
  for(const r of manifest.records){if(!['tasks','commercial','activities','products','shipments','sectorRecords'].includes(r.name))continue;await writeCollection(db,r.name,r.payload,0,'restore','Restauração de backup');await db.prepare('UPDATE collections SET revision=?,updated_at=? WHERE name=?').bind(r.revision,r.updated_at||now,r.name).run()}
  const tables={specs:['specs','INSERT INTO specs (id,product_id,kind,supplier,filename,size,created_at,created_by) VALUES (?,?,?,?,?,?,?,?)',r=>[r.id,r.product_id,r.kind,r.supplier,r.filename,r.size,r.created_at,'restore']],crmFiles:['crm','INSERT INTO crm_files (id,opportunity_id,filename,size,created_at,created_by) VALUES (?,?,?,?,?,?)',r=>[r.id,r.opportunity_id,r.filename,r.size,r.created_at,'restore']],sectorFiles:['sector','INSERT INTO sector_files (id,record_id,filename,size,created_at,created_by) VALUES (?,?,?,?,?,?)',r=>[r.id,r.record_id,r.filename,r.size,r.created_at,'restore']]};
  const byId=new Map(manifest.files.map(f=>[f.id,f]));let restoredFiles=0;
  for(const [key,[prefix,sql,bind]] of Object.entries(tables))for(const row of manifest[key]||[]){
   const entry=byId.get(row.id),data=zip.entries.get(entry.zipPath);
   await bucket.put(prefix+'/'+row.id,data,{httpMetadata:{contentType:'application/pdf'}});
   await db.prepare(sql).bind(...bind(row)).run();restoredFiles++;
  }
  for(const r of manifest.specRevisions||[])await db.prepare('INSERT INTO spec_revisions (spec_id,root_id,revision,sha256,issued_on,valid_until,change_note) VALUES (?,?,?,?,?,?,?)').bind(r.spec_id,r.root_id,r.revision,r.sha256,r.issued_on,r.valid_until,r.change_note).run();
  // Conferência: o que foi gravado precisa ser idêntico ao backup.
  const problems=[];
  for(const r of manifest.records){const row=await db.prepare('SELECT revision FROM collections WHERE name=?').bind(r.name).first();if(!row||row.revision!==r.revision)problems.push('Revisão divergente: '+r.name);const read=await load(root+'/db/collections.ts').readCollection(db,r.name);if(!read||JSON.stringify(read.payload)!==JSON.stringify(r.payload))problems.push('Conteúdo divergente: '+r.name)}
  for(const [key,[prefix]] of Object.entries(tables))for(const row of manifest[key]||[]){const obj=await bucket.get(prefix+'/'+row.id),data=zip.entries.get(byId.get(row.id).zipPath);if(!obj||sha(Buffer.from(await obj.arrayBuffer()))!==sha(data))problems.push('PDF divergente: '+prefix+'/'+row.id)}
  const restoredRevisions=(await db.prepare('SELECT spec_id,root_id,revision,sha256,issued_on,valid_until,change_note FROM spec_revisions ORDER BY root_id,revision').all()).results;
  const expectedRevisions=[...(manifest.specRevisions||[])].sort((a,b)=>(a.root_id<b.root_id?-1:a.root_id>b.root_id?1:0)||a.revision-b.revision);
  if(restoredRevisions.length!==expectedRevisions.length||restoredRevisions.some((r,i)=>Object.keys(r).some(k=>r[k]!==expectedRevisions[i][k])))problems.push('Histórico documental divergente.');
  if(problems.length)throw new Error('A conferência pós-restauração falhou:\n- '+problems.join('\n- '));
  return {collections:manifest.records.length,files:restoredFiles,warnings:check.warnings,summary:check.summary};
 }finally{await handle.dispose()}
}
module.exports={readZip,verifyBackup,restoreBackup,openProxy,crc32};
