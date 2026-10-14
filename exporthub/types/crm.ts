import type {Opportunity,Quote} from './commercial';
export interface CRMCompany {id:string;name:string;country:string;website:string;industry:string;owner:string;source:string;tags:string[];notes:string;createdAt?:string;archivedAt?:string}
export interface CRMContact {id:string;companyId:string;name:string;role:string;email:string;phone:string;linkedin:string;language:string;notes:string;primary:boolean;createdAt?:string;archivedAt?:string}
export interface CRMStage {id:string;name:string;probability:number}
export interface CRMPipeline {id:string;name:string;stages:CRMStage[]}
export interface CRMEvent {id:string;opportunityId:string;type:string;text:string;at:string;owner:string}
export interface CRMGoal {id:string;owner:string;month:string;currency:string;value:number}
export interface CRMTemplate {id:string;name:string;subject:string;body:string}
export interface CRMRule {id:string;pipelineId:string;stageId:string;taskTitle:string;days:number;enabled:boolean}
export interface CRMField {id:string;name:string;type?:'text'|'number'|'date'|'select';required?:boolean;options?:string[]}
export interface CRMView {id:string;name:string;owner:string;country:string;source:string;priority:string;attention:string;status:string}
export interface CRMData {ops:Opportunity[];quotes:Quote[];companies:CRMCompany[];contacts:CRMContact[];events:CRMEvent[];pipelines:CRMPipeline[];goals:CRMGoal[];templates:CRMTemplate[];rules:CRMRule[];fields:CRMField[];views:CRMView[]}
