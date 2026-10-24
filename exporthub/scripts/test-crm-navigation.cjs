const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ts=require('typescript'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const moduleValue={exports:{}};
const js=ts.transpileModule(fs.readFileSync('components/exporthub/crm/CRMNavigation.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
vm.runInNewContext(js,{exports:moduleValue.exports,module:moduleValue,require});
const Navigation=moduleValue.exports.default,sections=moduleValue.exports.crmSections;
for(const current of sections){const html=renderToStaticMarkup(React.createElement(Navigation,{current,counts:{negociacoes:7,empresas:2000,contatos:23,tarefas:2}}));const anchors=[...html.matchAll(/<a\b([^>]+)>/g)].map(m=>m[1]);assert.equal(anchors.length,6);for(const id of sections){const anchor=anchors.find(a=>a.includes('href="/setores/comercial/crm?aba='+id+'"'));assert(anchor,'Acesso direto ausente: '+id);assert.equal(anchor.includes('aria-current="page"'),id===current)}assert.equal(anchors.filter(a=>a.includes('aria-current="page"')).length,1)}
console.log('PASS: seis seções com links nativos únicos, acesso direto e indicação correta da seção ativa.');
