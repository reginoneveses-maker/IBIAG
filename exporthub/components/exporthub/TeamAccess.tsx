'use client';
import {useEffect,useState} from 'react';
import {readApiResponse} from '@/services/workspace';
import {inviteRoles,roleLabels,type Invite,type InviteRole,type Member} from '@/services/members';
type People={members:Member[];invites:Invite[];you:string};
const date=(value:string)=>{const d=new Date(value);return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('pt-BR',{timeZone:'America/Fortaleza'})};

/** Convites e perfis de acesso. Só o proprietário vê esta área; a API também exige permissão de administrador. */
export default function TeamAccess(){
 const [people,setPeople]=useState<People|null>(null),[email,setEmail]=useState(''),[role,setRole]=useState<InviteRole>('editor'),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 async function call(method:string,payload?:unknown){
  setBusy(true);setError('');
  try{
   const r=await fetch('/api/members',{method,cache:'no-store',headers:payload?{'Content-Type':'application/json'}:undefined,body:payload?JSON.stringify(payload):undefined,signal:AbortSignal.timeout(30000)});
   setPeople(await readApiResponse<People>(r));return true;
  }catch(e){setError((e as Error).message);return false}finally{setBusy(false)}
 }
 useEffect(()=>{void call('GET')},[]);
 async function invite(e:React.FormEvent){e.preventDefault();const sent=email.trim();if(await call('POST',{email:sent,role})){setEmail('');setNotice(`Convite registrado para ${sent}. Nenhuma mensagem é enviada: avise a pessoa para entrar no sistema com este e-mail.`)}}
 return <section className="surface team-access" aria-label="Equipe e acessos">
  <h2>Equipe e acessos</h2>
  <p>Convide uma pessoa pelo e-mail da conta que ela usa para entrar. No primeiro acesso, o convite vira um acesso pessoal e deixa de valer. <b>Nenhum e-mail é enviado pelo sistema</b>: avise a pessoa por conta própria. Editores consultam e alteram dados; leitura só consulta. Backups, histórico e esta área são exclusivos do proprietário.</p>
  <form className="form-grid" onSubmit={invite}>
   <label>E-mail da pessoa<input type="email" required maxLength={254} value={email} onChange={e=>{setEmail(e.target.value);setNotice('')}} autoComplete="off"/></label>
   <label>Acesso<select value={role} onChange={e=>setRole(e.target.value as InviteRole)}>{inviteRoles.map(r=><option key={r} value={r}>{roleLabels[r]}</option>)}</select></label>
   <div className="actions"><button className="btn primary" disabled={busy||!email.trim()}>Registrar convite</button></div>
  </form>
  {notice&&<p role="status" className="form-note">{notice}</p>}
  {error&&<p role="alert" className="logistics-warning">{error}</p>}
  {!people&&!error&&<p role="status">Carregando equipe…</p>}
  {people&&<div className="table-wrap"><table><thead><tr><th>Pessoa</th><th>Acesso</th><th>Desde</th><th>Ação</th></tr></thead><tbody>
   {people.members.map(m=><tr key={m.userId}><td>{m.email}{m.userId===people.you&&<small>Você</small>}</td><td>{m.role==='owner'?roleLabels.owner:<select aria-label={'Acesso de '+m.email} disabled={busy} value={m.role} onChange={e=>void call('PATCH',{userId:m.userId,role:e.target.value})}>{inviteRoles.map(r=><option key={r} value={r}>{roleLabels[r]}</option>)}</select>}</td><td>{date(m.createdAt)}</td><td>{m.role!=='owner'&&<button className="btn" disabled={busy} onClick={()=>{if(window.confirm(`Remover o acesso de ${m.email}? A pessoa perde a entrada imediatamente.`))void call('DELETE',{userId:m.userId})}}>Remover acesso</button>}</td></tr>)}
   {people.invites.map(i=><tr key={i.email}><td>{i.email}<small>Convite pendente · {i.invitedBy}</small></td><td>{roleLabels[i.role]}</td><td>{date(i.createdAt)}</td><td><button className="btn" disabled={busy} onClick={()=>void call('DELETE',{email:i.email})}>Cancelar convite</button></td></tr>)}
  </tbody></table></div>}
 </section>;
}
