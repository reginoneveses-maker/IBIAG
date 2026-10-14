export interface NamedCost {id:string;name:string;value:number}
export interface WorkbookTax {id:string;name:string;enabled:boolean;rate:number}
export interface WorkbookLine {id:string;productId:string;name:string;supplier:string;quantity:number;unitCost:number}
export interface WorkbookPricingInput {
 version:1;mode:'products'|'services';title:string;unit:'kg'|'unidades';currency:'BRL'|'USD'|'EUR';rate:number;
 indirectCosts:NamedCost[];monthlyRevenue:number;margin:number;taxes:WorkbookTax[];
 directCosts:NamedCost[];hourCost:number;hours:number;lines:WorkbookLine[];
 serviceMargin:number;serviceTaxes:WorkbookTax[];projectCosts:NamedCost[];ownHourCost:number;ownHours:number;externalHourCost:number;externalHours:number;externalTaxRate:number;
}
export interface WorkbookRowResult {id:string;quantity:number;productCost:number;allocatedCost:number;indirectCost:number;profit:number;tax:number;totalBRL:number;unitBRL:number;total:number;unitPrice:number}
export interface WorkbookPricingResult {rows:WorkbookRowResult[];quantity:number;indirectMonthly:number;indirectRate:number;directTotal:number;ownLabour:number;externalLabour:number;productCost:number;allocatedCost:number;indirectCost:number;profit:number;tax:number;taxRate:number;totalBRL:number;total:number;unitPrice:number}
