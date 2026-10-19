import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast } from "@/components/erp";

const states = {planned:"Planejado",booked:"Reservado",in_transit:"Em trânsito",arrived:"Chegou ao destino",delivered:"Entregue",cancelled:"Transporte cancelado"};
const modes = {sea:"Marítimo",air:"Aéreo",road:"Rodoviário",rail:"Ferroviário",multimodal:"Multimodal"};
const defaults = {reference:"",status:"planned",origin:"",destination:"",mode:"sea",responsible_id:"",carrier:"",booking_reference:"",transport_reference:"",planned_departure:"",planned_arrival:"",actual_departure:"",actual_arrival:"",actual_delivery:"",notes:"",change_note:""};
const fields = [["reference","Referência",120],["origin","Origem",200],["destination","Destino",200],["carrier","Transportadora",160],["booking_reference","Reserva / booking",120],["transport_reference","Documento de transporte",160]];
const dates = [["planned_departure","Saída prevista"],["planned_arrival","Chegada prevista"],["actual_departure","Saída real"],["actual_arrival","Chegada real"],["actual_delivery","Entrega real"]];
const labels = {...Object.fromEntries([...fields,...dates].map(([key,title])=>[key,title])),status:"Situação",mode:"Modal",responsible_id:"Responsável (cadastro)",responsible_name:"Responsável",notes:"Observações"};
const selectClass = "border rounded-md p-2 bg-white w-full text-sm";
const error = e => typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Não foi possível concluir. Recarregue e tente novamente.";

