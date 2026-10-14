import {getChatGPTUser} from '@/app/chatgpt-auth';
export async function GET(){const user=await getChatGPTUser();return Response.json(user?{name:user.displayName,email:user.email}:null,{status:user?200:401,headers:{'Cache-Control':'no-store'}})}
