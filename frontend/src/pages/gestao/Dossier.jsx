import {useEffect,useState} from "react";
import {Link,useSearchParams} from "react-router-dom";
import {api} from "@/AuthContext";
import {PageHeader,Button,Card,CardContent} from "@/components/erp";
const states={draft:"Rascunho",confirmed:"Confirmado",shipped:"Embarcado",delivered:"Entregue",cancelled:"Cancelado",unknown:"A conferir",approved:"Aprovado internamente"};
const docs={review:"Metadados inconsistentes; conferir documento",missing:"Nenhum documento ativo",draft:"Rascunho ativo",approved:"Aprovado internamente e compatível com o pedido",outdated:"Origem alterada; conferir documento",ambiguous:"Mais de um documento ativo; conferir vínculo"};
const quoteStates={not_linked:"Pedido sem cotação vinculada",linked:"Cotação vinculada à revisão registrada no pedido",missing:"Cotação de origem não encontrada",ambiguous:"Cotação de origem ambígua",review:"Cotação ou vínculo a conferir"};
const flags={documents_pending:"Documentação comercial a conferir",shipment_missing:"Embarque não registrado ou cancelado",shipment_overdue:"Previsão logística vencida",data_review:"Dados ou vínculos a conferir",quote_review:"Cotação de origem a conferir"};
const shipping={planned:"Planejado",booked:"Reservado",in_transit:"Em trânsito",arrived:"Chegou ao destino",delivered:"Entregue",cancelled:"Cancelado"};
export default function Dossier(){
 const [params]=useSearchParams(),order=params.get("order")||"";
 const [result,setResult]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState(""),[refresh,setRefresh]=useState(0);
 useEffect(()=>{let active=true;setResult(null);setError("");setLoading(false);
  if(order){setLoading(true);api.get("/orders/"+encodeURIComponent(order)+"/dossier").then(r=>{if(active)setResult(r.data);}).catch(e=>{if(active)setError(typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível consultar o dossiê. Tente atualizar.");}).finally(()=>{if(active)setLoading(false);});}
  return()=>{active=false;};
 },[order,refresh]);
 const links=<div className="flex flex-wrap gap-4 text-sm"><Link className="underline" to="/gestao/operacao">Escolher na operação do dia</Link><Link className="underline" to="/gestao/pedidos">Abrir pedidos</Link><Link className="underline" to="/gestao/qualidade">Qualidade documental</Link></div>;
 const documents=(rows,type)=><div className="space-y-3">{!rows.length&&<p>Nenhum documento deste tipo vinculado ao pedido.</p>}{rows.map(row=><article key={row.id} className="border rounded p-3 break-words">
  <h3 className="font-semibold">{row.reference||"Referência não informada"}</h3><p>{states[row.status]||"A conferir"} · Revisão {row.version??"a conferir"} · Emissão: {row.issue_date||"não informada"}</p>
  <p>{row.source_current===true?"Origem compatível com o pedido atual":row.source_current===false?"Origem diferente do pedido atual":"Origem não conferida: revise os dados comerciais"}</p>
  {row.status==="cancelled"&&<p>Documento cancelado: preservado para consulta, excluído dos ativos.</p>}
  <Link className="underline text-sm" to={type==="invoice"?"/gestao/invoices-comerciais?invoice="+encodeURIComponent(row.id):"/gestao/packing-lists?packing="+encodeURIComponent(row.id)}>Abrir {type==="invoice"?"Invoice":"Packing List"} {row.reference||"sem referência"}</Link>
 </article>)}</div>;
 return <div className="space-y-4" data-testid="dossier-page">
  <PageHeader title="Dossiê do pedido" subtitle="Origem comercial, documentos vinculados e logística" action={order?<Button variant="outline" onClick={()=>setRefresh(v=>v+1)}>Atualizar dossiê</Button>:undefined}/>
  <p className="text-sm">Consulta dos registros existentes. Este dossiê não comprova liberação de carga, conformidade do produto, documentação exigida pelo destino ou transmissão ao Siscomex. A aprovação exibida é interna.</p>
  {links}
  {!order&&<p>Abra um pedido na operação do dia ou em Pedidos e selecione “Ver dossiê”.</p>}
  {loading&&<p role="status">Conferindo o dossiê…</p>}{error&&<p role="alert">{error}</p>}
  {result&&!loading&&<>
   <Card><CardContent className="p-4 break-words"><h2 className="font-semibold">{result.order.number||"Pedido sem número"} — {result.order.customer}</h2><p>{result.order.customer_country||"País não informado"} · {states[result.order.status]||"A conferir"} · {result.order.incoterm||"Incoterm não informado"}</p><p>Pedido: {result.order.order_date||"data não informada"} · Revisão {result.order.version??"a conferir"}</p><p className="text-xs">Consulta em {result.today} · {result.timezone}. As fontes podem mudar durante a consulta; atualize antes de decidir.</p></CardContent></Card>
   <section aria-label="Pendências do dossiê" className="border rounded p-4">
    <h2 className="font-semibold">Pendências detectadas</h2>{result.flags.length?<ul className="list-disc pl-5">{result.flags.map(flag=><li key={flag}>{flags[flag]||"Registro a conferir"}</li>)}</ul>:<p>Sem alertas destas regras. Conferência operacional necessária.</p>}
    {!result.commercial_source_checked&&<p>Não foi possível conferir a origem comercial. Revise os itens e os dados do pedido.</p>}
   </section>
   <section aria-label="Origem comercial" className="border rounded p-4 break-words"><h2 className="font-semibold">Origem comercial</h2><p>{quoteStates[result.quote.state]||"A conferir"}</p>
    {result.quote.id&&<><p>{result.quote.reference||"Cotação sem referência"} · Revisão registrada {result.quote.recorded_version??"a conferir"} · Situação atual: {states[result.quote.current_status]||"não confirmada"}</p><Link className="underline" to={"/gestao/cotacoes?quote="+encodeURIComponent(result.quote.id)}>Conferir cotação de origem</Link></>}
    <p className="text-xs">Ausência de cotação vinculada não invalida um pedido criado por outro fluxo.</p>
   </section>
   <section aria-label="Invoices do dossiê" className="space-y-2"><h2 className="font-semibold">Commercial Invoice</h2><p>{docs[result.invoice_state]||"A conferir"} · {result.counts.active_invoices} ativo(s) / {result.counts.invoices} cadastrado(s)</p>{documents(result.invoices,"invoice")}</section>
   <section aria-label="Packing Lists do dossiê" className="space-y-2"><h2 className="font-semibold">Packing List</h2><p>{docs[result.packing_state]||"A conferir"} · {result.counts.active_packing_lists} ativo(s) / {result.counts.packing_lists} cadastrado(s)</p>{documents(result.packing_lists,"packing")}</section>
   <section aria-label="Logística do dossiê" className="border rounded p-4 break-words space-y-2"><h2 className="font-semibold">Embarque manual</h2><p>{shipping[result.shipment.status]||"Não registrado"} · {result.shipment.reference||"Sem referência"}</p><p>Origem: {result.shipment.origin||"não informada"} · Destino: {result.shipment.destination||"não informado"}</p><p>Transportadora: {result.shipment.carrier||"não informada"} · Documento de transporte: {result.shipment.transport_reference||"não informado"}</p><p>Saída prevista: {result.shipment.planned_departure||"não informada"} · Chegada prevista: {result.shipment.planned_arrival||"não informada"}</p><p>Saída real: {result.shipment.actual_departure||"não informada"} · Chegada real: {result.shipment.actual_arrival||"não informada"} · Entrega real: {result.shipment.actual_delivery||"não informada"}</p>
    <Link className="underline" to={"/gestao/embarques?order="+encodeURIComponent(result.order.id)}>Conferir embarque do pedido</Link>
   </section>
   <p className="text-sm">Arquivos gerais do cliente, produto ou fornecedor não são associados automaticamente a este pedido. Certificados, COA, certificados de origem e demais exigências precisam de conferência específica. Esta tela não gera arquivos, pagamentos ou alterações de estoque.</p>
  </>}
 </div>;
}
