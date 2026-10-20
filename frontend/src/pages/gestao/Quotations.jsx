import OperationHistory from "@/components/OperationHistory";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast } from "@/components/erp";
import { priceMoney } from "@/lib/pricing";
const fmtUSD=value=>priceMoney(value,"USD");

const terms=["valid_until","incoterm","payment_terms","delivery_terms","notes"];
const labels={draft:"Rascunho",approved:"Aprovada internamente",cancelled:"Cancelada"};
const defaults={valid_until:"",incoterm:"FOB",payment_terms:"",delivery_terms:"",notes:"",change_note:""};
const selectClass="border rounded-md p-2 bg-white w-full text-sm";
const error=e=>typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível concluir. Confira a conexão e recarregue.";
export default function Quotations(){
  const [params,setParams]=useSearchParams(), requestedPrice=params.get("price"),requestedQuote=params.get("quote");
  const [records,setRecords]=useState([]),[status,setStatus]=useState(""),[skip,setSkip]=useState(0),[retry,setRetry]=useState(0),[loading,setLoading]=useState(false),[listError,setListError]=useState(false);
  const [detail,setDetail]=useState(null),[form,setForm]=useState(defaults),[isNew,setIsNew]=useState(false),[leads,setLeads]=useState([]),[opening,setOpening]=useState(false),[openError,setOpenError]=useState(""),[saving,setSaving]=useState(false);
  const request=useRef(0),busy=useRef(false);
  useEffect(()=>{let active=true;setLoading(true);setListError(false);setRecords([]);
    api.get("/quotations",{params:{status:status||undefined,skip,limit:50}}).then(r=>{if(active)setRecords(r.data);}).catch(()=>{if(active)setListError(true);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[status,skip,retry]);
  const apply=useCallback(data=>{setDetail(data);setIsNew(false);setForm({...defaults,...Object.fromEntries(terms.map(k=>[k,data[k]??defaults[k]]))});},[]);
  const open=useCallback(async(id,price)=>{
    if(busy.current)return;const seq=++request.current;setOpening(true);setOpenError("");setDetail(null);
    setParams(current=>{const next=new URLSearchParams(current);next.delete("price");next.delete("quote");return next;},{replace:true});
    try{
      if(id&&price)throw new Error("ambiguous");
      if(id){const r=await api.get(`/quotations/${encodeURIComponent(id)}`);if(seq===request.current)apply(r.data);}
      else{
        const source=await api.get(`/prices/${encodeURIComponent(price)}/order-draft`);const all=[];let offset=0;
        while(seq===request.current){const r=await api.get("/leads",{params:{skip:offset,limit:250}});all.push(...r.data);if(r.data.length<250)break;offset+=250;}
        if(seq===request.current){const id=crypto.randomUUID();setLeads(all);setDetail({...source.data,id});setIsNew(true);setForm({...defaults,reference:`COT-${new Date().toISOString().slice(0,10)}-${id.slice(0,8)}`,lead_id:""});}
      }
    }catch(e){if(seq===request.current)setOpenError(error(e));}finally{if(seq===request.current)setOpening(false);}
  },[apply,setParams]);
  useEffect(()=>{if(requestedPrice||requestedQuote)open(requestedQuote,requestedPrice);},[requestedPrice,requestedQuote,open]);
  useEffect(()=>()=>{request.current+=1;},[]);
  const close=()=>{if(busy.current)return;request.current+=1;setDetail(null);setOpening(false);setOpenError("");};
  const change=(k,v)=>setForm(f=>({...f,[k]:v}));
  const dirty=!!detail&&!isNew&&terms.some(k=>form[k]!==detail[k]);
  const save=async(nextStatus)=>{
    if(!detail||busy.current)return;busy.current=true;setSaving(true);
    try{
      let r;
      if(nextStatus)r=await api.post(`/quotations/${encodeURIComponent(detail.id)}/status`,{version:detail.version,status:nextStatus,change_note:form.change_note});
      else{const body={...Object.fromEntries(terms.map(k=>[k,form[k]])),change_note:form.change_note};
        r=isNew?await api.post("/quotations",{...body,id:detail.id,reference:form.reference,lead_id:form.lead_id,source_price_id:detail.source_price_id,source_price_revision:detail.source_price_revision}):await api.put(`/quotations/${encodeURIComponent(detail.id)}`,{...body,version:detail.version});}
      apply(r.data);setRetry(n=>n+1);toast.success(nextStatus==="approved"?"Cotação aprovada internamente.":nextStatus==="cancelled"?"Cotação cancelada.":"Cotação salva.");
    }catch(e){toast.error(error(e));}finally{busy.current=false;setSaving(false);}
  };
  const editable=isNew||detail?.status==="draft",reason=form.change_note.trim().length>=3;
  const valid=reason&&form.valid_until&&form.payment_terms.trim().length>=3&&form.delivery_terms.trim().length>=3&&(!isNew||(form.lead_id&&form.reference.trim()));
  return <div data-testid="quotations-page">
    <PageHeader title="Cotações comerciais" subtitle="Condições, aprovação interna e memória dos valores em USD" action={<Link className="underline" to="/gestao/precos">Escolher cálculo</Link>}/>
    <p className="text-sm mb-4">Crie a cotação a partir de um cálculo salvo. A aprovação é interna da IBIAG; envio e aceite do comprador são tratados separadamente. Aprovar não movimenta estoque nem financeiro.</p>
    <div className="flex flex-wrap items-end gap-3 mb-4"><label>Situação da cotação<select aria-label="Situação da cotação" className={selectClass} value={status} onChange={e=>{setStatus(e.target.value);setSkip(0);}}><option value="">Todas</option>{Object.entries(labels).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label><Button variant="outline" onClick={()=>setRetry(n=>n+1)}>Atualizar lista</Button></div>
    {loading&&<p role="status">Carregando cotações…</p>}{listError&&<p role="alert">Não foi possível carregar as cotações. Use Atualizar lista.</p>}
    {!loading&&!listError&&!records.length&&<p>Nenhuma cotação nesta página.</p>}
    <div className="space-y-3">{records.map(q=><Card key={q.id}><CardContent className="p-4 flex flex-wrap items-center gap-3"><div className="flex-1"><strong>{q.reference} — {q.customer}</strong><p>{labels[q.status]} · validade {q.valid_until} · {q.incoterm}</p>{q.linked_order_id&&<Link className="underline text-sm" to="/gestao/pedidos">Pedido já gerado</Link>}</div><strong>{fmtUSD(q.total_usd)}</strong><Button variant="outline" disabled={saving} onClick={()=>open(q.id)}>Abrir cotação</Button></CardContent></Card>)}</div>
    <div className="flex gap-3 items-center my-4"><Button disabled={!skip||loading} onClick={()=>setSkip(n=>Math.max(0,n-50))}>Anterior</Button><span>Página {skip/50+1}</span><Button disabled={records.length<50||loading} onClick={()=>setSkip(n=>n+50)}>Próxima</Button></div>
    {opening&&<p role="status">Preparando cotação…</p>}{openError&&<p role="alert">{openError} Abra novamente pelo cálculo ou pela lista.</p>}
    <Dialog open={!!detail} onOpenChange={v=>{if(!v)close();}}><DialogContent className="bg-white max-w-3xl max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>{isNew?"Nova cotação comercial":`Cotação ${detail?.reference}`}</DialogTitle></DialogHeader>
    {detail&&<><p>{isNew?"Confira os valores e informe as condições.":`${labels[detail.status]} · versão ${detail.version}`}</p>
      {isNew?<fieldset disabled={saving} className="grid sm:grid-cols-2 gap-3"><label>Referência<Input maxLength={80} value={form.reference} onChange={e=>change("reference",e.target.value)}/></label><label>Empresa do CRM<select aria-label="Empresa do CRM" className={selectClass} value={form.lead_id} onChange={e=>change("lead_id",e.target.value)}><option value="">Selecione</option>{leads.map(l=><option key={l.id} value={l.id}>{l.company}{l.country?` · ${l.country}`:""}</option>)}</select></label></fieldset>:<p><strong>{detail.customer}</strong> · {detail.customer_country}</p>}
      <div className="rounded-lg bg-slate-50 p-4 space-y-2" aria-label="Valores da cotação">{detail.items?.map((i,n)=><p key={n}>{i.product_name} · {i.supplier_name} · {i.quantity} {i.unit} × {priceMoney(i.unit_price,"USD",true)}</p>)}<strong>Total: {fmtUSD(detail.total_usd)}</strong><p className="text-xs">Valores preservados do cálculo conferido. Mudanças de preço ou comprador exigem uma nova cotação.</p></div>
      <fieldset disabled={!editable||saving} className="grid sm:grid-cols-2 gap-3"><label>Validade até<Input type="date" value={form.valid_until} onChange={e=>change("valid_until",e.target.value)}/></label><label>Incoterm<select aria-label="Incoterm da cotação" className={selectClass} value={form.incoterm} onChange={e=>change("incoterm",e.target.value)}>{["EXW","FOB","FCA","CFR","CIF","CPT","CIP","DAP","DPU","DDP"].map(v=><option key={v}>{v}</option>)}</select></label><label>Condições de pagamento<Textarea maxLength={1000} value={form.payment_terms} onChange={e=>change("payment_terms",e.target.value)}/></label><label>Condições de entrega<Textarea maxLength={1000} value={form.delivery_terms} onChange={e=>change("delivery_terms",e.target.value)}/></label><label className="sm:col-span-2">Observações comerciais<Textarea maxLength={2000} value={form.notes} onChange={e=>change("notes",e.target.value)}/></label></fieldset>
      {(isNew||(!detail.linked_order_id&&detail.status!=="cancelled"))&&<label>Motivo do registro ou decisão<Textarea disabled={saving} maxLength={300} value={form.change_note} onChange={e=>change("change_note",e.target.value)}/></label>}
      {detail.expired&&<p role="status">Cotação vencida. Crie uma nova cotação para outra venda.</p>}{dirty&&<p role="status">Salve as condições antes de aprovar ou cancelar.</p>}
      {detail.linked_order_id?<Link className="underline" to="/gestao/pedidos">Consultar pedido gerado</Link>:!isNew&&detail.can_order&&!dirty&&<Link className="underline font-semibold" to={`/prospects/orders?quote=${encodeURIComponent(detail.id)}`}>Preparar pedido em rascunho</Link>}
    {!isNew&&<OperationHistory kind="quotation" resourceId={detail.id} version={detail.version} recent={detail?.history||[]} archived={!!detail?.history_archive} disabled={saving} onReload={()=>open(detail.id)}/>}
    </>}
    <DialogFooter className="flex-wrap gap-2"><Button variant="outline" disabled={saving} onClick={close}>Fechar</Button>{!isNew&&<Button variant="outline" disabled={saving} onClick={()=>open(detail.id)}>Recarregar cotação</Button>}{editable&&<Button disabled={saving||!valid} onClick={()=>save()}>Salvar cotação</Button>}{!isNew&&detail?.status==="draft"&&<Button disabled={saving||dirty||!reason||detail.expired} onClick={()=>save("approved")}>Aprovar internamente</Button>}{!isNew&&detail?.status!=="cancelled"&&!detail?.linked_order_id&&<Button variant="outline" disabled={saving||dirty||!reason} onClick={()=>save("cancelled")}>Cancelar cotação</Button>}</DialogFooter>
    </DialogContent></Dialog>
  </div>;
}
