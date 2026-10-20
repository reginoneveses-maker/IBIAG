import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Card, CardContent } from "@/components/erp";
const states={draft:"Rascunho",confirmed:"Confirmado",shipped:"Embarcado",delivered:"Entregue",cancelled:"Cancelado",unknown:"Revisar situação"};
const flags={receivable_overdue:"Recebimento vencido",shipment_overdue:"Previsão de embarque vencida",documents_pending:"Documentação a conferir",shipment_missing:"Embarque não registrado / cancelado",data_review:"Cadastro ou vínculo a revisar"};
const shipmentStates={planned:"Planejado",booked:"Reservado",in_transit:"Em trânsito",arrived:"Chegou ao destino",delivered:"Entregue",cancelled:"Cancelado"};
const docStates={missing:"Não preparado",draft:"Rascunho",approved:"Aprovado",outdated:"Origem alterada",ambiguous:"Vínculo ambíguo"};
const defaults={status:"",country:"",date_from:"",date_to:"",attention:""};
const selectClass="border rounded-md p-2 bg-white w-full text-sm";
export default function Operations(){
 const [form,setForm]=useState(defaults),[filters,setFilters]=useState(defaults),[skip,setSkip]=useState(0),[refresh,setRefresh]=useState(0),[data,setData]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState("");
 useEffect(()=>{let active=true;setLoading(true);setError("");setData(null);
  api.get("/gestao/operations",{params:{...Object.fromEntries(Object.entries(filters).filter(([,v])=>v)),skip,limit:50}}).then(r=>{if(active)setData(r.data);}).catch(e=>{if(active)setError(typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível carregar os pedidos. Tente atualizar.");}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};
 },[filters,skip,refresh]);
 const change=(key,value)=>setForm(f=>({...f,[key]:value}));
 const apply=e=>{e.preventDefault();setSkip(0);setFilters({...form});};
 return <div className="space-y-5" data-testid="operations-page">
  <PageHeader title="Operação do dia" subtitle="Pedidos, documentação, embarques e recebimentos" action={<Button variant="outline" onClick={()=>setRefresh(n=>n+1)}>Atualizar painel</Button>}/>
  <p className="text-sm">Visão de consulta dos registros atuais. Alertas pedem conferência e não alteram operações. Datas de vencimento usam Fortaleza; pagamento vem da conta vinculada ao pedido. Recarregue antes de decidir em outra área.</p>
  <form onSubmit={apply} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 rounded-xl border p-4 bg-white">
   <label>Situação do pedido<select aria-label="Situação do pedido" className={selectClass} value={form.status} onChange={e=>change("status",e.target.value)}><option value="">Todas</option>{Object.entries(states).filter(([k])=>k!=="unknown").map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
   <label>País do comprador<Input aria-label="País do comprador" maxLength={100} value={form.country} onChange={e=>change("country",e.target.value)} placeholder="Nome exato do cadastro"/></label>
   <label>Pendência<select aria-label="Pendência" className={selectClass} value={form.attention} onChange={e=>change("attention",e.target.value)}><option value="">Todas</option>{Object.entries(flags).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
   <label>Pedido de<Input aria-label="Pedido de" type="date" value={form.date_from} onChange={e=>change("date_from",e.target.value)}/></label><label>Pedido até<Input aria-label="Pedido até" type="date" value={form.date_to} onChange={e=>change("date_to",e.target.value)}/></label>
   <div className="flex items-end gap-2"><Button type="submit">Aplicar filtros</Button><Button type="button" variant="outline" onClick={()=>{setForm(defaults);setFilters({...defaults});setSkip(0);}}>Limpar filtros</Button></div>
  </form>
  {loading&&<p role="status">Carregando operação…</p>}{error&&<p role="alert">{error}</p>}
  {data&&<>
   <p className="text-xs">Atualizado: {new Date(data.generated_at).toLocaleString("pt-BR",{timeZone:data.timezone})} · {data.timezone}. Resumo por situação, país e período; o filtro de pendência restringe a lista abaixo.</p>
   <section aria-label="Resumo operacional" className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
    <Card><CardContent className="p-4"><p>Pedidos no período e filtros</p><strong className="text-2xl">{data.summary.total}</strong><p className="text-sm">{data.summary.needs_attention} com alguma pendência</p></CardContent></Card>
    {Object.entries(flags).map(([k,title])=><Card key={k}><CardContent className="p-4"><p className="text-sm">{title}</p><strong className="text-2xl">{data.summary.attention[k]}</strong><Button className="block mt-2 whitespace-normal h-auto text-left max-w-full py-2" variant="outline" onClick={()=>{setForm(f=>({...f,attention:k}));setFilters(f=>({...f,attention:k}));setSkip(0);}}>Ver: {title}</Button></CardContent></Card>)}
   </section>
   <p>{data.total} {data.total===1?"pedido":"pedidos"} na lista · página {skip/50+1}</p>
   {!data.rows.length&&<p>Nenhum pedido nos filtros atuais.</p>}
   <div className="space-y-3">{data.rows.map(row=><Card key={row.id} data-testid={`operation-${row.id}`}><CardContent className="p-4 space-y-3">
    <div className="flex flex-wrap justify-between gap-2"><div className="min-w-0 break-words"><strong>{row.number||"Pedido sem referência"} — {row.customer}</strong><p>{states[row.status]} · {row.customer_country||"País não informado"} · {row.order_date||"Data a revisar"}</p></div><Link className="underline text-sm" to="/gestao/pedidos">Pedidos</Link></div>
    <p className="text-sm">Invoice: {docStates[row.invoice_status]} · Packing List: {docStates[row.packing_status]}</p>
    <p className="text-sm">Embarque: {shipmentStates[row.shipment_status]||"Não registrado"}{row.planned_arrival?` · chegada prevista ${row.planned_arrival}`:""} · Recebimento: {row.workflow_enabled&&["confirmed","shipped","delivered"].includes(row.status)?row.finance_paid===true?"Registrado":row.finance_paid===false?`Pendente · vence ${row.receivable_due_date||"data a revisar"}`:"A revisar":"Sem conta automática neste estado"}</p>
    {row.flags.length?<ul className="list-disc ml-5 text-sm text-amber-900">{row.flags.map(key=><li key={key}>{flags[key]}{key==="receivable_overdue"?` · ${row.days_overdue} ${row.days_overdue===1?"dia":"dias"}`:""}</li>)}</ul>:<p className="text-sm">Sem pendências detectadas por estas regras.</p>}
    {row.workflow_enabled&&["confirmed","shipped","delivered"].includes(row.status)&&<div className="flex flex-wrap gap-4 text-sm"><Link className="underline" to={`/gestao/invoices-comerciais?order=${encodeURIComponent(row.id)}`}>Conferir invoice</Link><Link className="underline" to={`/gestao/packing-lists?order=${encodeURIComponent(row.id)}`}>Conferir Packing List</Link><Link className="underline" to={`/gestao/embarques?order=${encodeURIComponent(row.id)}`}>Conferir embarque</Link><Link className="underline" to="/gestao/financeiro">Conferir financeiro</Link></div>}
   </CardContent></Card>)}</div>
   <div className="flex flex-wrap gap-3"><Button disabled={!skip||loading} onClick={()=>setSkip(n=>Math.max(0,n-50))}>Anterior</Button><Button disabled={skip+50>=data.total||loading} onClick={()=>setSkip(n=>n+50)}>Próxima</Button></div>
  </>}
 </div>;
}
