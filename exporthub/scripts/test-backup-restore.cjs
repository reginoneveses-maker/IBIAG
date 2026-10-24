// Backup com PDFs: verificação (CRC, tamanhos, vínculos, validação) e restauração conferida em ambiente local vazio.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {load,root}=require('./lib/ts-loader.cjs'),{verifyBackup,restoreBackup,openProxy}=require('./lib/backup.cjs'),{streamZip}=load(root+'/services/zip-stream.ts'),{readCollection}=load(root+'/db/collections.ts');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const pdf=(seed,size=3000)=>Buffer.concat([Buffer.from('%PDF-1.4\n'),crypto.createHash('sha512').update(seed).digest(),crypto.randomBytes(size)]);
const files={specA:pdf('a'),specB:pdf('b',8000),crmA:pdf('c',500),sectorA:pdf('d',100)};
const row=(table,id,extra)=>({id,filename:id+'.pdf',size:files[id].length,created_at:'2026-10-10T10:00:00.000Z',...extra});
const specs=[row('specs','specA',{product_id:'P1',kind:'ibiag',supplier:'Fornecedor ç/ã'}),row('specs','specB',{product_id:'P1',kind:'original',supplier:'Fornecedor 2'})],crmFiles=[row('crm','crmA',{opportunity_id:'OP-FANTASMA'})],sectorFiles=[row('sector','sectorA',{record_id:'PROC-1'})];
const entry=(file,zipPath,category)=>({id:file.id,filename:file.filename,size:file.size,createdAt:file.created_at,category,context:'x',sector:'x',href:'/x',contextHref:'/x',zipPath});
const manifest=(over={})=>({format:'exporthub-complete-v1',exportedAt:'2026-10-14T00:00:00.000Z',products:[{id:'P1',name:'Produto 1'}],records:[
 {name:'commercial',payload:{ops:[],quotes:[]},revision:7,updated_at:'2026-10-13T10:00:00.000Z'},{name:'products',payload:[{id:'P1',supplier:'Fornecedor ç/ã',cost:'17,50'}],revision:3,updated_at:'2026-10-12T10:00:00.000Z'},{name:'sectorRecords',payload:[],revision:1,updated_at:'2026-10-11T10:00:00.000Z'}],
 specs,crmFiles,sectorFiles,files:[entry(specs[0],'Specs/IBIAG/F/P1/specA.pdf','Spec IBIAG'),entry(specs[1],'Specs/Originais/F2/P1/specB.pdf','Spec original'),entry(crmFiles[0],'Negociacoes/OP/crmA.pdf','Negociação'),entry(sectorFiles[0],'Setores/x/PROC-1/sectorA.pdf','Processo setorial')],...over});
