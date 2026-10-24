import {workspace,apiError} from '@/db/workspace';
import {sameOrigin} from '@/db/validation';
import {saveDraft,saveDraftSchema} from '@/db/quote-drafts';
import {readRequestJSON,RequestDataError} from '@/services/request-json';
export async function PUT(request:Request,{params}:{params:Promise<{id:string}>}){try{const {db,bucket,user}=await workspace('write');if(!sameOrigin(request))return new Response(null,{status:403});const {id}=await params,parsed=saveDraftSchema.safeParse(await readRequestJSON(request,200000));if(!parsed.success||parsed.data.draft.id!==id)throw new RequestDataError(400,'Rascunho ou revisão inválidos.');return Response.json(await saveDraft(db,parsed.data,user,bucket),{headers:{'Cache-Control':'private, no-store'}})}catch(e){return apiError(e)}}
