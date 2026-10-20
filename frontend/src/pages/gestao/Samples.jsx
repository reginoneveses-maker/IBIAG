
import {useEffect,useRef,useState} from "react";
import {api} from "@/AuthContext";
import OperationHistory from "@/components/OperationHistory";
import {PageHeader,Button,Input,Textarea,Card,CardContent,Dialog,DialogContent,DialogHeader,DialogTitle,DialogFooter,toast} from "@/components/erp";

export const sampleStates={requested:"Solicitada",preparing:"Em preparação",sent:"Enviada",delivered:"Entregue",evaluated:"Avaliada",cancelled:"Cancelada"};
const actions={preparing:"Iniciar preparação",sent:"Registrar envio",delivered:"Registrar entrega",evaluated:"Registrar avaliação",cancelled:"Cancelar solicitação"};
const terms=["quantity","unit","lot","packaging","recipient","address","destination_country","delivery_method","carrier","tracking_code","expected_delivery","follow_up_on","cost_amount","cost_currency","notes"];
const frozen=["quantity","unit","lot","packaging","recipient","address","destination_country","delivery_method"];
const defaults={quantity:"",unit:"g",lot:"",packaging:"",recipient:"",address:"",destination_country:"",delivery_method:"courier",carrier:"",tracking_code:"",expected_delivery:"",follow_up_on:"",cost_amount:"",cost_currency:"USD",notes:""};
const labels={quantity:"Quantidade da amostra",unit:"Unidade da amostra",lot:"Lote informado pelo fornecedor",packaging:"Embalagem da amostra",recipient:"Destinatário",address:"Endereço de entrega",destination_country:"País da entrega",delivery_method:"Forma de envio",carrier:"Transportadora ou responsável pela entrega",tracking_code:"Código de rastreio ou referência",expected_delivery:"Entrega prevista",follow_up_on:"Retorno previsto do comprador",cost_amount:"Custo total informado",cost_currency:"Moeda do custo",notes:"Observações"};
const selectClass="w-full border rounded-md p-2 bg-white text-sm";
const error=e=>typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível concluir. Confira a conexão e recarregue.";
const today=()=>{const d=new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10);};
async function allLeads(){
 const rows=[];for(let offset=0;offset<25000;offset+=250){
  const r=await api.get("/leads",{params:{skip:offset,limit:250}});if(!Array.isArray(r.data))throw new Error("Invalid CRM response");
  rows.push(...r.data);if(r.data.length<250)return rows;
 }throw new Error("CRM acima do limite de seleção; solicite revisão.");
}

