export async function readApiResponse<T>(response:Response):Promise<T>{
const data=await response.json().catch(()=>null) as any;
if(!response.ok){
if(response.status===401&&typeof window!=='undefined')window.dispatchEvent(new Event('exporthub:signin-required'));
const fallback=response.status===401?'Entre com sua conta para continuar. Use Entrar novamente no topo da página.':response.status===409?'Os registros foram alterados em outra janela. Recarregue os dados antes de salvar novamente.':'Não foi possível concluir. Seus dados de entrada foram preservados; tente novamente.';
throw new Error(response.status===401?fallback:data?.error||fallback);
}
if(data===null)throw new Error('A resposta do sistema está incompleta. Tente novamente.');return data as T;
}
async function recordRequest(url:string,options:RequestInit={}){try{return await fetch(url,{...options,signal:AbortSignal.timeout(60000)})}catch{throw new Error('A conexão foi interrompida ou demorou demais. Verifique os registros salvos antes de repetir uma gravação.')}}
function checkedRevision(value:unknown){if(typeof value!=='number'||!Number.isSafeInteger(value)||value<0)throw new Error('A resposta do sistema está incompleta. Verifique os registros salvos antes de tentar novamente.');return value}
// Cada tela mantém as revisões correspondentes aos dados que ela carregou.
export function createRecordSession(){
const revisions:Record<string,number>={};
async function writeRecordsBatch(data:Record<string,unknown>){for(const name of Object.keys(data))if(revisions[name]===undefined)throw new Error('Carregue os registros antes de salvar.');const records=Object.entries(data).map(([name,value])=>({name,data:value,revision:revisions[name]}));const r=await recordRequest('/api/records/transaction',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({records})}),result=await readApiResponse<any>(r);for(const name of Object.keys(data))checkedRevision(result.revisions?.[name]);for(const name of Object.keys(data))revisions[name]=result.revisions[name];}
async function readRecords<T>(name:string):Promise<T>{const r=await recordRequest('/api/records/'+name,{cache:'no-store'});const d=await readApiResponse<any>(r);const revision=checkedRevision(d.revision);if(!Object.prototype.hasOwnProperty.call(d,'data'))throw new Error('A resposta do sistema está incompleta. Tente novamente.');revisions[name]=revision;return d.data;}
async function writeRecords(name:string,data:unknown){if(revisions[name]===undefined)throw new Error('Carregue os registros antes de salvar.');const r=await recordRequest('/api/records/'+name,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({data,revision:revisions[name]})});const d=await readApiResponse<any>(r);revisions[name]=checkedRevision(d.revision);}

return {readRecords,writeRecords,writeRecordsBatch};
}
const defaultSession=createRecordSession();
export const {readRecords,writeRecords,writeRecordsBatch}=defaultSession;
