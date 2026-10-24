import {z} from 'zod';
import type {TaxInput} from './pricing';
import {applyWorkbookFormula} from './workbook-pricing';

/**
 * Motor de preço único do assistente de cotações, baseado na planilha IBIAG (divisores sequenciais).
 *
 * Regras (decisão explícita):
 *  - Base = produto (custo BRL/kg × kg) + frete + seguro + documentos + outros custos + tributos "de custo".
 *  - Tributos de custo = valor fixo ou % sobre produto/operação/base informada, quando marcados para somar ao preço.
 *  - Custos indiretos = total mensal ÷ faturamento mensal da empresa (perfil salvo), como na planilha.
 *  - Margem incide sobre o preço antes de tributos, como na planilha (e não sobre o preço final).
 *  - Tributos % sobre a receita e comissões/despesas % dividem o mesmo passo final: preço ÷ (1 − tributos − comissões).
 *  - Tributos não marcados para somar ao preço são apenas registrados.
 *  - Sem perfil de custos indiretos o cálculo é só uma prévia (indirectConfigured=false) e não gera proposta final.
 */
const money=z.number().finite().nonnegative();
export const companyPricingProfileSchema=z.object({
 version:z.literal(1),
 indirectCosts:z.array(z.object({id:z.string().min(1).max(500),name:z.string().min(1).max(500),value:money})).max(100),
 monthlyRevenue:money.positive(),
 updatedAt:z.string().max(100),
});
export type CompanyPricingProfile=z.infer<typeof companyPricingProfileSchema>;
export interface IndirectCosts {configured:boolean;rate:number}
/** Fração dos custos indiretos sobre o faturamento (0–1). Perfil ausente ou inválido = não configurado. */
export function indirectCostsFrom(profile?:unknown):IndirectCosts{
 const parsed=companyPricingProfileSchema.safeParse(profile);
 if(!parsed.success)return {configured:false,rate:0};
 const rate=parsed.data.indirectCosts.reduce((s,c)=>s+c.value,0)/parsed.data.monthlyRevenue;
 if(rate>=1)throw new Error('Os custos indiretos devem ser menores que o faturamento mensal.');
 return {configured:true,rate};
}
export interface UnifiedPriceInput {quantity:number;costPerKg:number;rate:number;freight:number;insurance:number;documents:number;other:number;margin:number;fees:number;taxes?:TaxInput[];indirect:IndirectCosts}
export interface UnifiedPriceModel {engine:'workbook-sequential-v1';indirectConfigured:boolean;indirectRate:number;marginPct:number;taxRate:number;feeRate:number}
export function calculateUnifiedPrice(p:UnifiedPriceInput){
 const {taxes=[],indirect,...numbers}=p;
 if(Object.values(numbers).some(v=>!Number.isFinite(v)||v<0))throw new Error('Preencha todos os valores com números válidos, iguais ou maiores que zero.');
 if(p.quantity<=0)throw new Error('A quantidade deve ser maior que zero.');
 if(p.rate<=0)throw new Error('O câmbio deve ser maior que zero.');
 const productCost=p.quantity*p.costPerKg,extras=p.freight+p.insurance+p.documents+p.other,operationCost=productCost+extras;
 const enabled=taxes.filter(t=>t.enabled);
 for(const t of enabled){
  const required=t.mode==='fixed'?[t.amount]:t.base==='custom'?[t.rate,t.customBase]:[t.rate];
  if(!required.every(v=>Number.isFinite(v)&&v>=0))throw new Error(`Revise a alíquota, o valor ou a base de ${t.name}.`);
  if(t.mode==='percent'&&t.rate>100)throw new Error(`A alíquota de ${t.name} deve estar entre 0% e 100%.`);
 }
 const isRevenue=(t:TaxInput)=>t.mode==='percent'&&t.base==='revenue';
 const costBase=(t:TaxInput)=>t.base==='product'?productCost:t.base==='operation'?operationCost:t.customBase;
 const costTaxAmount=(t:TaxInput)=>t.mode==='fixed'?t.amount:costBase(t)*t.rate/100;
 const costTaxTotal=enabled.filter(t=>t.addToPrice&&!isRevenue(t)).reduce((s,t)=>s+costTaxAmount(t),0);
 const taxRate=enabled.filter(t=>t.addToPrice&&isRevenue(t)).reduce((s,t)=>s+t.rate,0)/100,feeRate=p.fees/100;
 const f=applyWorkbookFormula({base:operationCost+costTaxTotal,indirectRate:indirect.rate,marginPct:p.margin,taxRate,feeRate});
 const recordedTaxTotal=enabled.filter(t=>!t.addToPrice).reduce((s,t)=>s+(isRevenue(t)?f.totalBRL*t.rate/100:costTaxAmount(t)),0);
 const result={productCost,extras,costTaxTotal,recordedTaxTotal,indirectCost:f.indirectCost,profit:f.profit,revenueTaxTotal:f.tax,feeValue:f.fee,totalBRL:f.totalBRL,total:f.totalBRL/p.rate,unitPrice:f.totalBRL/p.rate/p.quantity,
  model:{engine:'workbook-sequential-v1' as const,indirectConfigured:indirect.configured,indirectRate:indirect.rate,marginPct:p.margin,taxRate,feeRate} satisfies UnifiedPriceModel};
 if(![productCost,extras,costTaxTotal,recordedTaxTotal,result.indirectCost,result.profit,result.revenueTaxTotal,result.feeValue,result.totalBRL,result.total,result.unitPrice].every(Number.isFinite))throw new Error('Os valores excedem o limite de cálculo. Revise os números.');
 return result;
}
