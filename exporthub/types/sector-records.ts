import type {Status} from './exporthub';
export interface SectorRecord {id:string;sectorId:string;title:string;kind:string;client:string;owner:string;due:string;status:Status;productId:string;opportunityId:string;shipmentId:string;notes:string;fields:Record<string,string>;createdAt:string;updatedAt:string;archivedAt?:string;history:{at:string;owner:string;action:string}[]}
export interface SectorField {key:string;label:string;type?:'date'|'decimal'|'select'|'url';options?:string[];required?:boolean}
export interface SectorConfig {title:string;singular:string;kinds:string[];fields:SectorField[];links:{label:string;href:string}[]}
