export type TaxBase='product'|'operation'|'custom'|'revenue';
export interface TaxInput {id:string;name:string;enabled:boolean;mode:'percent'|'fixed';base:TaxBase;rate:number;amount:number;customBase:number;addToPrice:boolean}
export function parseDecimal(value:string){const v=value.trim();if(!v)return NaN;return Number(v.includes(',')?v.replace(/\./g,'').replace(',','.'):v)}
