import {z} from 'zod';
import {normalize} from './crm';
const text=(max:number)=>z.string().max(max).refine(v=>!/[\x00-\x1f\x7f]/.test(v));
const website=text(1000).refine(v=>{if(!v)return true;try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password}catch{return false}});
export const transferSchema=z.object({format:z.literal('ibiag-crm-transfer-v1'),source:z.literal('IBIAG'),companies:z.array(z.object({sourceId:text(180).refine(v=>!!v.trim()),name:text(180).refine(v=>!!v.trim()),country:text(180),website,industry:text(180),contact:z.object({name:text(180),email:text(320),phone:text(80)}).strict()}).strict()).max(1000)}).strict().refine(v=>new Set(v.companies.map(c=>c.sourceId)).size===v.companies.length,'IDs de origem duplicados');
export function buildTransferPreview(raw:unknown,existing:{id:string;name:string;country:string}[]){
 const input=transferSchema.parse(raw),key=(name:string,country:string)=>normalize(name)+'|'+normalize(country);
 const count=new Map<string,number>();for(const row of input.companies){const k=key(row.name,row.country);count.set(k,(count.get(k)||0)+1)}
 const rows=input.companies.map(row=>{const matches=existing.filter(c=>key(c.name,c.country)===key(row.name,row.country)),duplicate=count.get(key(row.name,row.country))!>1;
 return {sourceId:row.sourceId,name:row.name,country:row.country,action:duplicate||matches.length>1?'review':matches.length===1?'match':'new',targetId:!duplicate&&matches.length===1?matches[0].id:null,contactProvided:!!(row.contact.name||row.contact.email||row.contact.phone)}});
 return {format:'ibiag-crm-preview-v1',readOnly:true,rows,counts:{new:rows.filter(r=>r.action==='new').length,matched:rows.filter(r=>r.action==='match').length,review:rows.filter(r=>r.action==='review').length},limitations:['Nenhum dado foi gravado.','Nomes e países só correspondem por normalização exata; confirme a identidade.','Cotações, preços, pedidos, documentos, permissões e arquivos não são migrados.','A migração efetiva exige mapeamento e validação separados.']};
}
