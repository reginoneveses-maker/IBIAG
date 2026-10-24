'use client';
import {useEffect,useState,useRef} from 'react';
import {parseDecimal} from '@/services/pricing';
import ProductQuoteSettings from './ProductQuoteSettings';
import {validateProductQuoteProfile,readProductQuoteSettings,productQuoteReadiness,emptyProductQuoteSettings} from '@/services/product-quote';
import PackagingEditor from './logistics/PackagingEditor';
import {packageListSchema} from '@/services/logistics';
import {createRecordSession} from '@/services/workspace';
const groups=[{title:'Produto, fornecedor e disponibilidade',fields:[['supplier','Fornecedor'],['manufacturer','Fabricante'],['origin','Cidade / país da fábrica'],['pickupAddress','Endereço de coleta e CEP'],['supplierContact','Contato da expedição'],['supplierEmail','E-mail da expedição'],['supplierPhone','Telefone da expedição'],['productCode','Código do fornecedor'],['processing','Forma / processamento'],['composition','Composição e parâmetros'],['moqKg','Pedido mínimo (kg)'],['leadDays','Prazo para disponibilizar (dias)'],['leadTime','Condições e prazo de entrega'],['shelfLife','Validade do produto'],['storage','Armazenamento'],['allergens','Alergênicos / OGM'],['certifications','Certificações e laudos'],['packaging','Resumo da embalagem'],['quantityDiscounts','Faixas de preço por quantidade / condições']]},{title:'Preço e condições para a cotação automática',fields:[['priceCurrency','Moeda do preço do fornecedor'],['cost','Preço do fornecedor por kg'],['priceRate','Câmbio do preço: BRL por unidade da moeda'],['priceValidUntil','Preço válido até'],['supplierPriceTerm','Condição / local do preço do fornecedor'],['paymentTerms','Condições de pagamento'],['quoteAliases','Nomes usados nos pedidos (separados por vírgula)'],['quoteCurrency','Moeda padrão da proposta'],['quoteRate','Câmbio da proposta: BRL por unidade da moeda'],['quoteMargin','Margem padrão sobre receita (%)'],['quoteFees','Outras comissões / despesas sobre receita (%)']]}];
const numeric=['cost','priceRate','moqKg','leadDays','quoteRate','quoteMargin','quoteFees'];
type Profile={id:string;[key:string]:string};
export default function ProductProfile({productId}:{productId:string}) {
const {readRecords,writeRecords}=useState(createRecordSession)[0];
const [all,setAll]=useState<Profile[]>([]),[values,setValues]=useState<Profile>({id:productId}),[ready,setReady]=useState(false),[loadError,setLoadError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
const loadVersion=useRef(0),saveLock=useRef(false);
async function load(){const version=++loadVersion.current;setReady(false);setLoadError('');try{const items=await readRecords<Profile[]>('products');if(version!==loadVersion.current)return;setAll(items);setValues(items.find(p=>p.id===productId)||{id:productId,priceCurrency:'BRL'});setReady(true)}catch(e){if(version===loadVersion.current)setLoadError((e as Error).message)}}
useEffect(()=>{if(!message)return;const timer=setTimeout(()=>setMessage(''),6000);return()=>clearTimeout(timer)},[message]);
useEffect(()=>{setMessage('');void load();return()=>{loadVersion.current++}},[productId]);
let packaging;let packagingDraft:any[]=[];try{const raw=JSON.parse(values.logistics||'[]');if(Array.isArray(raw))packagingDraft=raw;packaging=packageListSchema.safeParse(raw)}catch{packaging=undefined}
async function save(e:React.FormEvent<HTMLFormElement>){
e.preventDefault();if(saveLock.current)return;saveLock.current=true;setBusy(true);setMessage('');
try{
let raw;try{raw=JSON.parse(values.logistics||'[]')}catch{throw new Error('Revise as embalagens: o cadastro salvo está em formato inválido.')}
const parsed=packageListSchema.safeParse(raw);if(!parsed.success)throw new Error(parsed.error.issues.map(i=>i.message).join(' · '));
validateProductQuoteProfile(values);
const normalized:Profile={...values,quoteCurrency:(values.quoteCurrency||'').trim().toUpperCase()};if(normalized.quoteCurrency==='BRL')normalized.quoteRate='1';if(!normalized.priceCurrency)normalized.priceCurrency='BRL';if(normalized.priceCurrency==='BRL')normalized.priceRate='1';normalized.quoteSettings=JSON.stringify(readProductQuoteSettings(values.quoteSettings)||emptyProductQuoteSettings());
const next=[...all.filter(p=>p.id!==productId),normalized];await writeRecords('products',next);setAll(next);setValues(normalized);setMessage('Ficha salva no sistema.');
}catch(e){setMessage((e as Error).message)}finally{saveLock.current=false;setBusy(false)}
}
return <section><h3>Informações operacionais do produto</h3><p className="form-note">Preencha com dados confirmados do fornecedor. O portfólio original permanece preservado.</p>
{loadError?<div role="alert"><p>{loadError}</p><button className="btn" onClick={load}>Tentar novamente</button></div>:!ready?<p role="status">Carregando ficha…</p>:<form onSubmit={save}>
{groups.map(group=><section className="product-profile-group" key={group.title}><h4>{group.title}</h4><div className="form-grid">{group.fields.map(([key,label])=><label key={key}>{label}{['quoteCurrency','priceCurrency'].includes(key)?<select value={values[key]||''} onChange={e=>setValues({...values,[key]:e.target.value,...(e.target.value==='BRL'?{[key==='priceCurrency'?'priceRate':'quoteRate']:'1'}:{})})}><option value="">Selecionar moeda</option>{['BRL','USD','EUR'].map(c=><option key={c}>{c}</option>)}</select>:<input maxLength={1000} type={key==='priceValidUntil'?'date':'text'} inputMode={numeric.includes(key)?'decimal':'text'} value={values[key]||''} placeholder="Não informado" onChange={e=>setValues({...values,[key]:e.target.value})}/>}</label>)}</div></section>)}
<ProductQuoteSettings value={values.quoteSettings||''} onChange={raw=>setValues({...values,quoteSettings:raw})}/>

{!packaging?.success&&<p role="alert" className="logistics-warning">O cadastro de embalagens precisa de revisão. Os dados atuais serão preservados até você cadastrar uma opção válida.</p>}
<PackagingEditor options={packagingDraft} onChange={items=>setValues({...values,logistics:JSON.stringify(items)})} supplier={values.supplier||''} origin={values.origin||''} pickupAddress={values.pickupAddress||''}/>
<div className="product-quote-status"><b>Preparação do cadastro para cotações</b>{(()=>{try{const pending=productQuoteReadiness(values);return pending.length?<p>Falta preencher: {pending.join(' · ')}</p>:<p>Dados principais preenchidos. Confira custos além do frete e embalagens para a quantidade de cada pedido.</p>}catch{return <p>Revise a configuração de cotação.</p>}})()}</div>
<button className="btn primary" disabled={busy}>{busy?'Salvando…':'Salvar informações do produto'}</button></form>}
<p role="status">{message}</p>{message==='Ficha salva no sistema.'&&<div className="toast" role="status">Dados do produto salvos para as próximas cotações.</div>}</section>}