export default function Shipments(){
  const [params,setParams]=useSearchParams();
  const requested=params.get("order");
  const [records,setRecords]=useState([]),[status,setStatus]=useState(""),[archived,setArchived]=useState(false),[skip,setSkip]=useState(0),[retry,setRetry]=useState(0);
  const [loading,setLoading]=useState(false),[loadError,setLoadError]=useState(false);
  const [detail,setDetail]=useState(null),[form,setForm]=useState(defaults),[users,setUsers]=useState([]),[opening,setOpening]=useState(false),[openError,setOpenError]=useState(""),[saving,setSaving]=useState(false);
  const request=useRef(0),savingRef=useRef(false);
  useEffect(()=>{let active=true;setLoading(true);setLoadError(false);setRecords([]);
    api.get("/shipments",{params:{status:status||undefined,archived,skip,limit:50}})
      .then(r=>{if(active)setRecords(r.data);}).catch(()=>{if(active)setLoadError(true);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[status,archived,skip,retry]);
  const apply=useCallback(data=>{setDetail(data);setForm({...defaults,...Object.fromEntries(Object.keys(defaults).filter(k=>k!=="change_note").map(k=>[k,data.shipment?.[k]??defaults[k]])),status:data.shipment?.status||data.allowed_statuses[0]||"planned"});},[]);
  const open=useCallback(async id=>{
    if(savingRef.current)return;
    const seq=++request.current;setOpening(true);setDetail(null);setOpenError("");
    setParams(current=>{const next=new URLSearchParams(current);next.delete("order");return next;},{replace:true});
    try{const [order,directory]=await Promise.all([api.get(`/orders/${encodeURIComponent(id)}/shipment`),api.get("/auth/users")]);
      if(seq===request.current){apply(order.data);setUsers(directory.data.filter(u=>u.active!==false&&["admin","user"].includes(u.role||"user")));}
    }catch(e){if(seq===request.current)setOpenError(error(e));}
    finally{if(seq===request.current)setOpening(false);}
  },[apply,setParams]);
  useEffect(()=>{if(requested)open(requested);},[requested,open]);
  useEffect(()=>()=>{request.current+=1;},[]);
  const close=()=>{if(savingRef.current)return;request.current+=1;setOpening(false);setDetail(null);setOpenError("");};
  const change=(key,value)=>setForm(f=>({...f,[key]:value}));
  const save=async()=>{if(!detail||savingRef.current)return;savingRef.current=true;setSaving(true);
    try{const r=await api.put(`/orders/${encodeURIComponent(detail.id)}/shipment`,{...form,version:detail.version});apply(r.data);setRetry(n=>n+1);toast.success("Embarque salvo.");window.dispatchEvent(new Event("finance-updated"));}
    catch(e){toast.error(error(e));}finally{savingRef.current=false;setSaving(false);}
  };
  const readonly=!detail?.allowed_statuses?.length;
  const departed=!!detail?.shipment?.actual_departure;
  return <div data-testid="shipments-page">
    <PageHeader title="Embarques" subtitle="Acompanhamento manual · um embarque completo por pedido" />
    <p className="text-sm mb-4">Abra um pedido confirmado para registrar o embarque. As mudanças atualizam o pedido, o estoque próprio e a conta a receber no mesmo fluxo. Embarques parciais ainda não são atendidos.</p>
    <Link className="underline" to="/gestao/pedidos">Consultar pedidos</Link>
    <div className="flex flex-wrap gap-3 my-4">
      <label>Situação logística<select aria-label="Situação logística" className={selectClass} value={status} onChange={e=>{setStatus(e.target.value);setSkip(0);}}><option value="">Todas</option>{Object.entries(states).map(([v,t])=><option key={v} value={v} label={t} aria-label={t}/>)}</select></label>
      <label className="flex items-center gap-2"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setSkip(0);}}/>Pedidos arquivados</label>
      <Button variant="outline" onClick={()=>setRetry(n=>n+1)}>Atualizar lista</Button>
    </div>
    {loading&&<p role="status">Carregando embarques…</p>}
    {loadError&&<p role="alert">Não foi possível carregar os embarques. Use Atualizar lista para tentar novamente.</p>}
    {!loading&&!loadError&&!records.length&&<p>Nenhum embarque nesta página.</p>}
    {records.map(o=><Card key={o.id}><CardContent className="p-4"><strong>{`${o.shipment.reference} — ${o.customer}`}</strong><p>{states[o.shipment.status]} · {o.shipment.origin} → {o.shipment.destination}</p><p className="text-sm">{o.shipment.responsible_name} · chegada prevista {o.shipment.planned_arrival}</p><Button variant="outline" disabled={saving} onClick={()=>open(o.id)}>Abrir embarque</Button></CardContent></Card>)}
    <div className="flex items-center gap-3 my-4"><Button disabled={!skip||loading} onClick={()=>setSkip(n=>Math.max(0,n-50))}>Anterior</Button><span>Página {skip/50+1}</span><Button disabled={records.length<50||loading} onClick={()=>setSkip(n=>n+50)}>Próxima</Button></div>
    {opening&&<p role="status">Abrindo pedido…</p>}{openError&&<p role="alert">{openError} Abra o pedido novamente para tentar.</p>}
    <Dialog open={!!detail} onOpenChange={v=>{if(!v)close();}}><DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>Embarque — {detail?.customer}</DialogTitle></DialogHeader>
      {detail&&<><p>{`Pedido ${detail.number||detail.id} · versão ${detail.version}`}</p>{readonly&&<p role="status">Histórico somente para consulta. O pedido não permite alterações logísticas.</p>}
      <fieldset disabled={readonly||saving} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label>Situação do embarque<select aria-label="Situação do embarque" className={selectClass} value={form.status} onChange={e=>change("status",e.target.value)}>{[...new Set([form.status,...detail.allowed_statuses])].map(v=><option key={v} value={v} label={states[v]||v} aria-label={states[v]||v}/>)}</select></label>
        <label>Modal<select aria-label="Modal" className={selectClass} disabled={departed} value={form.mode} onChange={e=>change("mode",e.target.value)}>{Object.entries(modes).map(([v,t])=><option key={v} value={v} label={t} aria-label={t}/>)}</select></label>
        {fields.map(([key,title,max])=><label key={key}>{title}<Input value={form[key]} maxLength={max} readOnly={departed&&["origin","destination"].includes(key)} onChange={e=>change(key,e.target.value)}/></label>)}
        <label>Responsável<select aria-label="Responsável" className={selectClass} value={form.responsible_id} onChange={e=>change("responsible_id",e.target.value)}><option value="">Selecione</option>{form.responsible_id&&!users.some(u=>u.id===form.responsible_id)&&<option value={form.responsible_id} label={detail.shipment.responsible_name||"Responsável indisponível"} aria-label={detail.shipment.responsible_name||"Responsável indisponível"}/>}{users.map(u=><option key={u.id} value={u.id} label={u.name||u.email||u.id} aria-label={u.name||u.email||u.id}/>)}</select></label>
        {dates.map(([key,title])=><label key={key}>{title}<Input type="date" value={form[key]} readOnly={key.startsWith("actual_")&&!!detail.shipment?.[key]} onChange={e=>change(key,e.target.value)}/></label>)}
        <label>Observações<Textarea value={form.notes} maxLength={2000} onChange={e=>change("notes",e.target.value)}/></label>
        <label>Motivo da alteração<Textarea value={form.change_note} maxLength={300} onChange={e=>change("change_note",e.target.value)}/></label>
      </fieldset>
      <p className="text-xs">Saída real confirma a baixa do estoque próprio. Cancelar transporte antes da saída mantém a venda confirmada; o cancelamento da venda é feito no pedido. Datas reais já registradas e rota após a saída ficam preservadas.</p>
      <section aria-label="Histórico do embarque"><h3 className="font-semibold">Histórico</h3>{(detail.shipment?.history||[]).slice().reverse().map(event=><div key={event.id} className="border-b py-2 text-sm"><strong>{states[event.to_status]||event.to_status}</strong> · {event.by_name||event.by} · {event.at}<p>{event.note}</p><dl>{Object.entries(event.changes||{}).map(([key,value])=><div key={key}><dt className="inline">{labels[key]||key}: </dt><dd className="inline break-words">{key==="status"?(states[value]||value):key==="mode"?(modes[value]||value):String(value)}</dd></div>)}</dl></div>)}</section>
      </>}
      <DialogFooter><Button variant="outline" disabled={saving} onClick={close}>Fechar</Button>{!readonly&&<><Button variant="outline" disabled={saving} onClick={()=>open(detail.id)}>Recarregar pedido</Button><Button disabled={saving||form.change_note.trim().length<3} onClick={save}>{saving?"Salvando…":"Salvar embarque"}</Button></>}</DialogFooter>
    </DialogContent></Dialog>
  </div>;
}
