import {useEffect,useRef,useState} from "react";
import {api} from "@/AuthContext";
import {documentPreview,downloadDocument} from "@/lib/api";

const labels={expired:"Vencido",expiring:"Vence em breve",missing_expiry:"Validade não informada",invalid_dates:"Datas a revisar",missing_file:"Arquivo não informado",data_review:"Cadastro a revisar",missing_supplier:"Fornecedor a revisar",missing_product:"Produto a revisar"};
export default function QuoteSourceContext({offerId}){
 const [context,setContext]=useState(null),[error,setError]=useState(""),[loading,setLoading]=useState(false),[preview,setPreview]=useState(null),[retry,setRetry]=useState(0);
 const request=useRef(0),fileRequest=useRef(0);
 useEffect(()=>{const id=++request.current;fileRequest.current++;setContext(null);setError("");setPreview(null);if(!offerId)return;setLoading(true);
 api.get("/integrated/offers/"+encodeURIComponent(offerId)+"/context",{timeout:15000}).then(r=>{if(id===request.current)setContext(r.data)}).catch(()=>{if(id===request.current)setError("Não foi possível carregar o contexto da oferta. A cotação continua disponível; não há confirmação de documentos.")}).finally(()=>{if(id===request.current)setLoading(false)});
 return()=>{request.current++;fileRequest.current++};
 },[offerId,retry]);
 useEffect(()=>()=>{if(preview?.url)URL.revokeObjectURL(preview.url)},[preview]);
 async function view(file){const id=++fileRequest.current;try{const {data}=await api.get("/files/"+file.file_path,{responseType:"blob",timeout:60000});if(id!==fileRequest.current)return;const result=await documentPreview(data);if(id!==fileRequest.current){if(result.url)URL.revokeObjectURL(result.url);return}setPreview({...result,file})}catch{if(id===fileRequest.current)setError("Não foi possível abrir o arquivo privado. Os dados da cotação foram mantidos.")}}
 async function download(file){try{await downloadDocument(file)}catch{setError("Não foi possível baixar o arquivo privado.")}}
 if(!offerId)return null;
 return <section className="surface" aria-label="Fornecedor e documentos da cotação"><h2>Consultar fornecedor e documentos sem sair da cotação</h2>{loading&&<p role="status">Carregando vínculos da oferta…</p>}{error&&<><p role="alert">{error}</p><button type="button" onClick={()=>setRetry(n=>n+1)}>Recarregar consulta sem alterar cotação</button></>}{context&&<>
 <p><strong>{context.supplier.name}</strong> · {context.product.name}</p><p>{context.supplier.contact||"Contato não informado"} · {context.supplier.email||"E-mail não informado"} · {context.supplier.phone||"Telefone não informado"}</p>
 <details><summary>Condições registradas — confira a atualidade com o fornecedor</summary><dl>{Object.entries(context.conditions).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value||"Não informado"}</dd></div>)}</dl><p>Textos do cadastro não são convertidos em pesos, medidas ou valores presumidos.</p></details>
 {context.linksRequiringReview>0&&<p role="status">{context.linksRequiringReview} vínculo(s) sem documento visível único. Revise com a administração; nenhum dado foi removido.</p>}
 {!context.documents.length&&<p>Nenhum documento visível vinculado a esta oferta.</p>}
 {context.documents.map(doc=><article key={doc.kind+":"+doc.id}><strong>{doc.title}</strong><p>{doc.kind==="spec"?"Ficha técnica":doc.kind==="certification"?"Certificado":"Documento"}{doc.expiryDate?" · validade "+doc.expiryDate:""}{doc.flags.length?" · "+doc.flags.map(f=>labels[f]||"Revisar vínculo").join(" · "):""}</p>{doc.files.map((file,i)=><span key={i}><button type="button" onClick={()=>view(file)}>Visualizar {file.label}</button><button type="button" onClick={()=>download(file)}>Baixar {file.label}</button></span>)}</article>)}
 <p>Vínculo e validade são verificações de cadastro; não comprovam conformidade ou o conteúdo do PDF e não bloqueiam a cotação.</p>
 </>}{preview&&<section aria-label="Documento privado da oferta"><h3>{preview.file.label}</h3><button type="button" onClick={()=>{fileRequest.current++;setPreview(null)}}>Fechar documento e continuar cotação</button>{preview.kind==="pdf"?<object data={preview.url} type="application/pdf" aria-label="Prévia do documento privado" style={{width:"100%",height:600}}><p>Use Baixar para abrir o PDF.</p></object>:preview.kind==="image"?<img src={preview.url} alt={preview.file.file_name} style={{maxWidth:"100%"}}/>:<p>Formato sem prévia segura. Use Baixar.</p>}</section>}</section>
}
