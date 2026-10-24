import {workspace,apiError} from '@/db/workspace';
import {readAllCollections} from '@/db/collections';
import {systemHealth} from '@/services/system-health';
import {automaticBackupsAllowed} from '@/services/backup-policy';
import {env} from 'cloudflare:workers';
export async function GET(){try{
 const {db,bucket}=await workspace('admin');
 await db.prepare('SELECT 1 AS ok').first();
 const [rows,specs,files]=await Promise.all([readAllCollections(db),db.prepare('SELECT id,product_id,kind FROM specs LIMIT 1001').all<{id:string;product_id:string;kind:string}>(),db.prepare('SELECT record_id FROM sector_files LIMIT 1001').all<{record_id:string}>()]);
 if(specs.results.length>1000||files.results.length>1000)return Response.json({error:'Volume documental acima do limite deste painel. Nenhum resumo parcial foi exibido.'},{status:413,headers:{'Cache-Control':'private, no-store'}});
 const day=new Date().toLocaleDateString('en-CA',{timeZone:'America/Fortaleza'});
 const summary=systemHealth(rows,specs.results,files.results,day);
 return Response.json({...summary,status:!bucket?'attention':summary.status,database:'ok',storage:bucket?'configured':'unavailable',automaticBackups:automaticBackupsAllowed((env as unknown as {ALLOW_AUTOMATIC_SAFETY_BACKUPS?:string}).ALLOW_AUTOMATIC_SAFETY_BACKUPS),checkedAt:new Date().toISOString()},{headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
 }catch(e){return apiError(e)}}
