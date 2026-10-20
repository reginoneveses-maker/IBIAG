import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {api} from "@/AuthContext";
import {PageHeader,Button,Card,CardContent} from "@/components/erp";
export const qualityFlags={expired:"Certificado vencido",expiring:"Vencimento próximo",missing_expiry:"Validade não informada",invalid_dates:"Datas inconsistentes",missing_file:"Anexo não informado",missing_supplier:"Fornecedor não vinculado ou não encontrado",missing_product:"Produto não vinculado ou não encontrado",data_review:"Cadastro a conferir"};
const origins={certification:"Certificação de fornecedor",document:"Documento técnico"};
const empty={source:"",attention:"",supplier_id:"",product_id:""};
const err=e=>typeof e.response?.data?.detail==="string"?e.response.data.detail:"Não foi possível carregar a qualidade. Tente novamente.";
export default function Quality(){
 const [form,setForm]=useState(empty),[filters,setFilters]=useState(empty),[skip,setSkip]=useState(0),[reload,setReload]=useState(0);
 const [result,setResult]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
 useEffect(()=>{let active=true;setLoading(true);setResult(null);setError("");
  api.get("/gestao/quality",{params:{...Object.fromEntries(Object.entries(filters).filter(([,v])=>v)),skip,limit:50}}).then(r=>{if(active)setResult(r.data);}).catch(e=>{if(active)setError(err(e));}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[filters,skip,reload]);
 const update=(key,value)=>setForm(previous=>({...previous,[key]:value}));
 return <div data-testid="quality-page">
  <PageHeader title="Qualidade documental" subtitle="Pendências derivadas dos certificados e documentos técnicos cadastrados"/>
  <p className="text-sm mb-4">Consulta de metadados. Sem alerta não significa documento aprovado, produto conforme ou lote liberado. Anexo informado não comprova que o arquivo abre ou que o conteúdo foi conferido.</p>
  <form className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4" onSubmit={e=>{e.preventDefault();setSkip(0);setFilters({...form});}}>
   <label>Tipo de registro<select aria-label="Tipo de registro" className="border rounded p-2 w-full bg-white" value={form.source} onChange={e=>update("source",e.target.value)}><option value="">Todos</option>{Object.entries(origins).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
   <label>Pendência de qualidade<select aria-label="Pendência de qualidade" className="border rounded p-2 w-full bg-white" value={form.attention} onChange={e=>update("attention",e.target.value)}><option value="">Todas as situações</option>{Object.entries(qualityFlags).map(([key,label])=><option key={key} value={key}>{label}</option>)}<option value="without_findings">Sem alertas de metadados</option></select></label>
   <div className="flex flex-wrap gap-2 items-end"><Button type="submit">Aplicar filtros</Button><Button type="button" variant="outline" onClick={()=>{setForm(empty);setFilters(empty);setSkip(0);}}>Limpar filtros</Button><Button type="button" variant="outline" onClick={()=>setReload(v=>v+1)}>Atualizar qualidade</Button></div>
  </form>
  {(filters.supplier_id||filters.product_id)&&<p className="text-sm mb-3">Consulta restrita ao fornecedor e/ou produto selecionado. Use Limpar filtros para ver os demais.</p>}
  <p className="text-xs mb-4">O filtro de produto abrange documentos técnicos; certificados de fornecedor não comprovam cobertura de um produto. A análise usa somente registros classificados como Ficha Técnica, COA / Laudo, Certificado ou FISPQ / SDS; outros arquivos e documentos na lixeira não entram. Os totais correspondem aos filtros aplicados.</p>
  <div className="flex flex-wrap gap-4 mb-4"><Link className="underline" to="/gestao/fornecedores">Abrir fornecedores e certificações</Link><Link className="underline" to="/gestao/documentos">Abrir Central de Documentos</Link><Link className="underline" to="/gestao/prospeccao">Abrir especificações técnicas</Link></div>
  {loading&&<p role="status">Conferindo metadados…</p>}{error&&<p role="alert">{error}</p>}
  {result&&!loading&&<>
   <section aria-label="Resumo de qualidade" className="grid sm:grid-cols-3 gap-3 mb-4">
    <Card><CardContent className="p-4">Registros: <strong>{result.summary.total}</strong></CardContent></Card>
    <Card><CardContent className="p-4">Com pendência: <strong>{result.summary.needs_attention}</strong></CardContent></Card>
    <Card><CardContent className="p-4">Sem alertas de metadados: <strong>{result.summary.without_findings}</strong></CardContent></Card>
   </section>
   <p className="text-xs mb-3">Data de referência: {result.today} · {result.timezone}. Cadastros podem mudar durante a consulta.</p>
   {!result.rows.length&&<p>Nenhum registro nesta página para os filtros aplicados.</p>}
   <div className="space-y-3">{result.rows.map(row=><Card key={row.source+":"+row.id}><CardContent className="p-4 break-words">
    <h2 className="font-semibold">{row.title}</h2><p className="text-sm">{origins[row.source]} · {row.document_type}</p>
    <p>Fornecedor: {row.supplier_name||"A conferir"}{row.product_id||row.source==="document"?" · Produto: "+(row.product_name||"A conferir"):""}</p>
    <div className="flex flex-wrap gap-2 my-2">{row.supplier_id&&row.supplier_name&&<Button variant="outline" onClick={()=>{const next={...filters,supplier_id:row.supplier_id};setForm(next);setFilters(next);setSkip(0);}}>Filtrar por este fornecedor</Button>}{row.product_id&&row.product_name&&<Button variant="outline" onClick={()=>{const next={...filters,product_id:row.product_id};setForm(next);setFilters(next);setSkip(0);}}>Filtrar por este produto</Button>}</div>
    {row.source==="certification"&&<p>Emissão: {row.issue_date||"Não informada"} · Validade: {row.expiry_date||"Não informada"}{row.days_remaining!==null?" · Dias até o vencimento: "+row.days_remaining:""}{row.alert_days!==null?" · Antecedência do alerta: "+row.alert_days+" dias":""}</p>}
    <p>Anexo: {row.file_declared?"Informado; conferir abertura e conteúdo":"Não informado"}</p>
    {row.flags.length?<ul className="list-disc pl-5 mt-2">{row.flags.map(flag=><li key={flag}>{qualityFlags[flag]}</li>)}</ul>:<p className="mt-2">Sem alertas de metadados. Conferência humana necessária.</p>}
   </CardContent></Card>)}</div>
   <div className="flex flex-wrap gap-3 mt-4"><Button variant="outline" disabled={skip===0} onClick={()=>setSkip(v=>Math.max(0,v-50))}>Página anterior</Button><p>Página {Math.floor(skip/50)+1} · {result.total} registros</p><Button variant="outline" disabled={skip+50>=result.total} onClick={()=>setSkip(v=>v+50)}>Próxima página</Button></div>
  </>}
 </div>;
}
