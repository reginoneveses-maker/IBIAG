import {getChatGPTUser} from '@/app/chatgpt-auth';
import {workspace} from '@/db/workspace';
export async function GET(){
 const user=await getChatGPTUser();
 if(!user)return Response.json(null,{status:401,headers:{'Cache-Control':'no-store'}});
 // O papel vem do acesso cadastrado; quem não tem acesso aparece com role null.
 const role=await workspace('read').then(w=>w.role,()=>null);
 return Response.json({name:user.displayName,email:user.email,role},{headers:{'Cache-Control':'no-store'}});
}