async function zipOf(m,skip=[],mutate=x=>x){
 const bytes=Buffer.from(JSON.stringify(m,null,2)),list=[{name:'ExportHub_backup.json',data:bytes},...m.files.filter(f=>!skip.includes(f.zipPath)).map(f=>({name:f.zipPath,data:files[f.id]}))];
 const stream=streamZip(list.map(e=>({name:e.name,size:e.data.length,body:async()=>new ReadableStream({start(c){c.enqueue(new Uint8Array(e.data));c.close()}})})));
 const chunks=[];for await(const c of stream)chunks.push(Buffer.from(c));return mutate(Buffer.concat(chunks));
}
(async()=>{
 // 1) Backup íntegro: sem erros; aponta apenas o vínculo órfão.
 const good=await zipOf(manifest()),ok=verifyBackup(good);
 assert.deepEqual(ok.errors,[]);assert.equal(ok.summary.files,4);assert.equal(ok.summary.collections,3);assert(ok.warnings.some(w=>/OP-FANTASMA/.test(w)),'vínculo órfão deve gerar aviso');assert(ok.warnings.some(w=>/PROC-1/.test(w)));
 // 2) Byte alterado em um PDF → CRC.
 const flipped=await zipOf(manifest(),[],b=>{const i=b.indexOf(files.specB.subarray(100,140));const c=Buffer.from(b);c[i+5]^=0xff;return c});assert(verifyBackup(flipped).errors.some(e=>/CRC.*specB/.test(e)));
 // 3) PDF listado e ausente; tamanho divergente; coleção inválida; ZIP truncado; sem manifesto.
 assert(verifyBackup(await zipOf(manifest(),['Specs/IBIAG/F/P1/specA.pdf'])).errors.some(e=>/ausente.*specA/.test(e)));
 const wrongSize=manifest();wrongSize.files[0].size+=1;assert(verifyBackup(await zipOf(wrongSize)).errors.some(e=>/Tamanho diferente/.test(e)));
 assert(verifyBackup(await zipOf(manifest({records:[{name:'commercial',payload:{ops:'x'},revision:1,updated_at:''}]}))).errors.some(e=>/validação/.test(e)));
 assert(verifyBackup(good.subarray(0,good.length-40)).errors.length>0);assert(verifyBackup(Buffer.from('não é zip')).errors.length>0);
 const orphanRow=manifest({specs:[...specs,{...specs[0],id:'semArquivo'}]});assert(verifyBackup(await zipOf(orphanRow)).errors.some(e=>/semArquivo/.test(e)));
 console.log('PASS: verificação detecta PDF alterado, ausente ou de tamanho diferente, coleção inválida, ZIP truncado e registro sem arquivo; vínculos órfãos viram aviso.');
 // 4) Restauração em ambiente vazio: dados, revisões e PDFs idênticos.
 const state=fs.mkdtempSync(path.join(os.tmpdir(),'restore-state-'));
 try{
  const report=await restoreBackup(good,state);assert.equal(report.collections,3);assert.equal(report.files,4);
  const handle=await openProxy(state);
  try{
   const {DB:db,BUCKET:bucket}=handle.env;
   for(const r of manifest().records){const read=await readCollection(db,r.name);assert.deepEqual(read.payload,r.payload);assert.equal(read.revision,r.revision);assert.equal(read.updated_at,r.updated_at)}
   assert.deepEqual((await db.prepare('SELECT id,product_id,kind,supplier,filename,size,created_at FROM specs ORDER BY id').all()).results.map(r=>r.id),['specA','specB']);
   assert.equal((await db.prepare('SELECT supplier FROM specs WHERE id=?').bind('specA').first()).supplier,'Fornecedor ç/ã');
   for(const [id,key] of [['specA','specs/'],['specB','specs/'],['crmA','crm/'],['sectorA','sector/']]){const obj=await bucket.get(key+id);assert.equal(sha(Buffer.from(await obj.arrayBuffer())),sha(files[id]),id)}
  }finally{await handle.dispose()}
  // 5) Nunca sobrescreve: segunda restauração no mesmo destino é recusada e o conteúdo permanece.
  await assert.rejects(restoreBackup(good,state),/não está vazio/);
  const again=await openProxy(state);try{assert.equal((await readCollection(again.env.DB,'commercial')).revision,7)}finally{await again.dispose()}
  console.log('PASS: restauração em ambiente vazio preserva dados, revisões, IDs e PDFs (SHA-256) e recusa sobrescrever um destino com dados.');
  // 6) Backup com problema: nada é gravado.
  const empty=fs.mkdtempSync(path.join(os.tmpdir(),'restore-empty-'));
  try{await assert.rejects(restoreBackup(flipped,empty),/nada foi restaurado/);const check=await openProxy(empty);try{assert.equal(await check.env.DB.prepare("SELECT name FROM sqlite_master WHERE name='collections'").first(),null)}finally{await check.dispose()}}finally{fs.rmSync(empty,{recursive:true,force:true})}
  console.log('PASS: backup corrompido é recusado antes de qualquer gravação.');
 }finally{fs.rmSync(state,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
