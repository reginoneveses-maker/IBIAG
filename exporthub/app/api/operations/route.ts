import {readRequestJSON} from '@/services/request-json';
import {assertRecordIntegrity} from '@/services/record-integrity';
import {preserveBeforeWrite} from '@/db/safety-backups';
import {workspace,apiError} from '@/db/workspace';
import {readAllCollections,writeCollectionsAtomic} from '@/db/collections';
import {recordSchemas,sameOrigin} from '@/db/validation';
import {operationInputSchema,createOperationPlan} from '@/services/operation-flow';
import {normalizeCRM} from '@/services/crm';
import {allProducts as portfolio} from '@/data/product-catalog';
export async function POST(request:Request){try{
const {db,bucket,user}=await workspace('write');if(!sameOrigin(request))return new Response(null,{status:403});const json=await readRequestJSON(request,20000);const parsed=operationInputSchema.safeParse(json);if(!parsed.success)return Response.json({error:parsed.error.issues.map(i=>i.message).join(' · ')},{status:400});
const rows=await readAllCollections(db),get=(name:string,fallback:any)=>rows.find(r=>r.name===name)?.payload??fallback;
const commercial=normalizeCRM(get('commercial',{})),quote=commercial.quotes.find(q=>q.id===parsed.data.quoteId);if(!quote)return Response.json({error:'Cotação não encontrada.'},{status:404});if(quote.operationId)return Response.json({error:'Esta cotação já possui uma operação vinculada.',operationId:quote.operationId},{status:409});
if(parsed.data.productId&&!portfolio.some(p=>p.id===parsed.data.productId))return Response.json({error:'Produto não encontrado.'},{status:400});
const now=new Date().toISOString();let plan;try{plan=createOperationPlan(quote,commercial.ops.find(o=>o.id===quote.opportunityId),parsed.data,user.displayName,now)}catch(e){return Response.json({error:(e as Error).message},{status:400})}
const next={commercial:{...commercial,quotes:commercial.quotes.map(q=>q.id===quote.id?plan.quote:q),events:plan.event?[...commercial.events,plan.event]:commercial.events},shipments:[plan.shipment,...get('shipments',[])],sectorRecords:[...plan.records,...get('sectorRecords',[])],tasks:[...plan.tasks,...get('tasks',[])],activities:[{id:'a-'+crypto.randomUUID(),sectorId:'comercial',title:'Operação criada para '+parsed.data.client+' · '+plan.shipment.id,time:now},...get('activities',[])]};
for(const [name,data] of Object.entries(next)){if(!recordSchemas[name as keyof typeof recordSchemas].safeParse(data).success)return Response.json({error:'Revise os registros antes de criar a operação. Nenhuma alteração foi salva.'},{status:400})}
try{const before=Object.fromEntries(rows.map(r=>[r.name,r.payload]));assertRecordIntegrity(before,{...before,...next})}catch{return Response.json({error:'Revise os vínculos da cotação antes de criar a operação.'},{status:409})}
const records=Object.entries(next).map(([name,data])=>({name,data,revision:rows.find(r=>r.name===name)?.revision??0}));await preserveBeforeWrite(db,bucket,records.map(r=>r.name));if(!await writeCollectionsAtomic(db,records,user.userId,user.displayName,['commercial','shipments','sectorRecords','tasks','products','activities'].map(name=>({name,revision:rows.find(r=>r.name===name)?.revision??0}))))return Response.json({error:'Outro acesso alterou os registros. Nenhuma parte da operação foi salva. Recarregue antes de tentar novamente.'},{status:409});
return Response.json({operationId:plan.shipment.id,records:plan.records.map(r=>({id:r.id,sectorId:r.sectorId})),tasks:plan.tasks.length},{status:201});
}catch(e){return apiError(e)}}
