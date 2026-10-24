import {readCollection} from './collections';
export async function preserveBeforeWrite(db:D1Database,bucket:R2Bucket|undefined,names:string[]){
 if(!bucket)throw new Error('Backup indisponível');const group=new Date().toISOString().replace(/[:.]/g,'-')+'_'+crypto.randomUUID();
 for(const name of names){const row=await readCollection(db,name);if(!row)continue;const text=JSON.stringify({format:'exporthub-collection-snapshot-v1',savedAt:new Date().toISOString(),...row});const bytes=new TextEncoder().encode(text);const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');await bucket.put('safety-backups/'+group+'/'+name+'.json',bytes,{httpMetadata:{contentType:'application/json'},customMetadata:{sha256:hash}})}
}
