import type {ChatGPTUser} from '@/app/chatgpt-auth';
export type Capability='read'|'write'|'export'|'admin';
export type MemberRole='owner'|'editor'|'viewer';
// Initial owner enrollment only. Stable Site user ID becomes the membership key.
const ownerEmail='pocket.regino@outlook.com';
export function can(role:MemberRole,capability:Capability){return role==='owner'||capability==='read'||role==='editor'&&capability==='write'}
export async function authorize(db:D1Database,user:ChatGPTUser,capability:Capability){
 const email=user.email.trim().toLowerCase();
 if(email===ownerEmail)await db.prepare("INSERT INTO workspace_members (user_id,email,role,created_at) VALUES (?,?,'owner',?) ON CONFLICT DO NOTHING").bind(user.userId,email,new Date().toISOString()).run();
 const member=await db.prepare('SELECT email,role FROM workspace_members WHERE user_id=?').bind(user.userId).first<{email:string;role:MemberRole}>();
 if(!member||member.email!==email||!can(member.role,capability))throw new Error('FORBIDDEN');return member.role;
}
