// Equipe e acesso: regras puras (services/members.ts) e fluxo real de convite sobre um D1 local descartável.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict'),ts=require('typescript'),root=path.resolve(__dirname,'..'),cache={};
function load(file){file=path.resolve(file);if(cache[file])return cache[file].exports;const m={exports:{}};cache[file]=m;const req=n=>n.startsWith('@/')?load(path.join(root,n.slice(2))+'.ts'):n.startsWith('.')?load(path.resolve(path.dirname(file),n)+'.ts'):require(n);vm.runInThisContext('(function(require,module,exports){'+ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText+'\n})')(req,m,m.exports);return m.exports}
const members=load(root+'/services/members.ts');
const thrown=(fn,re,status)=>{try{fn()}catch(e){assert(e instanceof members.MemberError,'erro esperado de equipe: '+e);assert.match(e.message,re);if(status)assert.equal(e.status,status);return}assert.fail('deveria falhar: '+re)};
const owner={userId:'u-owner',email:'dono@ibiag.com',role:'owner',createdAt:'1'},ed={userId:'u-ed',email:'socia@ibiag.com',role:'editor',createdAt:'2'};
// 1) Regras puras
assert.equal(members.normalizeEmail('  Socia@IBIAG.com '),'socia@ibiag.com');
for(const bad of ['','abc','a@b','a b@c.com','<x>@y.com','a@b.c',null,undefined,42,'a'.repeat(250)+'@x.com'])thrown(()=>members.normalizeEmail(bad),/e-mail válido/);
assert.deepEqual(members.planInvite([owner],[],'Nova@x.com','viewer'),{email:'nova@x.com',role:'viewer',replaces:false});
assert.equal(members.planInvite([owner],[{email:'nova@x.com',role:'viewer',invitedBy:'x',createdAt:'1'}],'nova@x.com','editor').replaces,true);
thrown(()=>members.planInvite([owner],[],'x@y.com','owner'),/editor ou leitura/);thrown(()=>members.planInvite([owner],[],'x@y.com','admin'),/editor ou leitura/);thrown(()=>members.planInvite([owner],[],'x@y.com',undefined),/editor ou leitura/);
thrown(()=>members.planInvite([owner,ed],[],'SOCIA@ibiag.com','viewer'),/já tem acesso/,409);
const many=Array.from({length:members.MAX_PEOPLE},(_,i)=>({email:`p${i}@x.com`,role:'viewer',invitedBy:'x',createdAt:'1'}));thrown(()=>members.planInvite([owner],many,'novo@x.com','viewer'),/limite/,409);assert.equal(members.planInvite([owner],many.slice(0,-1).concat({email:'p0@x.com',role:'viewer',invitedBy:'x',createdAt:'1'}),'p0@x.com','editor').replaces,true);
assert.equal(members.planRoleChange([owner,ed],'u-owner','u-ed','viewer').role,'viewer');
thrown(()=>members.planRoleChange([owner,ed],'u-owner','u-owner','viewer'),/próprio acesso/,409);thrown(()=>members.planRoleChange([owner,ed],'u-ed','u-owner','viewer'),/próprio acesso|proprietário/);thrown(()=>members.planRoleChange([owner,ed],'u-owner','u-ed','owner'),/editor ou leitura/);thrown(()=>members.planRoleChange([owner,ed],'u-owner','ghost','viewer'),/não encontrada/,404);
thrown(()=>members.planRemoval([owner,ed],'u-owner','u-owner'),/próprio acesso/,409);thrown(()=>members.planRemoval([owner,{...ed,role:'owner'}],'u-owner','u-ed'),/proprietário/,409);assert.equal(members.planRemoval([owner,ed],'u-owner','u-ed').member.email,'socia@ibiag.com');
console.log('PASS: regras de equipe — e-mail, perfis permitidos, duplicidade, limite, proprietário protegido e auto-alteração bloqueada.');
// 2) Fluxo real sobre D1 local descartável (Miniflare)
(async()=>{
 const {getPlatformProxy}=await import('wrangler');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'members-d1-')),config=path.join(dir,'wrangler.toml');
 fs.writeFileSync(config,'name = "members-test"\ncompatibility_date = "2025-01-01"\n[[d1_databases]]\nbinding = "DB"\ndatabase_name = "members-test"\ndatabase_id = "00000000-0000-4000-8000-000000000000"\n');
 const proxy=await getPlatformProxy({configPath:config,persist:false}),db=proxy.env.DB;
 try{
  for(const file of fs.readdirSync(path.join(root,'drizzle')).filter(f=>f.endsWith('.sql')).sort())for(const sql of fs.readFileSync(path.join(root,'drizzle',file),'utf8').split('--> statement-breakpoint').map(s=>s.trim()).filter(Boolean))await db.exec(sql.replace(/\s*\n\s*/g,' '));
  const perms=load(root+'/db/permissions.ts'),user=(id,email,name='Pessoa')=>({userId:id,email,displayName:name,fullName:name});
  const roleOf=async(u,cap)=>perms.authorize(db,u,cap).then(r=>r,e=>e.message);
  assert.equal(await roleOf(user('u-owner','pocket.regino@outlook.com','Dono'),'admin'),'owner');
  assert.equal(await roleOf(user('u-x','estranho@x.com'),'read'),'FORBIDDEN');
  // Convite de leitura: primeiro acesso vincula o ID, consome o convite e registra auditoria.
  await db.prepare('INSERT INTO workspace_invites (email,role,invited_by,created_at) VALUES (?,?,?,?)').bind('parceira@ibiag.com','viewer','Dono','2026-10-14').run();
  assert.equal(await roleOf(user('u-p','Parceira@IBIAG.com','Parceira'),'read'),'viewer');
  assert.equal((await db.prepare('SELECT COUNT(*) n FROM workspace_invites').first()).n,0);
  assert.deepEqual(await db.prepare('SELECT user_id,email,role FROM workspace_members WHERE email=?').bind('parceira@ibiag.com').first(),{user_id:'u-p',email:'parceira@ibiag.com',role:'viewer'});
  for(const cap of ['write','export','admin'])assert.equal(await roleOf(user('u-p','parceira@ibiag.com'),cap),'FORBIDDEN',cap);
  assert.equal((await db.prepare("SELECT COUNT(*) n FROM audit_events WHERE action='accept_invite'").first()).n,1);
  // O convite é de uso único: outra conta com o mesmo e-mail não entra por ele.
  assert.equal(await roleOf(user('u-p2','parceira@ibiag.com'),'read'),'FORBIDDEN');
  // Editor: lê e grava, mas não exporta nem administra.
  await db.prepare('INSERT INTO workspace_invites (email,role,invited_by,created_at) VALUES (?,?,?,?)').bind('editor@ibiag.com','editor','Dono','2026-10-14').run();
  assert.equal(await roleOf(user('u-e','editor@ibiag.com'),'write'),'editor');
  for(const cap of ['export','admin'])assert.equal(await roleOf(user('u-e','editor@ibiag.com'),cap),'FORBIDDEN',cap);
  // Convite não concede proprietário nem aceita perfil inválido.
  await assert.rejects(db.prepare('INSERT INTO workspace_invites (email,role,invited_by,created_at) VALUES (?,?,?,?)').bind('x@ibiag.com','owner','Dono','1').run());
  // Convite não vale para quem já tem outro acesso com e-mail diferente.
  assert.equal(await roleOf(user('u-p','outro@ibiag.com'),'read'),'FORBIDDEN');
  // Remover acesso corta a entrada na hora; sem convite novo, não volta.
  await db.prepare('DELETE FROM workspace_members WHERE user_id=?').bind('u-p').run();
  assert.equal(await roleOf(user('u-p','parceira@ibiag.com'),'read'),'FORBIDDEN');
  console.log('PASS: convite sobre D1 real — primeiro acesso vincula o ID, uso único, perfis limitados, e-mail sem diferenciar maiúsculas, remoção efetiva e auditoria.');
 }finally{await proxy.dispose();fs.rmSync(dir,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
