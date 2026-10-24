import OperationHistory from "@/components/OperationHistory";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast } from "@/components/erp";
import {priceMoney} from "@/lib/pricing";
import {saleCurrency,saleMoney} from "@/lib/saleCurrency";
import { documentPreview } from "@/lib/api";
const labels={draft:"Rascunho",approved:"Aprovada internamente",cancelled:"Cancelada"};
const fields=[
 ["issue_date","Data de emissão",10,"date"],["seller_name","Razão social do emitente",200],["seller_tax_id","Registro fiscal do emitente",80],
 ["seller_address","Endereço do emitente",1000,"text"],["seller_country","País do emitente",100],["buyer_address","Endereço do comprador",1000,"text"],
 ["buyer_country","País do comprador",100],["buyer_tax_id","Registro fiscal do comprador (opcional)",80],["buyer_reference","Referência do comprador (opcional)",120],
 ["incoterm_place","Local nomeado do Incoterm",200],["payment_terms","Condições de pagamento",1000,"text"],["delivery_terms","Condições de entrega",1000,"text"],
 ["notes","Observações comerciais",2000,"text"],["declaration","Declaração adicional (opcional)",2000,"text"],["signatory","Representante autorizado",160]
];
const defaults={...Object.fromEntries(fields.map(([k])=>[k,""])),delivery_same_as_buyer:true,ship_to_name:"",ship_to_address:"",ship_to_country:"",customs:[],change_note:""};
const detailKeys=Object.keys(defaults).filter(k=>k!=="change_note");
const selectClass="border rounded-md p-2 bg-white w-full text-sm";
const error=e=>typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível concluir. Recarregue e confira o documento.";
export default function CommercialInvoices(){
 const [params,setParams]=useSearchParams(),requestedOrder=params.get("order"),requestedInvoice=params.get("invoice");
 const [records,setRecords]=useState([]),[status,setStatus]=useState(""),[skip,setSkip]=useState(0),[retry,setRetry]=useState(0),[loading,setLoading]=useState(false),[listError,setListError]=useState(false);
 const [detail,setDetail]=useState(null),[form,setForm]=useState(defaults),[isNew,setIsNew]=useState(false),[opening,setOpening]=useState(false),[openError,setOpenError]=useState(""),[saving,setSaving]=useState(false),[confirmed,setConfirmed]=useState(false),[pdf,setPdf]=useState(null),[pdfLoading,setPdfLoading]=useState(false);
 const request=useRef(0),busy=useRef(false),pdfBusy=useRef(false),pdfRequest=useRef(0);
 useEffect(()=>{let active=true;setLoading(true);setListError(false);setRecords([]);
  api.get("/commercial-invoices",{params:{status:status||undefined,skip,limit:50}}).then(r=>{if(active)setRecords(r.data);}).catch(()=>{if(active)setListError(true);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};
 },[status,skip,retry]);
 useEffect(()=>()=>{if(pdf)URL.revokeObjectURL(pdf.url);},[pdf]);
 const apply=useCallback(data=>{pdfRequest.current+=1;setPdf(null);setDetail(data);setIsNew(false);setConfirmed(false);setForm({...defaults,...Object.fromEntries(detailKeys.map(k=>[k,data[k]??defaults[k]]))});},[]);
 const open=useCallback(async(id,order)=>{
  if(busy.current)return;const seq=++request.current;setPdf(null);setOpening(true);setOpenError("");setDetail(null);setConfirmed(false);
  setParams(current=>{const next=new URLSearchParams(current);next.delete("order");next.delete("invoice");return next;},{replace:true});
  try{
   if(id&&order)throw new Error("ambiguous");
   let source;
   if(order){source=(await api.get(`/orders/${encodeURIComponent(order)}/commercial-invoice-draft`)).data;if(seq!==request.current)return;id=source.active_invoice_id;}
   if(id){const r=await api.get(`/commercial-invoices/${encodeURIComponent(id)}`);if(seq===request.current)apply(r.data);}
   else if(seq===request.current){const id=crypto.randomUUID(),snapshot=source.source_order_snapshot;setDetail({...source,id});setIsNew(true);setForm({...defaults,reference:`CI-${new Date().toISOString().slice(0,10)}-${id.slice(0,8)}`,issue_date:new Date().toISOString().slice(0,10),buyer_country:snapshot.customer_country||"",payment_terms:snapshot.payment_terms||"",delivery_terms:snapshot.delivery_terms||"",customs:snapshot.items.map((_,index)=>({index,origin_country:"",hs_code:""}))});}
  }catch(e){if(seq===request.current)setOpenError(error(e));}finally{if(seq===request.current)setOpening(false);}
 },[apply,setParams]);
 useEffect(()=>{if(requestedOrder||requestedInvoice)open(requestedInvoice,requestedOrder);},[requestedOrder,requestedInvoice,open]);
 useEffect(()=>()=>{request.current+=1;},[]);
 const close=()=>{if(busy.current)return;request.current+=1;setDetail(null);setPdf(null);setOpening(false);setOpenError("");};
 const change=(k,v)=>{setConfirmed(false);setForm(f=>({...f,[k]:v}));};
 const dirty=!!detail&&!isNew&&detailKeys.some(k=>JSON.stringify(form[k])!==JSON.stringify(detail[k]));
 const editable=isNew||detail?.status==="draft",reason=form.change_note.trim().length>=3;
 const save=async(nextStatus)=>{
  if(!detail||busy.current)return;busy.current=true;setSaving(true);
  try{let r;
   if(nextStatus)r=await api.post(`/commercial-invoices/${encodeURIComponent(detail.id)}/status`,{version:detail.version,status:nextStatus,details_confirmed:nextStatus==="approved"&&confirmed,change_note:form.change_note});
   else{const body={...Object.fromEntries(detailKeys.map(k=>[k,form[k]])),change_note:form.change_note};r=isNew?await api.post("/commercial-invoices",{...body,id:detail.id,reference:form.reference,order_id:detail.order_id,source_order_version:detail.source_order_version}):await api.put(`/commercial-invoices/${encodeURIComponent(detail.id)}`,{...body,version:detail.version});}
   apply(r.data);setRetry(n=>n+1);toast.success(nextStatus==="approved"?"Commercial Invoice aprovada internamente.":nextStatus==="cancelled"?"Commercial Invoice cancelada.":"Rascunho de Commercial Invoice salvo.");
  }catch(e){toast.error(error(e));}finally{busy.current=false;setSaving(false);}
 };
 const getPdf=async(preview)=>{
  if(!detail||isNew||pdfBusy.current||busy.current||dirty)return;pdfBusy.current=true;setPdfLoading(true);const seq=request.current,ticket=++pdfRequest.current;
  try{const r=await api.get(`/commercial-invoices/${encodeURIComponent(detail.id)}/pdf`,{responseType:"blob"});if(seq!==request.current||ticket!==pdfRequest.current)return;
   if(preview){const result=await documentPreview(r.data);if(seq!==request.current||ticket!==pdfRequest.current){if(result.url)URL.revokeObjectURL(result.url);return;}if(result.kind!=="pdf")throw new Error("invalid-pdf");setPdf(result);}
   else{const url=URL.createObjectURL(r.data),a=document.createElement("a");a.href=url;a.download=`Commercial-Invoice-${String(detail.id).replace(/[^A-Za-z0-9_-]/g,"_")}-${detail.status}-v${detail.version}.pdf`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  }catch(e){if(seq===request.current)toast.error("Não foi possível gerar o PDF. Recarregue e confira os dados e a situação do pedido.");}finally{pdfBusy.current=false;setPdfLoading(false);}
 };
 const source=detail?.source_order_snapshot;
 return <div data-testid="commercial-invoices-page">
  <PageHeader title="Commercial Invoice" subtitle="Documento comercial na moeda do pedido" action={<Link className="underline" to="/gestao/pedidos">Escolher pedido</Link>}/>
  <p className="text-sm mb-4">Prepare pelo pedido confirmado, confira os dados e o PDF e aprove explicitamente. Dados fiscais e de origem exigem conferência; nenhuma classificação ou declaração é inferida. Esta aprovação não envia o documento, assina digitalmente ou valida o desembaraço. O documento não cria outra conta financeira.</p>
  <Link className="underline text-sm" to="/gestao/documentos">Voltar à central de documentos</Link>
  <div className="flex flex-wrap gap-3 items-end my-4"><label>Situação da invoice<select aria-label="Situação da invoice" className={selectClass} value={status} onChange={e=>{setStatus(e.target.value);setSkip(0);}}><option value="">Todas</option>{Object.entries(labels).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label><Button variant="outline" onClick={()=>setRetry(n=>n+1)}>Atualizar lista</Button></div>
  {loading&&<p role="status">Carregando invoices…</p>}{listError&&<p role="alert">Não foi possível carregar as invoices. Use Atualizar lista.</p>}{!loading&&!listError&&!records.length&&<p>Nenhuma invoice nesta página.</p>}
  <div className="space-y-3">{records.map(i=><Card key={i.id}><CardContent className="p-4 flex flex-wrap gap-3 items-center"><div className="flex-1"><strong>{i.reference} — {i.customer}</strong><p>{labels[i.status]} · emissão {i.issue_date}</p></div><strong>{saleMoney(i)}</strong><Button variant="outline" disabled={saving} onClick={()=>open(i.id)}>Abrir invoice</Button></CardContent></Card>)}</div>
  <div className="flex items-center gap-3 my-4"><Button disabled={!skip||loading} onClick={()=>setSkip(n=>Math.max(0,n-50))}>Anterior</Button><span>Página {skip/50+1}</span><Button disabled={records.length<50||loading} onClick={()=>setSkip(n=>n+50)}>Próxima</Button></div>
  {opening&&<p role="status">Conferindo pedido…</p>}{openError&&<p role="alert">{openError} Abra novamente pelo pedido ou pela lista.</p>}
  <Dialog open={!!detail} onOpenChange={v=>{if(!v)close();}}><DialogContent className="bg-white max-w-4xl max-h-[90vh] overflow-y-auto"><DialogHeader><DialogTitle>{isNew?"Preparar Commercial Invoice":`Commercial Invoice ${detail?.reference}`}</DialogTitle></DialogHeader>
   {detail&&<><p>{isNew?"Conferência sem gravação automática":`${labels[detail.status]} · versão ${detail.version}`}</p>
    <div className="rounded-lg bg-slate-50 p-4 space-y-2"><strong>{source.customer}</strong><p>Pedido {source.number||"sem referência comercial"} · {source.incoterm}</p>{source.items.map((i,n)=><p key={n}>{i.product_name} · {i.quantity} {i.unit} × {saleCurrency(source)} {Number(i.unit_price).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:12})} = {priceMoney(i.line_total,saleCurrency(source))}</p>)}<strong>Total: {saleMoney(source)}</strong><p className="text-xs">Valores vêm do pedido. Frete e acréscimos devem estar no cálculo/pedido antes de preparar este documento. Custos e fornecedores internos são excluídos do PDF.</p></div>
    <fieldset disabled={!editable||saving} className="grid sm:grid-cols-2 gap-3">
     {isNew&&<label>Referência da invoice<Input value={form.reference} maxLength={80} onChange={e=>change("reference",e.target.value)}/></label>}
     {fields.map(([key,title,max,type])=><label key={key}>{title}{type==="text"?<Textarea aria-label={title} value={form[key]} maxLength={max} readOnly={["payment_terms","delivery_terms"].includes(key)&&!!source[key]} onChange={e=>change(key,e.target.value)}/>:<Input aria-label={title} type={type||"text"} value={form[key]} maxLength={max} readOnly={key==="buyer_country"&&!!source.customer_country} onChange={e=>change(key,e.target.value)}/>}</label>)}
     <label className="sm:col-span-2 flex items-center gap-2"><input type="checkbox" checked={form.delivery_same_as_buyer} onChange={e=>change("delivery_same_as_buyer",e.target.checked)}/>Destinatário igual ao comprador</label>
     {!form.delivery_same_as_buyer&&[["ship_to_name","Nome do destinatário",200],["ship_to_address","Endereço do destinatário",1000],["ship_to_country","País do destinatário",100]].map(([key,title,max])=><label key={key}>{title}<Textarea aria-label={title} value={form[key]} maxLength={max} readOnly={["payment_terms","delivery_terms"].includes(key)&&!!source[key]} onChange={e=>change(key,e.target.value)}/></label>)}
    </fieldset>
    <fieldset disabled={!editable||saving} className="space-y-3"><legend className="font-semibold">Origem e classificação por item</legend>{form.customs.map((line,n)=><div key={n} className="border rounded p-3 grid sm:grid-cols-2 gap-3"><strong className="sm:col-span-2">{n+1}. {source.items[n].product_name}</strong><label>País de origem do item {n+1}<Input maxLength={100} value={line.origin_country} onChange={e=>change("customs",form.customs.map((x,i)=>i===n?{...x,origin_country:e.target.value}:x))}/></label><label>HS/NCM do item {n+1}<Input maxLength={10} inputMode="numeric" value={line.hs_code} onChange={e=>change("customs",form.customs.map((x,i)=>i===n?{...x,hs_code:e.target.value}:x))}/></label></div>)}</fieldset>
    {detail.status!=="cancelled"&&<label>Motivo do registro ou decisão<Textarea aria-label="Motivo do registro ou decisão" disabled={saving} maxLength={300} value={form.change_note} onChange={e=>change("change_note",e.target.value)}/></label>}
    {!isNew&&detail.status==="draft"&&<label className="flex items-start gap-2"><input type="checkbox" checked={confirmed} disabled={saving||dirty||detail.source_changed} onChange={e=>setConfirmed(e.target.checked)}/>Conferi dados cadastrais, valores, origem, classificação e requisitos do destino.</label>}
    {dirty&&<p role="status">Salve as alterações antes de conferir o PDF ou decidir.</p>}{detail.source_changed&&<p role="alert">O pedido está incompatível com esta memória. Cancele o rascunho ou a invoice e prepare outro documento após revisar o pedido.</p>}
    {detail.status==="cancelled"&&<p>Documento cancelado. O PDF recebe a marca CANCELLED.</p>}
    {!isNew&&<div className="flex flex-wrap gap-3"><Button variant="outline" disabled={pdfLoading||saving||dirty} onClick={()=>getPdf(true)}>Conferir PDF</Button><Button variant="outline" disabled={pdfLoading||saving||dirty} onClick={()=>getPdf(false)}>Baixar PDF</Button></div>}
    {pdf&&<section aria-label="Prévia da Commercial Invoice"><Button variant="outline" onClick={()=>setPdf(null)}>Fechar prévia</Button><object data={pdf.url} type="application/pdf" className="w-full h-[500px]" aria-label="PDF da Commercial Invoice"><p>Use Baixar PDF para abrir no seu dispositivo.</p></object></section>}
    {!isNew&&<OperationHistory kind="commercial_invoice" resourceId={detail.id} version={detail.version} recent={detail?.history||[]} archived={!!detail?.history_archive} disabled={saving} onReload={()=>open(detail.id)}/>}
   </>}
   <DialogFooter className="flex-wrap gap-2"><Button variant="outline" disabled={saving} onClick={close}>Fechar</Button>{!isNew&&<Button variant="outline" disabled={saving} onClick={()=>open(detail.id)}>Recarregar invoice</Button>}{editable&&<Button disabled={saving||!reason||!form.issue_date||(isNew&&!form.reference.trim())} onClick={()=>save()}>Salvar rascunho da invoice</Button>}{!isNew&&detail?.status==="draft"&&<Button disabled={saving||dirty||!reason||!confirmed||detail.source_changed} onClick={()=>save("approved")}>Aprovar invoice internamente</Button>}{!isNew&&detail?.status!=="cancelled"&&<Button variant="outline" disabled={saving||dirty||!reason} onClick={()=>save("cancelled")}>Cancelar invoice</Button>}</DialogFooter>
  </DialogContent></Dialog>
 </div>;
}
