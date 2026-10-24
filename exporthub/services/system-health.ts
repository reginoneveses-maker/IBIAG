import {validDate} from './sector-records';
type Source={name:string;payload:any;revision:number};
type Spec={id:string;product_id:string;kind:string};
export function documentHealth(records:any[],specs:Spec[],files:{record_id:string}[],day:string){
 const counts={expired:0,expiring:0,missingValidity:0,invalidValidity:0,missingAttachment:0,unlinkedSpecs:0};
 const end=new Date(day+'T12:00:00Z');end.setUTCDate(end.getUTCDate()+30);const horizon=end.toISOString().slice(0,10);
 for(const r of records){if(r.archivedAt||!['qualidade','documentacao'].includes(r.sectorId))continue;
 const date=r.fields?.validUntil||'';
 if(!date){if(r.kind==='Certificação')counts.missingValidity++}else if(!validDate(date))counts.invalidValidity++;else if(date<day)counts.expired++;else if(date<=horizon)counts.expiring++;
 if(!files.some(f=>f.record_id===r.id))counts.missingAttachment++;
 }
 for(const s of specs)if(!s.product_id||!['ibiag','original'].includes(s.kind))counts.unlinkedSpecs++;
 return counts;
}
export function systemHealth(rows:Source[],specs:Spec[],files:{record_id:string}[],day:string){
 const get=(name:string,fallback:any)=>rows.find(r=>r.name===name)?.payload??fallback;
 const docs=documentHealth(get('sectorRecords',[]),specs,files,day);
 const versions=rows.every(r=>Number.isSafeInteger(r.revision)&&r.revision>=0);
 const warnings=Object.values(docs).reduce((sum,n)=>sum+n,0);
 return {day,collections:rows.length,revisionsValid:versions,documents:docs,specs:specs.length,status:!versions?'review':warnings?'attention':'ok',limitations:['Presença de referência não comprova acesso ou conteúdo do PDF.','Validade de spec não é inferida; revise os registros de qualidade.','Este painel não certifica conformidade nem autoriza embarque.']};
}
