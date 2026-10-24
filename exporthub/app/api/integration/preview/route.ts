import {workspace,apiError} from '@/db/workspace';
import {sameOrigin} from '@/db/validation';
import {readCollection} from '@/db/collections';
import {readRequestJSON,RequestDataError} from '@/services/request-json';
import {buildTransferPreview,transferSchema} from '@/services/crm-transfer';
export async function POST(request:Request){try{
 const {db}=await workspace('admin');if(!sameOrigin(request))return new Response(null,{status:403});
 const body=await readRequestJSON(request,2*1024*1024),parsed=transferSchema.safeParse(body);
 if(!parsed.success)throw new RequestDataError(400,'Arquivo de intercâmbio inválido; use o formato IBIAG CRM.');
 const current=await readCollection(db,'commercial'),companies=current?.payload?.companies||[];
 if(!Array.isArray(companies)||companies.length>10000||companies.some((c:any)=>!c||typeof c.id!=='string'||typeof c.name!=='string'||typeof c.country!=='string'))throw new RequestDataError(409,'O cadastro de empresas precisa de revisão.');
 return Response.json({...buildTransferPreview(parsed.data,companies),targetRevision:current?.revision??0},{headers:{'Cache-Control':'private, no-store'}});
 }catch(e){return apiError(e)}}
