export type Status = 'Em andamento' | 'Pendente' | 'Concluído' | 'Em risco';
export interface Sector {id:string; name:string; short:string; description:string; icon:string; metrics:[string,string][]; processes:string[]}
export interface Task {id:string; sectorId:string; title:string; client:string; due:string; status:Status; owner:string;opportunityId?:string;recordId?:string;type?:string;time?:string;notes?:string;completedAt?:string}
export interface Shipment {id:string; client:string; origin:string; destination:string; country:string; modal:string; eta:string; status:Status; value:number; date:string; cargo:string; progress:number;currency?:'BRL'|'USD'|'EUR';quoteId?:string;opportunityId?:string;productId?:string}
export interface Document {id:string; shipmentId:string; type:string; status:Status; due:string}
export interface Alert {id:string; title:string; detail:string; sectorId:string; severity:'risk'|'warning'; due:string}
export interface Client {id:string; name:string; country:string; contact:string}
export interface Activity {id:string; title:string; sectorId:string; time:string}
export interface User {id:string; name:string; role:'admin'|'manager'|'viewer'; sectorIds:string[]}
