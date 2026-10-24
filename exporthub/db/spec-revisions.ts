import {auditStatement} from './audit';
import {RequestDataError} from '@/services/request-json';
import {validateRevisionIndex,type SpecRevision} from '@/services/spec-revisions';
type Spec={id:string;product_id:string;kind:string;supplier:string;filename:string;size:number;created_at:string};
export async function specHistory(db:D1Database,id:string){
 const source=await db.prepare('SELECT id,product_id,kind,supplier,filename,size,created_at FROM specs WHERE id=?').bind(id).first<Spec>();if(!source)throw new RequestDataError(404,'Documento não encontrado.');
 const own=await db.prepare('SELECT root_id FROM spec_revisions WHERE spec_id=?').bind(id).first<{root_id:string}>(),root=own?.root_id||id;
 const versions=await db.prepare('SELECT s.id,s.product_id,s.kind,s.supplier,s.filename,s.size,s.created_at,r.spec_id,r.root_id,r.revision,r.sha256,r.issued_on,r.valid_until,r.change_note FROM specs s JOIN spec_revisions r ON r.spec_id=s.id WHERE r.root_id=? ORDER BY r.revision LIMIT 501').bind(root).all<Spec&SpecRevision>();
 if(versions.results.length>500)throw new RequestDataError(413,'Histórico acima do limite de consulta.');
 if(!versions.results.length)return {root,original:source,versions:[{...source,spec_id:id,root_id:id,revision:1,sha256:'',issued_on:'',valid_until:'',change_note:'Arquivo original; metadados de validade não informados.'}]};
 validateRevisionIndex(versions.results,versions.results);return {root,original:versions.results[0],versions:versions.results};
}
export async function appendSpecRevision(db:D1Database,bucket:R2Bucket,id:string,input:Awaited<ReturnType<typeof import('@/services/spec-revisions').revisionUpload>>,user:{userId:string;displayName:string}){
 const history=await specHistory(db,id),latest=history.versions.at(-1)!;
 if(latest.revision!==input.expectedRevision)throw new RequestDataError(409,'O documento já tem outra versão. Atualize o histórico antes de reenviar.');
 const nextId=crypto.randomUUID(),guard=crypto.randomUUID(),now=new Date().toISOString(),next=input.expectedRevision+1;
 const statements=[
 db.prepare('INSERT INTO write_guards (id,valid) SELECT ?,CASE WHEN EXISTS(SELECT 1 FROM specs WHERE id=?) AND COALESCE((SELECT MAX(revision) FROM spec_revisions WHERE root_id=?),1)=? THEN 1 ELSE 0 END').bind(guard,history.root,history.root,input.expectedRevision),
 db.prepare("INSERT INTO spec_revisions (spec_id,root_id,revision,sha256,issued_on,valid_until,change_note) VALUES (?,?,1,'','','',?) ON CONFLICT(spec_id) DO NOTHING").bind(history.root,history.root,'Arquivo original; metadados de validade não informados.'),
 db.prepare('INSERT INTO specs (id,product_id,kind,supplier,filename,size,created_at,created_by) VALUES (?,?,?,?,?,?,?,?)').bind(nextId,history.original.product_id,history.original.kind,history.original.supplier,input.filename,input.size,now,user.userId),
 db.prepare('INSERT INTO spec_revisions (spec_id,root_id,revision,sha256,issued_on,valid_until,change_note) VALUES (?,?,?,?,?,?,?)').bind(nextId,history.root,next,input.hash,input.issuedOn,input.validUntil,input.changeNote),
 auditStatement(db,user.userId,user.displayName,'new_spec_revision','spec',nextId),db.prepare('DELETE FROM write_guards WHERE id=?').bind(guard)];
 await bucket.put('specs/'+nextId,input.content,{httpMetadata:{contentType:'application/pdf'}});
 try{await db.batch(statements)}catch(error){
 // A transport error can follow a committed batch. Never delete a possibly committed file.
 let saved;try{saved=await db.prepare('SELECT spec_id FROM spec_revisions WHERE spec_id=? AND root_id=? AND revision=? AND sha256=?').bind(nextId,history.root,next,input.hash).first()}catch{throw error}
 if(!saved){try{await bucket.delete('specs/'+nextId)}catch{console.error('ExportHub: arquivo não referenciado requer revisão manual.');}
 if(String(error).includes('write_revision_guard'))throw new RequestDataError(409,'O documento já tem outra versão. Atualize o histórico antes de reenviar.');throw error;}
 }
 return {id:nextId,rootId:history.root,revision:next,sha256:input.hash};
}
