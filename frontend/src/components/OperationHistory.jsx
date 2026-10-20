import { useEffect, useRef, useState } from "react";
import { api } from "@/AuthContext";
import { Button } from "@/components/erp";
const titles={quotation:"Histórico da cotação",commercial_invoice:"Histórico da invoice",packing_list:"Histórico da Packing List",shipment:"Histórico do embarque"};
const states={draft:"Rascunho",approved:"Aprovado internamente",cancelled:"Cancelado",planned:"Planejado",booked:"Reservado",in_transit:"Em trânsito",arrived:"Chegou ao destino",delivered:"Entregue"};
const fields={valid_until:"Validade",incoterm:"Incoterm",payment_terms:"Condições de pagamento",delivery_terms:"Condições de entrega",notes:"Observações",status:"Situação",issue_date:"Emissão",seller_name:"Emitente",seller_tax_id:"Registro fiscal do emitente",seller_address:"Endereço do emitente",seller_country:"País do emitente",buyer_address:"Endereço do comprador",buyer_country:"País do comprador",buyer_tax_id:"Registro fiscal do comprador",delivery_same_as_buyer:"Entrega ao comprador",ship_to_name:"Destinatário",ship_to_address:"Endereço do destinatário",ship_to_country:"País do destinatário",incoterm_place:"Local do Incoterm",buyer_reference:"Referência do comprador",declaration:"Declaração",signatory:"Responsável",customs:"Origem e classificação dos itens",packages:"Volumes e distribuição",reference:"Referência",mode:"Modal",origin:"Origem",destination:"Destino",responsible_id:"Identificador do responsável",responsible_name:"Responsável",carrier:"Transportadora",booking_reference:"Reserva",transport_reference:"Documento de transporte",planned_departure:"Saída prevista",planned_arrival:"Chegada prevista",actual_departure:"Saída real",actual_arrival:"Chegada real",actual_delivery:"Entrega real"};
function value(key,v){
 if(key==="status")return states[v]||"Situação a revisar";
 if(key==="mode")return {sea:"Marítimo",air:"Aéreo",road:"Rodoviário",rail:"Ferroviário",multimodal:"Multimodal"}[v]||"Modal a revisar";
 if(typeof v==="boolean")return v?"Sim":"Não";
 if(key==="customs"&&Array.isArray(v))return v.map(x=>`Item ${x.index+1}: ${x.origin_country||"Origem não informada"} · HS/NCM ${x.hs_code||"não informado"}`).join("\n");
 if(key==="packages"&&Array.isArray(v))return v.map(g=>`${g.marks||"Marcas não informadas"} · ${g.packaging||"Embalagem não informada"} · ${g.package_count} volumes · líquido ${g.net_kg||"não informado"} kg · bruto ${g.gross_kg||"não informado"} kg · cubagem ${g.volume_m3||"não informada"} m³\n${(g.allocations||[]).map(a=>`Item ${a.index+1}: ${a.quantity||"não informado"}`).join("; ")}`).join("\n\n")||"Nenhum grupo informado";
 return typeof v==="string"||typeof v==="number"?String(v)||"Não informado":"Conteúdo a conferir no documento";
}
export default function OperationHistory({kind,resourceId,version,recent,archived=false,onReload,disabled=false}){
 const [items,setItems]=useState([]),[total,setTotal]=useState(0),[next,setNext]=useState(""),[loading,setLoading]=useState(false),[error,setError]=useState("");
 const request=useRef(0),busy=useRef(false),loader=useRef(null);
 loader.current=async(cursor="",reset=false)=>{
  if(busy.current)return;busy.current=true;const seq=request.current;setLoading(true);setError("");
  try{const r=await api.get(`/operations-history/${kind}/${encodeURIComponent(resourceId)}`,{params:{limit:20,...(cursor?{cursor}:{})}});if(seq!==request.current)return;
   if(r.data.snapshot_version!==version)throw new Error("changed");
   if(!Array.isArray(r.data.items))throw new Error("invalid");
   setItems(old=>reset?r.data.items:[...old,...r.data.items]);setTotal(r.data.total);setNext(r.data.next_cursor||"");
  }catch(e){if(seq===request.current)setError(typeof e.response?.data?.detail==="string"?e.response.data.detail:"Recarregue o documento para consultar seu histórico atual.");}
  finally{if(seq===request.current){busy.current=false;setLoading(false);}}
 };
 useEffect(()=>{request.current+=1;busy.current=false;setItems([]);setTotal(0);setNext("");setError("");setLoading(false);
  if(!archived&&(recent||[]).length<=20){setItems((recent||[]).slice().reverse());setTotal((recent||[]).length);}
  else loader.current("",true);
  return()=>{request.current+=1;busy.current=false;};
 // Each stored change increments the source version; recent events belong to that revision.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[kind,resourceId,version,archived]);
 return <section aria-label={titles[kind]} className="space-y-3" data-testid="operation-history">
  <h3 className="font-semibold">{titles[kind]}</h3>
  <p className="text-sm">Eventos registrados: {total} · exibindo {items.length}</p>
  {items.map(e=><article key={e.id} className="border-b py-2 text-sm break-words"><p>{kind==="shipment"?states[e.to_status]||"Situação a revisar":`Versão ${e.version}`} · {e.by_name||e.by} · {e.at}</p><p className="whitespace-pre-wrap">{e.note}</p><details><summary className="cursor-pointer">Ver alterações registradas</summary><dl className="space-y-2 mt-2">{Object.entries(e.changes||{}).map(([k,v])=><div key={k}><dt className="font-semibold">{fields[k]||"Campo adicional"}</dt><dd className="whitespace-pre-wrap break-words">{value(k,v)}</dd></div>)}</dl></details></article>)}
  {loading&&<p role="status">Carregando histórico…</p>}{error&&<p role="alert">{error}</p>}{!loading&&!items.length&&!error&&<p>Nenhum evento registrado.</p>}
  <div className="flex flex-wrap gap-2">{next&&<Button variant="outline" disabled={loading||disabled} onClick={()=>loader.current(next,false)}>Carregar eventos anteriores</Button>}<Button variant="outline" disabled={loading||disabled} onClick={()=>loader.current("",true)}>Atualizar histórico</Button>{error&&onReload&&<Button className="whitespace-normal h-auto text-left max-w-full py-2" variant="outline" disabled={disabled} onClick={onReload}>Recarregar documento para conferir histórico</Button>}</div>
 </section>;
}
