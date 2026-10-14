export type TaxBase='product'|'operation'|'custom'|'revenue';
export interface TaxInput {id:string;name:string;enabled:boolean;mode:'percent'|'fixed';base:TaxBase;rate:number;amount:number;customBase:number;addToPrice:boolean}
export interface PriceInput {quantity:number;costPerKg:number;rate:number;freight:number;insurance:number;documents:number;other:number;margin:number;fees:number;taxes?:TaxInput[]}
export function calculatePrice(p:PriceInput){
const {taxes=[],...numbers}=p;
if(Object.values(numbers).some(v=>!Number.isFinite(v)||v<0))throw new Error('Preencha todos os valores com números válidos, iguais ou maiores que zero.');
if(p.quantity<=0)throw new Error('A quantidade deve ser maior que zero.');if(p.rate<=0)throw new Error('O câmbio deve ser maior que zero.');
const productCost=p.quantity*p.costPerKg;const extras=p.freight+p.insurance+p.documents+p.other;const preTaxCost=productCost+extras;
const enabled=taxes.filter(t=>t.enabled);for(const t of enabled){const required=t.mode==='fixed'?[t.amount]:t.base==='custom'?[t.rate,t.customBase]:[t.rate];if(!required.every(v=>Number.isFinite(v)&&v>=0))throw new Error(`Revise a alíquota, o valor ou a base de ${t.name}.`);if(t.mode==='percent'&&t.rate>100)throw new Error(`A alíquota de ${t.name} deve estar entre 0% e 100%.`)}
const costBase=(t:TaxInput)=>t.base==='product'?productCost:t.base==='operation'?preTaxCost:t.customBase;
const nonRevenueAmount=(t:TaxInput)=>t.mode==='fixed'?t.amount:costBase(t)*t.rate/100;
const revenueTaxRate=enabled.filter(t=>t.addToPrice&&t.mode==='percent'&&t.base==='revenue').reduce((s,t)=>s+t.rate,0);
if(p.margin+p.fees+revenueTaxRate>=100)throw new Error('Margem, despesas e tributos adicionais sobre receita devem somar menos de 100%.');
const costTaxTotal=enabled.filter(t=>t.addToPrice&&!(t.mode==='percent'&&t.base==='revenue')).reduce((s,t)=>s+nonRevenueAmount(t),0);const cost=preTaxCost+costTaxTotal;
const revenue=cost/(1-(p.margin+p.fees+revenueTaxRate)/100);const feeValue=revenue*p.fees/100;
const taxDetails=enabled.map(t=>({id:t.id,name:t.name,mode:t.mode,base:t.base,rate:t.rate,baseAmount:t.mode==='fixed'?null:t.base==='revenue'?revenue:costBase(t),amount:t.mode==='percent'&&t.base==='revenue'?revenue*t.rate/100:nonRevenueAmount(t),addToPrice:t.addToPrice}));
const revenueTaxTotal=revenue*revenueTaxRate/100;const taxTotal=costTaxTotal+revenueTaxTotal;const recordedTaxTotal=taxDetails.filter(t=>!t.addToPrice).reduce((s,t)=>s+t.amount,0);const profit=revenue-cost-feeValue-revenueTaxTotal;const breakEven=cost/(1-(p.fees+revenueTaxRate)/100)/p.rate/p.quantity;
if(![productCost,extras,cost,revenue,feeValue,profit,revenue/p.rate,revenue/p.rate/p.quantity,breakEven,recordedTaxTotal,...taxDetails.map(t=>t.amount)].every(Number.isFinite))throw new Error('Os valores excedem o limite de cálculo. Revise os números.');
return{productCost,extras,preTaxCost,costTaxTotal,revenueTaxTotal,taxTotal,recordedTaxTotal,taxDetails,revenueTaxRate,cost,revenue,feeValue,profit,total:revenue/p.rate,unitPrice:revenue/p.rate/p.quantity,breakEven};
}
export function parseDecimal(value:string){const v=value.trim();if(!v)return NaN;return Number(v.includes(',')?v.replace(/\./g,'').replace(',','.'):v)}
