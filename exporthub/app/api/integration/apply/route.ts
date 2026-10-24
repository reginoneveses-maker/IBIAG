import {workspace,apiError} from '@/db/workspace';
import {sameOrigin} from '@/db/validation';
import {readRequestJSON,RequestDataError} from '@/services/request-json';
import {applySchema} from '@/services/crm-interchange';
import {prepareImport,applyImport,canImport} from '@/db/crm-interchange';
export async function POST(request:Request){try{const {db,bucket,user}=await workspace('admin');if(!sameOrigin(request))return new Response(null,{status:403});if(!canImport())throw new RequestDataError(403,'Importação não liberada neste ambiente.');const parsed=applySchema.safeParse(await readRequestJSON(request,2*1024*1024));if(!parsed.success)throw new RequestDataError(400,'Confira o arquivo, a prévia e a confirmação.');return Response.json(await applyImport(db,bucket,parsed.data,user),{headers:{'Cache-Control':'private, no-store'}})}catch(e){return apiError(e)}}
