import {validDate} from './sector-records';
import {RequestDataError,readBoundedBytes} from './request-json';
export type SpecRevision={spec_id:string;root_id:string;revision:number;sha256:string;issued_on:string;valid_until:string;change_note:string};
export function revisionDates(issued:string,valid:string,day:string){
 if((issued&&(!validDate(issued)||issued>day))||(valid&&!validDate(valid))||(issued&&valid&&valid<issued))throw new RequestDataError(400,'Confira as datas de emissão e validade.');
}
export async function revisionUpload(request:Request){
 const bytes=await readBoundedBytes(request,21*1024*1024);let form:FormData;
 try{form=await new Response(bytes,{headers:{'content-type':request.headers.get('content-type')||''}}).formData()}catch{throw new RequestDataError(400,'Envio de arquivo inválido.');}
 const file=form.get('file'),raw=form.get('expectedRevision'),note=form.get('changeNote'),issued=form.get('issuedOn')||'',valid=form.get('validUntil')||'';
 if(typeof raw!=='string'||!/^([1-9][0-9]{0,2})$/.test(raw)||Number(raw)>=500||typeof note!=='string'||note.trim().length<3||note.length>300||typeof issued!=='string'||typeof valid!=='string')throw new RequestDataError(400,'Informe a versão conferida e o motivo da atualização.');
 revisionDates(issued,valid,new Date().toLocaleDateString('en-CA',{timeZone:'America/Fortaleza'}));
 if(!(file instanceof File)||!file.name.toLowerCase().endsWith('.pdf')||file.size===0||file.size>20*1024*1024)throw new RequestDataError(400,'Selecione um PDF de até 20 MB.');
 const content=await file.arrayBuffer();if(new TextDecoder().decode(content.slice(0,5))!=='%PDF-')throw new RequestDataError(400,'O arquivo não é um PDF válido.');
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',content)),v=>v.toString(16).padStart(2,'0')).join('');
 return {content,filename:file.name.replace(/[\r\n"\\/]/g,'_').slice(0,180),size:file.size,expectedRevision:Number(raw),issuedOn:issued,validUntil:valid,changeNote:note.trim(),hash};
}
export function validateRevisionIndex(revisions:SpecRevision[],specs:{id:string;product_id:string;kind:string;supplier:string}[]){
 const byId=new Map(specs.map(s=>[s.id,s])),ids=new Set<string>(),keys=new Set<string>();
 for(const r of revisions){const spec=byId.get(r.spec_id),root=byId.get(r.root_id),key=r.root_id+':'+r.revision;
 if(typeof r.spec_id!=='string'||typeof r.root_id!=='string'||typeof r.sha256!=='string'||typeof r.issued_on!=='string'||typeof r.valid_until!=='string'||!spec||!root||ids.has(r.spec_id)||keys.has(key)||!Number.isSafeInteger(r.revision)||r.revision<1||r.revision>500||(r.revision===1)!==(r.spec_id===r.root_id)||spec.product_id!==root.product_id||spec.kind!==root.kind||spec.supplier!==root.supplier||!/^([a-f0-9]{64})?$/.test(r.sha256)||(r.revision>1&&!r.sha256)||typeof r.change_note!=='string'||r.change_note.length<1||r.change_note.length>300)throw new Error('Histórico documental inconsistente.');
 if((r.issued_on&&!validDate(r.issued_on))||(r.valid_until&&!validDate(r.valid_until))||(r.issued_on&&r.valid_until&&r.valid_until<r.issued_on))throw new Error('Datas documentais inconsistentes.');
 ids.add(r.spec_id);keys.add(key);
 }
 const groups=new Map<string,SpecRevision[]>();for(const r of revisions){const group=groups.get(r.root_id)||[];group.push(r);groups.set(r.root_id,group)}
 for(const [id,group] of groups){group.sort((a,b)=>a.revision-b.revision);if(group[0]?.spec_id!==id||group.some((r,i)=>r.revision!==i+1))throw new Error('Histórico documental incompleto.');}
 return true;
}

export function specValiditySummary(specs:{id:string}[],revisions:SpecRevision[],day:string){
 const latest=new Map<string,SpecRevision>();for(const r of revisions)if(!latest.has(r.root_id)||latest.get(r.root_id)!.revision<r.revision)latest.set(r.root_id,r);
 const versioned=new Set(revisions.map(r=>r.spec_id)),active=[...specs.filter(s=>!versioned.has(s.id)).map(()=>''),...Array.from(latest.values(),r=>r.valid_until)];
 const end=new Date(day+'T12:00:00Z');end.setUTCDate(end.getUTCDate()+30);const horizon=end.toISOString().slice(0,10),summary={expired:0,expiring:0,unknown:0,invalid:0};
 for(const date of active){if(!date)summary.unknown++;else if(!validDate(date))summary.invalid++;else if(date<day)summary.expired++;else if(date<=horizon)summary.expiring++;}
 return summary;
}
