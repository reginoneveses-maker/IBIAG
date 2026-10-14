import type {WorkbookPricingInput} from './workbook-pricing';
import type {QuoteLogistics} from './logistics';
import type {TaxInput} from '@/services/pricing';
import type {UnifiedPriceModel} from '@/services/unified-pricing';
export type Stage=string;
export interface Opportunity {id:string;company:string;country:string;contact:string;email:string;phone:string;product:string;stage:Stage;value:number;currency:string;nextAction:string;nextDate:string;notes:string;title?:string;companyId?:string;contactIds?:string[];pipelineId?:string;stageId?:string;status?:'open'|'won'|'lost';owner?:string;source?:string;expectedClose?:string;priority?:'Baixa'|'Normal'|'Alta';probability?:number;lossReason?:string;createdAt?:string;updatedAt?:string;closedAt?:string;archivedAt?:string;tags?:string[];customFields?:Record<string,string>;productIds?:string[]}
export interface Quote {id:string;opportunityId:string;supplier:string;product:string;incoterm:string;quantity:number;costPerKg:number;rate:number;currency:string;freight:number;insurance:number;documents:number;other:number;margin:number;fees:number;total:number;unitPrice:number;createdAt:string;taxes?:TaxInput[];logistics?:QuoteLogistics;assistantRequest?:string;customer?:string;operationId?:string;workbookPricing?:WorkbookPricingInput;pricingModel?:UnifiedPriceModel}
