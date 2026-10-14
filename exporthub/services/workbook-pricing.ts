import {z} from 'zod';
import type {WorkbookPricingInput,WorkbookPricingResult,WorkbookRowResult} from '@/types/workbook-pricing';
const value=z.number().finite().nonnegative(),rate=value.lt(100),text=z.string().max(500),cost=z.object({id:text.min(1),name:text.min(1),value});
export const workbookPricingSchema=z.object({version:z.literal(1),mode:z.enum(['products','services']),title:text,unit:z.enum(['kg','unidades']),currency:z.enum(['BRL','USD','EUR']),rate:value.positive(),indirectCosts:z.array(cost).max(100),monthlyRevenue:value.positive(),margin:rate,taxes:z.array(z.object({id:text.min(1),name:text.min(1),enabled:z.boolean(),rate})).max(30),directCosts:z.array(cost).max(100),hourCost:value,hours:value,lines:z.array(z.object({id:text.min(1),productId:text,name:text.min(1),supplier:text,quantity:value.positive(),unitCost:value})).max(100),serviceMargin:rate,serviceTaxes:z.array(z.object({id:text.min(1),name:text.min(1),enabled:z.boolean(),rate})).max(30),projectCosts:z.array(cost).max(100),ownHourCost:value,ownHours:value,externalHourCost:value,externalHours:value,externalTaxRate:rate});

/**
 * Fórmula sequencial da planilha IBIAG, compartilhada pelo precificador e pelo assistente de cotações.
 * base → ÷(1 − indiretos) → ÷(1 − margem) → ÷(1 − tributos e comissões sobre o preço final).
 * `levyRate` (tributos) e `feeRate` (comissões/despesas) são frações (0–1) do preço final e dividem o mesmo passo.
 */
export interface WorkbookFormulaInput {base:number;indirectRate:number;marginPct:number;taxRate:number;feeRate?:number}
export function applyWorkbookFormula({base,indirectRate,marginPct,taxRate,feeRate=0}:WorkbookFormulaInput){
 const levy=taxRate+feeRate;
 if(indirectRate<0||indirectRate>=1)throw new Error('Os custos indiretos devem ser menores que o faturamento mensal.');
 if(marginPct<0||marginPct>=100)throw new Error('A margem deve estar entre 0% e 100%.');
 if(taxRate<0||feeRate<0||levy>=1)throw new Error('Tributos e comissões sobre o preço devem somar menos de 100%.');
 const indirectCost=base/(1-indirectRate)*indirectRate,withIndirect=base+indirectCost,profit=withIndirect/(1-marginPct/100)*marginPct/100,beforeTax=withIndirect+profit,tax=beforeTax/(1-levy)*taxRate,fee=beforeTax/(1-levy)*feeRate;
 return {base,indirectCost,withIndirect,profit,beforeTax,tax,fee,totalBRL:beforeTax+tax+fee};
}
export function calculateWorkbookPrice(raw:WorkbookPricingInput):WorkbookPricingResult {
 const parsed=workbookPricingSchema.safeParse(raw);if(!parsed.success)throw new Error('Preencha faturamento e câmbio positivos, nomes dos itens e quantidades maiores que zero. Custos não podem ser negativos; percentuais devem ficar abaixo de 100%.');const p=parsed.data;
 for(const list of [p.lines,p.indirectCosts,p.directCosts,p.projectCosts,p.taxes,p.serviceTaxes])if(new Set(list.map(x=>x.id)).size!==list.length)throw new Error('Há identificadores repetidos na memória de cálculo.');
 if(p.currency==='BRL'&&p.rate!==1)throw new Error('Para propostas em reais, o câmbio deve ser 1.');
 const sum=(items:{value:number}[])=>items.reduce((s,c)=>s+c.value,0),indirectMonthly=sum(p.indirectCosts),indirectRate=indirectMonthly/p.monthlyRevenue,margin=p.mode==='products'?p.margin:p.serviceMargin,taxes=p.mode==='products'?p.taxes:p.serviceTaxes,taxRate=taxes.filter(t=>t.enabled).reduce((s,t)=>s+t.rate,0)/100;
 if(indirectRate>=1)throw new Error('Os custos indiretos devem ser menores que o faturamento mensal.');if(taxRate>=1)throw new Error('A soma dos impostos selecionados deve ficar abaixo de 100%.');
 const finish=(id:string,quantity:number,productCost:number,allocatedCost:number):WorkbookRowResult=>{const {indirectCost,profit,tax,totalBRL}=applyWorkbookFormula({base:productCost+allocatedCost,indirectRate,marginPct:margin,taxRate});return {id,quantity,productCost,allocatedCost,indirectCost,profit,tax,totalBRL,unitBRL:totalBRL/quantity,total:totalBRL/p.rate,unitPrice:totalBRL/p.rate/quantity}};
 let rows:WorkbookRowResult[],quantity:number,directTotal:number,ownLabour:number,externalLabour=0;
 if(p.mode==='products'){if(!p.lines.length)throw new Error('Adicione pelo menos um produto.');quantity=p.lines.reduce((s,l)=>s+l.quantity,0);directTotal=sum(p.directCosts);ownLabour=p.hourCost*p.hours;rows=p.lines.map(l=>finish(l.id,l.quantity,l.quantity*l.unitCost,l.quantity/quantity*(directTotal+ownLabour)));}
 else {if(!p.title.trim())throw new Error('Informe o nome do projeto ou serviço.');if(p.ownHours<=0)throw new Error('Informe as horas próprias dedicadas para calcular o preço por hora.');quantity=p.ownHours;directTotal=sum(p.projectCosts);ownLabour=p.ownHourCost*p.ownHours;externalLabour=p.externalHourCost*p.externalHours/(1-p.externalTaxRate/100);rows=[finish('project',quantity,directTotal+ownLabour+externalLabour,0)];}
 const total=(k:keyof WorkbookRowResult)=>rows.reduce((s,r)=>s+Number(r[k]),0),result={rows,quantity,indirectMonthly,indirectRate,directTotal,ownLabour,externalLabour,productCost:total('productCost'),allocatedCost:total('allocatedCost'),indirectCost:total('indirectCost'),profit:total('profit'),tax:total('tax'),taxRate,totalBRL:total('totalBRL'),total:total('total'),unitPrice:total('total')/quantity};
 if(Object.values(result).filter(x=>typeof x==='number').some(x=>!Number.isFinite(x))||rows.some(r=>Object.values(r).some(x=>typeof x==='number'&&!Number.isFinite(x))))throw new Error('Os valores excedem o limite de cálculo.');return result;
}
