type Collections=Record<string,any>;
function links(data:Collections){
 const c=data.commercial||{},refs:{key:string;target:string;id:string}[]=[];
 const add=(kind:string,row:any,field:string,target:string)=>{if(typeof row[field]==='string'&&row[field])refs.push({key:kind+':'+row.id+':'+field,target,id:row[field]})};
 for(const row of c.contacts||[])add('contact',row,'companyId','companies');
 for(const row of c.ops||[]){add('deal',row,'companyId','companies');for(const id of row.contactIds||[])refs.push({key:'deal:'+row.id+':contact:'+id,target:'contacts',id})}
 for(const row of c.quotes||[]){add('quote',row,'opportunityId','ops');add('quote',row,'operationId','shipments')}
 for(const row of data.shipments||[]){add('shipment',row,'quoteId','quotes');add('shipment',row,'opportunityId','ops')}
 for(const kind of ['tasks','sectorRecords'])for(const row of data[kind]||[]){add(kind,row,'opportunityId','ops');add(kind,row,'shipmentId','shipments');if(kind==='tasks')add(kind,row,'recordId','sectorRecords')}
 return refs;
}
function targets(data:Collections){const c=data.commercial||{};return Object.fromEntries(['companies','contacts','ops','quotes','shipments','sectorRecords'].map(name=>[name,new Set((['shipments','sectorRecords'].includes(name)?data[name]||[]:c[name]||[]).map((r:any)=>r.id))]))}
export function assertRecordIntegrity(before:Collections,after:Collections){
 const oldTargets=targets(before),nextTargets=targets(after),old=new Set(links(before).filter(r=>!oldTargets[r.target].has(r.id)).map(r=>r.key+'|'+r.target+'|'+r.id));
 for(const ref of links(after))if(!nextTargets[ref.target].has(ref.id)&&!old.has(ref.key+'|'+ref.target+'|'+ref.id))throw new Error('Vínculo inexistente ou registro ainda utilizado. Revise os vínculos antes de salvar.');
 // Existing operation links are historical and cannot be removed to create a second operation.
 const nextQuotes=new Map((after.commercial?.quotes||[]).map((q:any)=>[q.id,q]));
 for(const quote of before.commercial?.quotes||[])if(quote.operationId){const next:any=nextQuotes.get(quote.id);if(!next||next.operationId!==quote.operationId)throw new Error('Preserve a cotação vinculada à operação existente.');}
}