export default function Samples(){
 const [records,setRecords]=useState([]),[filter,setFilter]=useState(""),[skip,setSkip]=useState(0),[revision,setRevision]=useState(0),[loading,setLoading]=useState(false),[listError,setListError]=useState("");
 const [detail,setDetail]=useState(null),[isNew,setIsNew]=useState(false),[form,setForm]=useState(defaults),[opening,setOpening]=useState(false),[openError,setOpenError]=useState(""),[saving,setSaving]=useState(false);
 const [leads,setLeads]=useState([]),[products,setProducts]=useState([]),[offers,setOffers]=useState([]),[offerError,setOfferError]=useState(""),[offerLoading,setOfferLoading]=useState(false);
 const [decisionDate,setDecisionDate]=useState(""),[feedback,setFeedback]=useState(""),[outcome,setOutcome]=useState(""),[confirmed,setConfirmed]=useState(false);
 const sequence=useRef(0),offerSequence=useRef(0),busy=useRef(false),lastOpen=useRef(null);
 useEffect(()=>{let active=true;setLoading(true);setListError("");setRecords([]);
  api.get("/samples",{params:{status:filter||undefined,skip,limit:50}}).then(r=>{if(active)setRecords(r.data);}).catch(e=>{if(active)setListError(error(e));}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[filter,skip,revision]);
 useEffect(()=>()=>{sequence.current+=1;offerSequence.current+=1;},[]);
 const apply=data=>{setDetail(data);setIsNew(false);setForm({...defaults,...Object.fromEntries(terms.map(k=>[k,data[k]??defaults[k]])),change_note:""});setDecisionDate("");setFeedback("");setOutcome("");setConfirmed(false);};
 const open=async(id=null)=>{
  if(busy.current)return;lastOpen.current=id;const seq=++sequence.current;offerSequence.current+=1;setOpening(true);setOpenError("");setDetail(null);setIsNew(false);setOffers([]);setOfferError("");
  try{
   if(id){const r=await api.get("/samples/"+encodeURIComponent(id));if(seq===sequence.current)apply(r.data);}
   else{
    const [companies,catalog]=await Promise.all([allLeads(),api.get("/products")]);if(seq!==sequence.current)return;
    const id=crypto.randomUUID();setLeads(companies);setProducts(catalog.data);setIsNew(true);setDetail({id});
    setForm({...defaults,reference:"AM-"+today()+"-"+id.slice(0,8),lead_id:"",product_id:"",offer_id:"",requested_on:today(),change_note:""});
   }
  }catch(e){if(seq===sequence.current)setOpenError(error(e));}finally{if(seq===sequence.current)setOpening(false);}
 };
 const close=()=>{if(busy.current)return;sequence.current+=1;offerSequence.current+=1;setDetail(null);setOpening(false);setOpenError("");};
 const change=(key,value)=>setForm(previous=>({...previous,[key]:value}));
 const selectProduct=async(id)=>{
  change("product_id",id);change("offer_id","");setOffers([]);setOfferError("");const seq=++offerSequence.current;
  if(!id){setOfferLoading(false);return;}setOfferLoading(true);
  try{const r=await api.get("/product-offers",{params:{product_id:id,active:true}});
   if(seq!==offerSequence.current)return;
   if(!Array.isArray(r.data)||r.data.length>=2000)throw new Error("Offer limit");
   setOffers(r.data.filter(o=>o.product_id===id&&o.active!==false));
  }catch(e){if(seq===offerSequence.current)setOfferError("Não foi possível carregar todas as ofertas. Você pode registrar sem fornecedor ou tentar selecionar o produto novamente.");}
  finally{if(seq===offerSequence.current)setOfferLoading(false);}
 };
 const dirty=!!detail&&!isNew&&terms.some(k=>form[k]!==detail[k]);
 const reason=(form.change_note||"").trim().length>=3;
 const save=async(state)=>{
  if(!detail||busy.current)return;busy.current=true;setSaving(true);
  try{
   let r;if(state){
    r=await api.post("/samples/"+encodeURIComponent(detail.id)+"/status",{version:detail.version,status:state,change_note:form.change_note,
     occurred_on:["sent","delivered","evaluated"].includes(state)?decisionDate:"",
     feedback_result:state==="evaluated"?outcome:"",feedback:state==="evaluated"?feedback:""});
   }else{
    const payload={...Object.fromEntries(terms.map(k=>[k,form[k]])),change_note:form.change_note};
    r=isNew?await api.post("/samples",{...payload,id:detail.id,reference:form.reference,lead_id:form.lead_id,product_id:form.product_id,offer_id:form.offer_id,requested_on:form.requested_on}):
     await api.put("/samples/"+encodeURIComponent(detail.id),{...payload,version:detail.version});
   }
   apply(r.data);setRevision(v=>v+1);toast.success(state?"Etapa da amostra registrada.":"Amostra salva.");
  }catch(e){toast.error(error(e));}finally{busy.current=false;setSaving(false);}
 };
 const locked=!isNew&&!detail?.can_edit;
 const dispatched=!isNew&&["sent","delivered","evaluated"].includes(detail?.status);
 const allowed=isNew?[]:detail?.allowed_statuses||[];
 const disableField=key=>saving||locked||(dispatched&&frozen.includes(key));
 const canSave=reason&&form.quantity&&(!isNew||(form.reference?.trim()&&form.lead_id&&form.product_id&&form.requested_on));
 const options={unit:{g:"g",kg:"kg",mL:"mL",L:"L",unit:"Unidade"},delivery_method:{courier:"Courier",postal:"Correios",hand:"Em mãos",air:"Aéreo",sea:"Marítimo",road:"Rodoviário"},cost_currency:{USD:"USD",BRL:"BRL",EUR:"EUR"}};
 return <div data-testid="samples-page">
  <PageHeader title="Amostras" subtitle="Do pedido de amostra ao retorno do comprador" action={<Button disabled={saving} onClick={()=>open()}>Nova amostra</Button>}/>
  <p className="text-sm mb-4">Uma solicitação por produto. Quantidade e unidade pertencem à amostra, sem conversão automática. Este registro não baixa estoque, não cria cobrança e não contrata transporte.</p>
  <div className="flex flex-wrap items-end gap-3 mb-4"><label>Situação da amostra<select aria-label="Situação da amostra" className={selectClass} value={filter} onChange={e=>{setFilter(e.target.value);setSkip(0);}}><option value="">Todas</option>{Object.entries(sampleStates).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label><Button variant="outline" onClick={()=>setRevision(v=>v+1)}>Atualizar lista</Button></div>
  {loading&&<p role="status">Carregando amostras…</p>}{listError&&<p role="alert">{listError}</p>}{!loading&&!listError&&!records.length&&<p>Nenhuma amostra nesta página.</p>}
  <div className="space-y-3">{records.map(r=><Card key={r.id}><CardContent className="p-4 flex flex-wrap items-center gap-3"><div className="flex-1 min-w-0 break-words"><strong>{r.reference} — {r.customer}</strong><p>{r.product_name} · {r.quantity} {r.unit==="unit"?"unidade":r.unit} · {sampleStates[r.status]}</p><p className="text-sm">Solicitada em {r.requested_on}{r.follow_up_on?" · Retorno previsto: "+r.follow_up_on:""}</p></div><Button variant="outline" disabled={saving} onClick={()=>open(r.id)}>Abrir amostra {r.reference}</Button></CardContent></Card>)}</div>
  <div className="flex gap-3 mt-4"><Button variant="outline" disabled={skip===0||loading} onClick={()=>setSkip(v=>Math.max(0,v-50))}>Página anterior</Button><Button variant="outline" disabled={loading||records.length<50} onClick={()=>setSkip(v=>v+50)}>Próxima página</Button></div>
  <Dialog open={!!detail||opening||!!openError} onOpenChange={value=>{if(!value)close();}}><DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>{isNew?"Nova amostra":detail?"Amostra "+detail.reference:"Abrir amostra"}</DialogTitle></DialogHeader>
   {opening&&<p role="status">Carregando dados…</p>}{openError&&<div><p role="alert">{openError}</p><Button variant="outline" onClick={()=>open(lastOpen.current)}>Tentar abrir novamente</Button></div>}
   {detail&&!opening&&<>
    {isNew?<div className="grid sm:grid-cols-2 gap-3">
     <label>Referência da amostra<Input aria-label="Referência da amostra" value={form.reference} onChange={e=>change("reference",e.target.value)}/></label>
     <label>Data da solicitação<Input aria-label="Data da solicitação" type="date" value={form.requested_on} onChange={e=>change("requested_on",e.target.value)}/></label>
     <label>Empresa do CRM<select aria-label="Empresa do CRM" className={selectClass} value={form.lead_id} onChange={e=>change("lead_id",e.target.value)}><option value="">Selecione</option>{leads.map((l,i)=><option key={l.id+"-"+i} value={l.id}>{l.company}</option>)}</select></label>
     <label>Produto da amostra<select aria-label="Produto da amostra" className={selectClass} value={form.product_id} onChange={e=>selectProduct(e.target.value)}><option value="">Selecione</option>{products.map((p,i)=><option key={p.id+"-"+i} value={p.id}>{p.name}</option>)}</select></label>
     <label>Oferta e fornecedor<select aria-label="Oferta e fornecedor" className={selectClass} disabled={offerLoading||!form.product_id} value={form.offer_id} onChange={e=>change("offer_id",e.target.value)}><option value="">Sem oferta vinculada</option>{offers.map((o,i)=><option key={o.id+"-"+i} value={o.id}>{o.supplier_name||"Fornecedor da oferta"} · {o.id}</option>)}</select></label>
     {offerLoading&&<p role="status">Carregando ofertas…</p>}{offerError&&<p role="alert">{offerError}</p>}
    </div>:<section aria-label="Origem da amostra" className="rounded-lg bg-slate-50 p-3 text-sm break-words"><p><strong>{detail.customer}</strong> · {detail.customer_country||"País do cliente não informado"}</p><p>{detail.product_name} · {detail.supplier_name||"Sem fornecedor vinculado"}</p><p>Solicitada em {detail.requested_on} · {sampleStates[detail.status]}</p>{detail.sent_on&&<p>Envio: {detail.sent_on}</p>}{detail.delivered_on&&<p>Entrega: {detail.delivered_on}</p>}{detail.evaluated_on&&<p>Avaliação: {detail.evaluated_on} · {{approved:"Aprovada pelo comprador",rejected:"Reprovada pelo comprador",retest:"Novo teste solicitado"}[detail.feedback_result]} — {detail.feedback}</p>}{detail.delivery_overdue&&<p className="text-amber-800">Entrega prevista vencida; confira com a transportadora.</p>}{detail.feedback_overdue&&<p className="text-amber-800">Retorno previsto vencido; acompanhe com o comprador.</p>}</section>}
    <div className="grid sm:grid-cols-2 gap-3 mt-4">{terms.map(key=><label key={key} className={["address","notes"].includes(key)?"sm:col-span-2":""}>{labels[key]}
     {options[key]?<select aria-label={labels[key]} className={selectClass} disabled={disableField(key)} value={form[key]} onChange={e=>change(key,e.target.value)}>{Object.entries(options[key]).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select>:
      ["address","notes"].includes(key)?<Textarea aria-label={labels[key]} disabled={disableField(key)} value={form[key]} onChange={e=>change(key,e.target.value)}/>:
      <Input aria-label={labels[key]} disabled={disableField(key)} type={["expected_delivery","follow_up_on"].includes(key)?"date":"text"} inputMode={["quantity","cost_amount"].includes(key)?"decimal":undefined} value={form[key]} onChange={e=>change(key,["quantity","cost_amount"].includes(key)?e.target.value.replace(",","."):e.target.value)}/>}
    </label>)}</div>
    <p className="text-xs mt-2">Lote e informações de envio são conferidos manualmente. Custo em branco significa não informado; não há soma entre moedas nem lançamento financeiro.</p>
    {!locked&&<label className="block mt-4">Motivo do registro ou decisão<Textarea aria-label="Motivo do registro ou decisão" maxLength={300} disabled={saving} value={form.change_note||""} onChange={e=>change("change_note",e.target.value)}/></label>}
    {!isNew&&allowed.length>0&&<section className="space-y-3 border-t pt-4 mt-4" aria-label="Próxima etapa da amostra">
     {allowed.some(s=>["sent","delivered","evaluated"].includes(s))&&<label>Data real da próxima etapa<Input aria-label="Data real da próxima etapa" type="date" disabled={saving} value={decisionDate} onChange={e=>setDecisionDate(e.target.value)}/></label>}
     {allowed.includes("evaluated")&&<><label>Resultado do comprador<select aria-label="Resultado do comprador" className={selectClass} value={outcome} disabled={saving} onChange={e=>setOutcome(e.target.value)}><option value="">Selecione</option><option value="approved">Aprovada</option><option value="rejected">Reprovada</option><option value="retest">Novo teste solicitado</option></select></label><label>Retorno do comprador<Textarea aria-label="Retorno do comprador" disabled={saving} value={feedback} onChange={e=>setFeedback(e.target.value)}/></label><p className="text-xs">Registrar aprovação não cria pedido. Novo teste exige outra solicitação de amostra.</p></>}
     <label className="flex gap-2"><input type="checkbox" checked={confirmed} disabled={saving} onChange={e=>setConfirmed(e.target.checked)}/>Conferi os dados desta etapa</label>
     <div className="flex flex-wrap gap-2">{allowed.map(state=><Button key={state} variant={state==="cancelled"?"outline":undefined} disabled={saving||dirty||!reason||!confirmed||(["sent","delivered","evaluated"].includes(state)&&!decisionDate)||(state==="evaluated"&&(!outcome||!feedback.trim()))} onClick={()=>save(state)}>{actions[state]}</Button>)}</div>
     {dirty&&<p className="text-sm">Salve as alterações antes de registrar uma etapa.</p>}
    </section>}
    {!isNew&&<div className="mt-4"><OperationHistory kind="sample" resourceId={detail.id} version={detail.version} recent={detail.history} archived={!!detail.history_archive?.count} onReload={()=>open(detail.id)} disabled={saving}/></div>}
   </>}
   <DialogFooter className="flex flex-wrap gap-2 mt-4"><Button variant="outline" disabled={saving} onClick={close}>Fechar</Button>{detail&&!opening&&!isNew&&<Button variant="outline" disabled={saving} onClick={()=>open(detail.id)}>Recarregar amostra</Button>}{detail&&!opening&&!locked&&<Button disabled={saving||!canSave} onClick={()=>save()}>Salvar amostra</Button>}</DialogFooter>
  </DialogContent></Dialog>
 </div>;
}
