import {readAllCollections} from './collections';
import {assertRecordIntegrity} from '@/services/record-integrity';
import {RequestDataError} from '@/services/request-json';
export async function validateRecordLinks(db:D1Database,records:{name:string;data:unknown}[]){
 const rows=await readAllCollections(db),before=Object.fromEntries(rows.map(r=>[r.name,r.payload]));
 try{assertRecordIntegrity(before,{...before,...Object.fromEntries(records.map(r=>[r.name,r.data]))})}catch{throw new RequestDataError(409,'Vínculo inexistente ou registro utilizado por outra etapa. Recarregue e revise antes de salvar.');}
 // All involved collections must be version-guarded, including those read only as references.
 return ['commercial','shipments','sectorRecords','tasks','products','activities'].map(name=>({name,revision:rows.find(r=>r.name===name)?.revision??0}));
}
