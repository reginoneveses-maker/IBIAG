import {RequestDataError} from '@/services/request-json';
import {env} from 'cloudflare:workers';
import {authorize,type Capability} from '@/db/permissions';
import {getChatGPTUser} from '@/app/chatgpt-auth';
export async function workspace(capability:Capability='read'){const user=await getChatGPTUser();if(!user)throw new Error('AUTH');if(!env.DB)throw new Error('DB indisponível');const role=await authorize(env.DB,user,capability);return {db:env.DB,bucket:env.BUCKET,user,role};}
export function apiError(e:unknown){if(e instanceof RequestDataError)return Response.json({error:e.message},{status:e.status});const code=e instanceof Error?e.message:'';if(!['AUTH','FORBIDDEN'].includes(code))console.error('ExportHub: falha interna');return Response.json({error:code==='AUTH'?'Entre com sua conta para continuar.':code==='FORBIDDEN'?'Sua conta não tem permissão para esta ação.':'Não foi possível concluir. Seus dados de entrada foram preservados; tente novamente.'},{status:code==='AUTH'?401:code==='FORBIDDEN'?403:503});}
