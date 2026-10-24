import {workspace,apiError} from '@/db/workspace';
import {recordAudit} from '@/db/audit';
import {sameOrigin} from '@/db/validation';
import {MemberError,planInvite,planRemoval,planRoleChange,normalizeEmail,type Invite,type Member} from '@/services/members';
const noStore={'Cache-Control':'private, no-store'};
async function readPeople(db:D1Database){
 const [members,invites]=await Promise.all([db.prepare('SELECT user_id AS userId,email,role,created_at AS createdAt FROM workspace_members ORDER BY created_at').all<Member>(),db.prepare('SELECT email,role,invited_by AS invitedBy,created_at AS createdAt FROM workspace_invites ORDER BY created_at').all<Invite>()]);
 return {members:members.results,invites:invites.results};
}
async function body(request:Request){
 if(!sameOrigin(request))throw new MemberError('Origem não permitida.',403);
 const raw=await request.text();if(raw.length>4096)throw new MemberError('Pedido grande demais.',413);
 try{const data=JSON.parse(raw);if(data&&typeof data==='object'&&!Array.isArray(data))return data as Record<string,unknown>}catch{}
 throw new MemberError('Pedido inválido.');
}
function fail(e:unknown){return e instanceof MemberError?Response.json({error:e.message},{status:e.status,headers:noStore}):apiError(e)}
export async function GET(){try{const {db,user}=await workspace('admin');return Response.json({...await readPeople(db),you:user.userId},{headers:noStore})}catch(e){return fail(e)}}
export async function POST(request:Request){try{
 const {db,user}=await workspace('admin'),data=await body(request),people=await readPeople(db),plan=planInvite(people.members,people.invites,data.email,data.role);
 await db.prepare('INSERT INTO workspace_invites (email,role,invited_by,created_at) VALUES (?,?,?,?) ON CONFLICT(email) DO UPDATE SET role=excluded.role,invited_by=excluded.invited_by,created_at=excluded.created_at').bind(plan.email,plan.role,user.displayName.slice(0,200),new Date().toISOString()).run();
 await recordAudit(db,user,'invite_member','member',plan.email+' · '+plan.role);
 return Response.json({...await readPeople(db),you:user.userId},{status:201,headers:noStore});
}catch(e){return fail(e)}}
export async function PATCH(request:Request){try{
 const {db,user}=await workspace('admin'),data=await body(request),plan=planRoleChange((await readPeople(db)).members,user.userId,data.userId,data.role);
 await db.prepare("UPDATE workspace_members SET role=? WHERE user_id=? AND role<>'owner'").bind(plan.role,plan.member.userId).run();
 await recordAudit(db,user,'change_member_role','member',plan.member.email+' · '+plan.role);
 return Response.json({...await readPeople(db),you:user.userId},{headers:noStore});
}catch(e){return fail(e)}}
export async function DELETE(request:Request){try{
 const {db,user}=await workspace('admin'),data=await body(request);
 if(data.email!==undefined){const email=normalizeEmail(data.email);await db.prepare('DELETE FROM workspace_invites WHERE email=?').bind(email).run();await recordAudit(db,user,'revoke_invite','member',email)}
 else{const plan=planRemoval((await readPeople(db)).members,user.userId,data.userId);await db.prepare("DELETE FROM workspace_members WHERE user_id=? AND role<>'owner'").bind(plan.member.userId).run();await recordAudit(db,user,'remove_member','member',plan.member.email)}
 return Response.json({...await readPeople(db),you:user.userId},{headers:noStore});
}catch(e){return fail(e)}}
