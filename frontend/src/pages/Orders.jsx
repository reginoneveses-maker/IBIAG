import { useCallback, useEffect, useRef, useState } from "react";
import { api, useAuth } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast, Plus } from "@/components/erp";
import { Link, useSearchParams } from "react-router-dom";
import { fmtUSD } from "@/lib/api";

const empty = { number:"", customer:"", customer_country:"", lead_id:"", products:"", incoterm:"FOB", total_usd:0, status:"draft", order_date:"", delivery_date:"", receivable_due_date:"", notes:"", items:[], track_stock:false, version:0 };
const statuses = { draft:"Rascunho", confirmed:"Confirmado", shipped:"Embarcado", delivered:"Entregue", cancelled:"Cancelado" };
const error = e => typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Não foi possível concluir. Recarregue e tente novamente.";
const selectClass = "border rounded-md p-2 bg-white w-full text-sm";

export default function Orders() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const requestedLead = params.get("lead");
  const sourceRequest = useRef(0);
  const [leads, setLeads] = useState([]), [sourceLead, setSourceLead] = useState(null);
  const [leadLoadError, setLeadLoadError] = useState(false), [loadingLeads, setLoadingLeads] = useState(false), [retryLeads, setRetryLeads] = useState(0);
  const [canChangeCustomer, setCanChangeCustomer] = useState(true);
  const [records,setRecords]=useState([]), [offers,setOffers]=useState([]), [dialog,setDialog]=useState(false), [form,setForm]=useState(empty), [isNew,setIsNew]=useState(false), [saving,setSaving]=useState(false), [archived,setArchived]=useState(false);
  const load=useCallback(()=>api.get("/orders",{params:{archived}}).then(r=>setRecords(r.data)).catch(e=>toast.error(error(e))),[archived]);
  useEffect(()=>{load();},[load]);
  useEffect(()=>{api.get("/product-offers").then(r=>setOffers(r.data)).catch(e=>toast.error(error(e)));},[]);
  const open=useCallback((record, lead=null)=>{
    sourceRequest.current+=1;
    setForm(record?{...empty,...record,items:(record.items||[]).map(x=>({...x}))}:{...empty,id:crypto.randomUUID(),order_date:new Date().toISOString().slice(0,10),items:[],...(lead?{lead_id:lead.id,customer:lead.company,customer_country:lead.country||""}:{})});
    setCanChangeCustomer(!record || record.status === "draft");
    setIsNew(!record);setDialog(true);
  },[]);
  useEffect(()=>{
    if(!requestedLead || user?.role!=="admin")return;
    let active=true;
    const request=++sourceRequest.current;
    api.get(`/leads/${encodeURIComponent(requestedLead)}`).then(r=>{if(active && request===sourceRequest.current){setSourceLead(r.data);open(null,r.data);}})
      .catch(()=>{if(active && request===sourceRequest.current)toast.error("Não foi possível abrir a empresa do CRM. Nenhum pedido foi criado.");});
    return ()=>{active=false;};
  },[requestedLead,user?.role,open]);
  useEffect(()=>{
    if(!dialog || user?.role!=="admin")return;
    let active=true;
    setLoadingLeads(true);setLeadLoadError(false);
    (async()=>{
      const all=[];let skip=0;
      while(active){
        const r=await api.get("/leads",{params:{skip,limit:250}});
        all.push(...r.data);
        if(r.data.length<250)break;
        skip+=250;
      }
      if(active)setLeads(all);
    })().catch(()=>{if(active)setLeadLoadError(true);}).finally(()=>{if(active)setLoadingLeads(false);});
    return ()=>{active=false;};
  },[dialog,user?.role,retryLeads]);
  const customerOptions=sourceLead&&!leads.some(l=>l.id===sourceLead.id)?[sourceLead,...leads]:leads;
  const chooseCustomer=id=>{
    const lead=customerOptions.find(l=>l.id===id);
    setForm(f=>({...f,lead_id:id,customer:lead?.company||"",customer_country:lead?.country||""}));
  };
  const change=(key,value)=>setForm(f=>({...f,[key]:value}));
  const changeItem=(index,changes)=>setForm(f=>({...f,items:f.items.map((x,i)=>i===index?{...x,...changes}:x)}));
  const chooseOffer=(index,id)=>{const o=offers.find(x=>x.id===id);changeItem(index,{offer_id:id,product_id:o?.product_id||"",product_name:o?.product_name||"",supplier_id:o?.supplier_id||"",supplier_name:o?.supplier_name||"",unit:o?.unit||"kg",unit_price:o?.sale_price_usd>0?o.sale_price_usd:""});};
  const total=form.items.length?form.items.reduce((sum,i)=>sum+Math.round((Number(i.quantity)||0)*(Number(i.unit_price)||0)*100)/100,0):Number(form.total_usd)||0;
  const locked=["shipped","delivered","cancelled"].includes(form.status)&&!isNew;
  const save=async()=>{
    if(!form.customer.trim())return toast.error("Cliente obrigatório");
    setSaving(true);
    try{const body={...form,total_usd:total,items:form.items.map(i=>({...i,quantity:Number(i.quantity),unit_price:Number(i.unit_price)}))};if(isNew)await api.post("/orders",body);else await api.put(`/orders/${form.id}`,body);setDialog(false);toast.success("Pedido salvo; estoque e financeiro atualizados.");await load();window.dispatchEvent(new Event("finance-updated"));}catch(e){toast.error(error(e));}finally{setSaving(false);}
  };
  const archive=async o=>{if(!window.confirm("Arquivar este pedido? Ele poderá ser restaurado em Arquivados."))return;try{await api.delete(`/orders/${o.id}`);load();}catch(e){toast.error(error(e));}};
  const restore=async o=>{try{await api.post(`/orders/${o.id}/restore`);load();toast.success("Pedido restaurado");}catch(e){toast.error(error(e));}};
  return <div data-testid="orders-page">
    <PageHeader number="04 · Pedidos de venda" title="Pedidos" subtitle="Itens por produto e fornecedor, recebimentos em USD e estoque próprio opcional" action={<Button onClick={()=>open()} data-testid="new-order-button"><Plus className="w-4 h-4 mr-1"/>Novo pedido</Button>}/>
    <Card className="mb-4"><CardContent className="p-4 flex justify-between items-center"><div>Total de pedidos ativos: <strong>{fmtUSD(records.filter(x=>x.status!=="cancelled").reduce((a,b)=>a+(b.total_usd||0),0))}</strong></div>{user?.role==="admin"&&<Button variant="outline" onClick={()=>setArchived(!archived)}>{archived?"Voltar aos ativos":"Arquivados"}</Button>}</CardContent></Card>
    <div className="space-y-2">{records.map(o=><Card key={o.id}><CardContent className="p-4"><div className="flex flex-wrap gap-3 items-center"><span className="text-xs rounded bg-slate-100 p-2">{statuses[o.status]||o.status}</span><div className="flex-1 min-w-[180px]"><strong>{o.number||"Pedido"} — {o.customer}</strong><div className="text-xs">{o.order_date} · {o.incoterm} · {o.track_stock?"Estoque próprio":"Entrega pelo fornecedor"}</div></div><strong>{fmtUSD(o.total_usd)}</strong>{archived?<Button onClick={()=>restore(o)}>Restaurar</Button>:<><Button variant="outline" onClick={()=>open(o)}>Editar</Button>{user?.role==="admin"&&["draft","cancelled"].includes(o.status)&&<Button variant="ghost" onClick={()=>archive(o)}>Arquivar</Button>}</>}</div><p className="text-sm mt-2">{o.products}</p>{o.lead_id&&<Link className="text-sm underline" to={`/prospects/pipeline?lead=${encodeURIComponent(o.lead_id)}`}>Ver empresa no CRM</Link>}{o.workflow_enabled&&o.status!=="draft"&&o.status!=="cancelled"&&<p className="text-xs mt-1">Financeiro: {o.finance_paid?"recebido":"a receber"} · vence {o.receivable_due_date}</p>}</CardContent></Card>)}{!records.length&&<p>Nenhum pedido {archived?"arquivado":"registrado"}.</p>}</div>
    <Dialog open={dialog} onOpenChange={v=>{if(!saving)setDialog(v);}}><DialogContent className="bg-white max-w-3xl max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>Pedido de venda</DialogTitle></DialogHeader>
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">Número<Input value={form.number} onChange={e=>change("number",e.target.value)}/></label>
        <label className="text-sm">Situação<select aria-label="Situação do pedido" className={selectClass} value={form.status} onChange={e=>change("status",e.target.value)}>{Object.entries(statuses).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
        <label className="text-sm col-span-2">Empresa do CRM<select aria-label="Empresa do CRM" className={selectClass} value={form.lead_id} disabled={!canChangeCustomer || loadingLeads || leadLoadError} onChange={e=>chooseCustomer(e.target.value)}>
          <option value="">Cliente informado manualmente</option>
          {form.lead_id&&!customerOptions.some(l=>l.id===form.lead_id)&&<option value={form.lead_id} aria-label={`${form.customer} · cadastro vinculado`} label={`${form.customer} · cadastro vinculado`}/>}
          {customerOptions.map(l=><option key={l.id} value={l.id} aria-label={`${l.company}${l.country?` · ${l.country}`:""}`} label={`${l.company}${l.country?` · ${l.country}`:""}`}/>)}
        </select></label>
        {loadingLeads&&<p role="status">Carregando empresas do CRM…</p>}
        {leadLoadError&&<div role="alert">Não foi possível carregar as empresas. <Button variant="outline" onClick={()=>setRetryLeads(x=>x+1)}>Tentar carregar empresas novamente</Button></div>}
        {form.lead_id&&<p className="text-xs col-span-2">Cliente e país vêm do cadastro ao vincular. O pedido preserva esses dados mesmo se o CRM mudar depois.</p>}
        <label className="text-sm col-span-2">Cliente<Input readOnly={!!form.lead_id} data-testid="ord-customer-input" value={form.customer} onChange={e=>change("customer",e.target.value)}/></label>
        <label className="text-sm">País<Input readOnly={!!form.lead_id} value={form.customer_country} onChange={e=>change("customer_country",e.target.value)}/></label>
        <label className="text-sm">Incoterm<select className={selectClass} value={form.incoterm} onChange={e=>change("incoterm",e.target.value)}>{["FOB","CIF","CFR","EXW","DDP"].map(x=><option key={x}>{x}</option>)}</select></label>
        <label className="text-sm">Data do pedido<Input type="date" value={form.order_date} onChange={e=>change("order_date",e.target.value)}/></label>
        <label className="text-sm">Vencimento do recebimento<Input type="date" value={form.receivable_due_date} onChange={e=>change("receivable_due_date",e.target.value)}/></label>
        <label className="text-sm">Data de entrega<Input type="date" value={form.delivery_date} onChange={e=>change("delivery_date",e.target.value)}/></label>
        <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={form.track_stock} disabled={locked} onChange={e=>change("track_stock",e.target.checked)}/>Usar estoque próprio</label>
      </div>
      <p className="text-xs">Com estoque próprio, confirmar reserva e embarcar baixa a quantidade. Entrega direta pelo fornecedor gera a conta a receber sem movimentar estoque próprio.</p>
      {form.items.map((item,i)=><div key={i} className="border rounded p-3 grid grid-cols-3 gap-2"><label className="col-span-3 text-sm">Produto / oferta / fornecedor<select aria-label={`Oferta do item ${i+1}`} className={selectClass} value={item.offer_id} disabled={locked} onChange={e=>chooseOffer(i,e.target.value)}><option value="">Selecione a oferta</option>{offers.filter(o=>o.active!==false||o.id===item.offer_id).map(o=><option key={o.id} value={o.id}>{o.product_name} · {o.form} · {o.supplier_name}</option>)}</select></label><label className="text-sm">Quantidade<Input aria-label={`Quantidade do item ${i+1}`} type="number" min="0" step="any" value={item.quantity} disabled={locked} onChange={e=>changeItem(i,{quantity:e.target.value})}/></label><label className="text-sm">Unidade<Input value={item.unit} disabled={locked} onChange={e=>changeItem(i,{unit:e.target.value})}/></label><label className="text-sm">Preço unitário USD<Input aria-label={`Preço USD do item ${i+1}`} type="number" min="0" step="any" value={item.unit_price} disabled={locked} onChange={e=>changeItem(i,{unit_price:e.target.value})}/></label>{!locked&&<Button variant="ghost" onClick={()=>change("items",form.items.filter((_,j)=>j!==i))}>Remover item</Button>}</div>)}
      {!locked&&<Button variant="outline" onClick={()=>change("items",[...form.items,{product_id:"",offer_id:"",quantity:"",unit:"kg",unit_price:""}])}>Adicionar item</Button>}
      {!form.items.length&&<p className="text-xs">Adicione itens para confirmar. A descrição antiga é preservada no rascunho: {form.products||"—"}.</p>}
      <strong>Total: {fmtUSD(total)}</strong>
      <label className="text-sm">Notas<Textarea value={form.notes} onChange={e=>change("notes",e.target.value)}/></label>
      <DialogFooter><Button variant="outline" disabled={saving} onClick={()=>setDialog(false)}>Fechar</Button><Button disabled={saving} onClick={save} data-testid="save-order-button">{saving?"Salvando…":"Salvar"}</Button></DialogFooter>
    </DialogContent></Dialog>
  </div>;
}
