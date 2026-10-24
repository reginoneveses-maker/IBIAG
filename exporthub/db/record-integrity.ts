import {assertOrigins} from '@/services/crm-interchange';
import {readAllCollections} from './collections';
import {assertRecordIntegrity} from '@/services/record-integrity';
import {RequestDataError} from '@/services/request-json';
export async function validateRecordLinks(db:D1Database,records:{name:string;data:unknown}[],allowNewOrigins=false){
 const rows=await readAllCollections(db),before=Object.fromEntries(rows.map(r=>[r.name,r.payload]));
 try{const after={...before,...Object.fromEntries(records.map(r=>[r.name,r.data]))};assertRecordIntegrity(before,after);if(records.some(r=>r.name==='commercial'))assertOrigins(before.commercial||{},after.commercial||{},allowNewOrigins)}catch{throw new RequestDataError(409,'Vínculo inexistente ou registro utilizado por outra etapa. Recarregue e revise antes de salvar.');}
 // All involved collections must be version-guarded, including those read only as references.
 return ['commercial','shipments','sectorRecords','tasks','products','activities'].map(name=>({name,revision:rows.find(r=>r.name===name)?.revision??0}));
}
