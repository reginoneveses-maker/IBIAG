import {z} from 'zod';
import {transferSchema} from './crm-transfer';
import {normalize} from './crm';
import {RequestDataError} from './request-json';
const id=z.string().min(1).max(180);
export const linkSchema=z.object({sourceId:id,companyId:id,contactId:z.string().max(180),sourceHash:z.string().regex(/^[a-f0-9]{64}$/),importedAt:z.string().datetime()}).strict();
export const inputSchema=z.object({transfer:transferSchema,matches:z.record(id,id).default({})}).strict();
export const applySchema=inputSchema.extend({planHash:z.string().regex(/^[a-f0-9]{64}$/),confirmation:z.literal('IMPORTAR EMPRESAS E CONTATOS')});
export const importAllowed=(value:unknown)=>value==='true';
function canonical(v:any):string{if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v)}
export async function digest(v:unknown){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(v)))),b=>b.toString(16).padStart(2,'0')).join('')}
export function origins(data:any){const links=z.array(linkSchema).max(10000).parse(data.interchangeLinks??[]),companies=new Set((data.companies||[]).map((c:any)=>c.id)),contacts=new Map((data.contacts||[]).map((c:any)=>[c.id,c.companyId]));if(new Set(links.map(l=>l.sourceId)).size!==links.length)throw new Error('Origens duplicadas');for(const l of links)if(!companies.has(l.companyId)||l.contactId&&contacts.get(l.contactId)!==l.companyId)throw new Error('Origem sem vínculo');return links}
export function assertOrigins(before:any,after:any,append=false){const old=origins(before),next=origins(after);if(next.length<old.length||!append&&next.length!==old.length||canonical(next.slice(0,old.length))!==canonical(old))throw new Error('Origem imutável')}
export async function importPlan(raw:unknown,current:any,revision:number,actor:string){
 const input=inputSchema.parse(raw),rows=input.transfer.companies;if(rows.length<1||rows.length>25)throw new RequestDataError(413,'Use de 1 a 25 empresas por lote.');
 const existing=origins(current),companies=[...(current.companies||[])],contacts=[...(current.contacts||[])],actions:any[]=[],links:any[]=[];
 if((current.ops||[]).some((o:any)=>o.company&&!o.companyId))throw new RequestDataError(409,'Revise negociações legadas sem empresa vinculada antes de importar.');
 const sourceIds=new Set(rows.map(r=>r.sourceId));if(Object.keys(input.matches).some(k=>!sourceIds.has(k)))throw new RequestDataError(400,'Confirmação fora do lote.');
 const key=(r:{name:string;country:string})=>JSON.stringify([normalize(r.name),normalize(r.country)]),counts=new Map<string,number>();for(const r of rows)counts.set(key(r),(counts.get(key(r))||0)+1);
 for(const r of rows){const sourceHash=await digest(r),prior=existing.find(l=>l.sourceId===r.sourceId),selected=Object.prototype.hasOwnProperty.call(input.matches,r.sourceId)?input.matches[r.sourceId]:undefined;
 const a:any={sourceId:r.sourceId,name:r.name,country:r.country,action:'blocked',companyId:'',contactId:'',contactNew:false,reason:'',candidates:[]};actions.push(a);
 if(prior){if(prior.sourceHash!==sourceHash){a.reason='Origem importada alterada; exige revisão manual.';continue}if(selected&&selected!==prior.companyId){a.reason='Origem já vinculada a outra empresa.';continue}Object.assign(a,{action:'already',companyId:prior.companyId,contactId:prior.contactId});continue}
 if(!r.country.trim()||counts.get(key(r))!>1){a.reason='País ausente ou identidade repetida no lote.';continue}
 const candidates=companies.filter((c:any)=>key(c)===key(r));a.candidates=candidates.filter((c:any)=>!c.archivedAt).slice(0,20).map((c:any)=>({id:c.id,name:c.name,country:c.country}));
 if(candidates.length){const chosen=candidates.find((c:any)=>c.id===selected&&!c.archivedAt);if(!chosen){a.reason='Confirme explicitamente a empresa existente e ativa.';continue}a.companyId=chosen.id;a.action='link'}else{if(selected){a.reason='Empresa escolhida não corresponde.';continue}a.companyId='IBIAG-'+await digest(['company',r.sourceId]);if(companies.some((c:any)=>c.id===a.companyId)){a.reason='Identificador já utilizado sem origem.';continue}a.action='new'}
 let contact:any;if(r.contact.name||r.contact.email||r.contact.phone){const matches=contacts.filter((c:any)=>!c.archivedAt&&c.companyId===a.companyId&&(r.contact.email?c.email.trim().toLowerCase()===r.contact.email.trim().toLowerCase():normalize(c.name)===normalize(r.contact.name||'Contato a identificar')&&c.phone===r.contact.phone));if(matches.length>1){a.action='blocked';a.reason='Contatos ambíguos.';continue}contact=matches[0];if(!contact){const cid='IBIAG-CONT-'+await digest(['contact',r.sourceId]);if(contacts.some((c:any)=>c.id===cid)){a.action='blocked';a.reason='Identificador de contato já utilizado.';continue}contact={id:cid,companyId:a.companyId,name:r.contact.name||'Contato a identificar',email:r.contact.email,phone:r.contact.phone,role:'',linkedin:'',language:'',notes:'',primary:!contacts.some((c:any)=>c.companyId===a.companyId)};a.contactNew=true}a.contactId=contact.id}
 if(a.action==='new')companies.push({id:a.companyId,name:r.name,country:r.country,website:r.website,industry:r.industry,owner:'',source:'Intercâmbio IBIAG',tags:[],notes:''});if(a.contactNew)contacts.push(contact);links.push({sourceId:r.sourceId,companyId:a.companyId,contactId:a.contactId,sourceHash});
 }
 const summary={companies:actions.filter(a=>a.action==='new').length,contacts:actions.filter(a=>a.action!=='blocked'&&a.contactNew).length,linked:actions.filter(a=>a.action==='link').length,already:actions.filter(a=>a.action==='already').length,blocked:actions.filter(a=>a.action==='blocked').length};
 return {input,actions,summary,links,next:{...current,companies,contacts},planHash:await digest({input,revision,existing,actions,actor})};
}
