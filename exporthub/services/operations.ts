import {readRecords,writeRecords} from './workspace';
import type {Task,User} from '@/types/exporthub';
export interface OperationsRepository {listTasks():Promise<Task[]>;saveTasks(items:Task[]):Promise<void>}
// Registros duráveis via API autenticada; controle de revisão no serviço workspace.
export const demoRepository:OperationsRepository={async listTasks(){return readRecords<Task[]>('tasks')},async saveTasks(items){await writeRecords('tasks',items)}};
export interface AuthProvider {getUser():Promise<User|null>}
export const canEdit=(user:User,sectorId:string)=>user.role==='admin'||(user.role==='manager'&&user.sectorIds.includes(sectorId));
export const demoUser:User={id:'demo',name:'Marina Costa',role:'admin',sectorIds:[]};
export function exportCsv(name:string,rows:Record<string,unknown>[]){const keys=Array.from(new Set(rows.flatMap(row=>Object.keys(row))));const esc=(x:unknown)=>`"${(typeof x==='string'&&/^[=+@\-\t\r]/.test(x)?"'"+x:String(x??'')).replace(/"/g,'""')}"`;const data=[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(esc).join(';')).join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF'+data],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name+'.csv';a.click();URL.revokeObjectURL(url)}
