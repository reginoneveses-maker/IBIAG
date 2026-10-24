/** Regras de equipe e acesso, sem acesso a banco: usadas pela API e testadas isoladamente. */
export type MemberRole='owner'|'editor'|'viewer';
export type InviteRole='editor'|'viewer';
export const inviteRoles:InviteRole[]=['editor','viewer'];
export const roleLabels:Record<MemberRole,string>={owner:'Proprietário',editor:'Editor (lê e altera dados)',viewer:'Leitura (só consulta)'};
export const MAX_PEOPLE=25;
export interface Member {userId:string;email:string;role:MemberRole;createdAt:string}
export interface Invite {email:string;role:InviteRole;invitedBy:string;createdAt:string}

/** Erro com mensagem própria para o usuário; a API responde 4xx em vez de erro interno. */
export class MemberError extends Error {constructor(message:string,readonly status=400){super(message)}}

export function normalizeEmail(raw:unknown){
 const email=typeof raw==='string'?raw.trim().toLowerCase():'';
 if(!email||email.length>254||!/^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[^\s@<>()[\]\\,;:"]{2,}$/.test(email))throw new MemberError('Informe um e-mail válido.');
 return email;
}
export function parseInviteRole(raw:unknown):InviteRole{
 if(!inviteRoles.includes(raw as InviteRole))throw new MemberError('Escolha o acesso: editor ou leitura.');
 return raw as InviteRole;
}
/** Convida por e-mail. O proprietário continua sendo único e não pode ser criado por convite. */
export function planInvite(members:Member[],invites:Invite[],rawEmail:unknown,rawRole:unknown){
 const email=normalizeEmail(rawEmail),role=parseInviteRole(rawRole);
 if(members.some(m=>m.email===email))throw new MemberError('Esta pessoa já tem acesso. Altere o perfil na lista.',409);
 const replaces=invites.some(i=>i.email===email);
 if(!replaces&&members.length+invites.length>=MAX_PEOPLE)throw new MemberError(`O limite é de ${MAX_PEOPLE} pessoas entre acessos e convites.`,409);
 return {email,role,replaces};
}
function target(members:Member[],actorUserId:string,targetUserId:unknown){
 const found=members.find(m=>m.userId===targetUserId);
 if(!found)throw new MemberError('Pessoa não encontrada.',404);
 if(found.userId===actorUserId)throw new MemberError('Você não pode alterar o seu próprio acesso.',409);
 if(found.role==='owner')throw new MemberError('O acesso do proprietário não pode ser alterado nem removido.',409);
 return found;
}
export function planRoleChange(members:Member[],actorUserId:string,targetUserId:unknown,rawRole:unknown){
 const found=target(members,actorUserId,targetUserId);return {member:found,role:parseInviteRole(rawRole)};
}
export function planRemoval(members:Member[],actorUserId:string,targetUserId:unknown){return {member:target(members,actorUserId,targetUserId)}}
