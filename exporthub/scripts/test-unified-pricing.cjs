const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict'),ts=require('typescript'),cache={},root=path.resolve(__dirname,'..');
function load(file){file=path.resolve(file);if(cache[file])return cache[file].exports;if(file.endsWith('.json'))return JSON.parse(fs.readFileSync(file,'utf8'));const m={exports:{}};cache[file]=m;const req=n=>n.startsWith('@/')?load(path.join(root,n.slice(2))+'.ts'):n.startsWith('.')?load(path.resolve(path.dirname(file),n)+'.ts'):require(n);vm.runInThisContext('(function(require,module,exports){'+ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText+'\n})')(req,m,m.exports);return m.exports}
const wb=load(root+'/services/workbook-pricing.ts'),uni=load(root+'/services/unified-pricing.ts'),pricing=load(root+'/services/pricing.ts'),validation=load(root+'/db/validation.ts');
const close=(a,b,m)=>assert(Math.abs(a-b)<1e-9,(m||'')+' '+a+' != '+b);
const base={quantity:1000,costPerKg:17.5,rate:1,freight:3000,insurance:500,documents:0,other:200,margin:20,fees:0,taxes:[]};
const indirect=uni.indirectCostsFrom({version:1,indirectCosts:[{id:'a',name:'Aluguel',value:5000},{id:'b',name:'Contab.',value:1000}],monthlyRevenue:50000,updatedAt:'2026-10-14'});
close(indirect.rate,0.12,'taxa indireta');assert.equal(indirect.configured,true);
// 1) Reconciliação com o motor da planilha: mesmos insumos → mesmo preço.
const taxRev=[{id:'t',name:'DAS',enabled:true,mode:'percent',base:'revenue',rate:15,amount:0,customBase:0,addToPrice:true}];
const u=uni.calculateUnifiedPrice({...base,taxes:taxRev,indirect});
const w=wb.calculateWorkbookPrice({version:1,mode:'products',title:'',unit:'kg',currency:'BRL',rate:1,indirectCosts:[{id:'a',name:'Aluguel',value:5000},{id:'b',name:'Contab.',value:1000}],monthlyRevenue:50000,margin:20,taxes:[{id:'t',name:'DAS',enabled:true,rate:15}],directCosts:[{id:'d',name:'Custos',value:3700}],hourCost:0,hours:0,lines:[{id:'l',productId:'',name:'P',supplier:'',quantity:1000,unitCost:17.5}],serviceMargin:0,serviceTaxes:[],projectCosts:[],ownHourCost:0,ownHours:0,externalHourCost:0,externalHours:0,externalTaxRate:0});
close(u.totalBRL,w.totalBRL,'assistente x planilha');close(u.unitPrice,w.unitPrice,'unitário');
close(u.totalBRL,(17500+3700)/(1-0.12)/(1-0.2)/(1-0.15),'fórmula manual');
// 2) Comissões/despesas dividem o passo final junto com tributos.
const f=uni.calculateUnifiedPrice({...base,fees:5,taxes:taxRev,indirect});
close(f.totalBRL,(21200)/(1-0.12)/(1-0.2)/(1-0.15-0.05),'comissão no passo final');close(f.feeValue,f.totalBRL*0.05,'valor da comissão');
// 3) Tributo de custo (ex.: 10% sobre a operação) entra na base; tributo apenas registrado não altera o preço.
const duty={id:'d',name:'Imposto de custo',enabled:true,mode:'percent',base:'operation',rate:10,amount:0,customBase:0,addToPrice:true};
close(uni.calculateUnifiedPrice({...base,taxes:[duty],indirect}).totalBRL,(21200*1.1)/(1-0.12)/(1-0.2),'tributo de custo');
const rec=uni.calculateUnifiedPrice({...base,taxes:[{...duty,addToPrice:false}],indirect});close(rec.totalBRL,21200/(1-0.12)/(1-0.2),'tributo registrado');close(rec.recordedTaxTotal,2120,'registro');
// 4) Moeda: total em moeda da proposta = BRL ÷ câmbio.
const usd=uni.calculateUnifiedPrice({...base,rate:5.5,indirect});close(usd.total,usd.totalBRL/5.5,'câmbio');close(usd.unitPrice,usd.total/1000,'unitário USD');
// 5) Sem perfil: prévia sem indiretos, sinalizada; perfil inválido ou indiretos ≥ faturamento não passam.
const none=uni.indirectCostsFrom(undefined);assert.equal(none.configured,false);const pre=uni.calculateUnifiedPrice({...base,indirect:none});assert.equal(pre.model.indirectConfigured,false);close(pre.totalBRL,21200/0.8,'prévia sem indiretos');
assert.equal(uni.indirectCostsFrom({version:1,indirectCosts:[],monthlyRevenue:0,updatedAt:''}).configured,false);
assert.throws(()=>uni.indirectCostsFrom({version:1,indirectCosts:[{id:'a',name:'x',value:60000}],monthlyRevenue:50000,updatedAt:''}));
// 6) Entradas inválidas.
for(const bad of [{margin:100},{margin:-1},{fees:90,taxes:taxRev},{quantity:0},{rate:0},{freight:NaN}])assert.throws(()=>uni.calculateUnifiedPrice({...base,taxes:[],...bad,indirect}),undefined,JSON.stringify(bad));
// 7) Motor legado preservado (cotações antigas continuam recalculáveis) e persistência.
close(pricing.calculatePrice({...base}).revenue,21200/(1-0.2),'legado intacto');
const quote={id:'COT-1',product:'P',opportunityId:'',supplier:'S',incoterm:'FOB',currency:'BRL',quantity:1000,costPerKg:17.5,rate:1,total:1,unitPrice:1,createdAt:'2026-10-14'};
const data={ops:[],quotes:[quote,{...quote,id:'COT-2',pricingModel:u.model}],pricingProfile:{version:1,indirectCosts:[{id:'a',name:'Aluguel',value:5000}],monthlyRevenue:50000,updatedAt:'2026-10-14'}};
assert(validation.recordSchemas.commercial.safeParse(data).success);assert(!validation.recordSchemas.commercial.safeParse({...data,pricingProfile:{...data.pricingProfile,monthlyRevenue:0}}).success);
// 8) Valores calculados gravados na planilha original (Precificador Ibiag V1.xlsx, aba Produtos): linhas XXXXXX, YYYYY e NNNNN.
{const ind={configured:true,rate:6800/50000},direct=13500+200*10;
for(const [qty,unit,expected] of [[150,25,12036.064425770308],[300,49,36327.03081232493],[250,37,25166.316526610648]]){
 const r=uni.calculateUnifiedPrice({quantity:qty,costPerKg:unit,rate:5.55,freight:0,insurance:0,documents:0,other:qty/700*direct,margin:20,fees:0,taxes:taxRev,indirect:ind});
 close(r.totalBRL,expected,'linha do Excel '+qty);}}
console.log('PASS: motor único do assistente reconcilia com a planilha, comissões/tributos no passo final, tributo de custo, câmbio, perfil ausente/inválido, entradas inválidas, legado e persistência.');
