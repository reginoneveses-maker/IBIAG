import {useEffect,useRef,useState} from 'react';
import {api,useAuth} from '@/AuthContext';
import {documentPreview,downloadDocument} from '@/lib/api';
import {Button} from '@/components/ui/button';
import {toast} from 'sonner';
import {cardIbiagSpecs,catalogSpecCode} from '@/pages/gestao/catalogCards';

export default function CatalogSpecActions({card,specs=[],onSaved}) {
  const {user}=useAuth();
  const [preview,setPreview]=useState(null), [picker,setPicker]=useState(false), [documents,setDocuments]=useState([]);
  const [selected,setSelected]=useState(''),[confirmed,setConfirmed]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState('');
  const [suppliers,setSuppliers]=useState([]),[supplier,setSupplier]=useState(''),[loading,setLoading]=useState(false);
  const request=useRef(0);
  useEffect(()=>()=>{request.current+=1;},[]);
  useEffect(()=>()=>{if(preview?.url)URL.revokeObjectURL(preview.url);},[preview]);
  const files=cardIbiagSpecs(card,specs);
  const download=async(path,name)=>{try{await downloadDocument({file_path:path,file_name:name});}catch{toast.error('Não foi possível baixar a ficha.');}};
  const view=async(path,name)=>{
    const id=++request.current;
    try{
      const r=await api.get('/files/'+path,{responseType:'blob'});
      if(id!==request.current)return;
      const result=await documentPreview(r.data);
      if(id!==request.current){if(result.url)URL.revokeObjectURL(result.url);return;}
      setPreview({...result,path,title:name});
    }catch{toast.error('Não foi possível visualizar a ficha.');}
  };
  const choose=async()=>{
    setPicker(true);setLoading(true);setSupplier(card.cardOffer?.supplier_id || '');setError('');setSelected('');setConfirmed(false);setDocuments([]);
    try{
      const supplierResponse=await api.get('/suppliers');setSuppliers(supplierResponse.data || []);
      const all=[];let skip=0;
      while(true){const r=await api.get('/documents/page',{params:{skip,limit:250,trash:false}});const rows=r.data.items || [];all.push(...rows);if(rows.length<250)break;skip+=250;}
      setDocuments(all.filter(d=>!d.deleted_at && d.file_path && /\.pdf$/i.test(d.file_name||'')));
    }catch{setError('Não foi possível carregar os PDFs. Tente novamente.');}finally{setLoading(false);}
  };
  const save=async()=>{
    const doc=documents.find(d=>d.id===selected);
    if(!doc||!confirmed||!supplier||saving)return;
    setSaving(true);setError('');
    try{
      const code=catalogSpecCode(card);
      const existing=specs.find(s=>s.code===code);
      const body={...(existing||{}),supplier_id:supplier,supplier_name:card.cardOffer?.supplier_name || doc.supplier_name || '',product_name:card.cardName,code,ibiag_file_path:doc.file_path,ibiag_file_name:doc.file_name,notes:'Versão IBIAG vinculada explicitamente pelo administrador para este card.'};
      if(existing)await api.put('/specs/'+existing.id,body);else await api.post('/specs',body);
      await onSaved();setPicker(false);toast.success('Ficha IBIAG vinculada ao card.');
    }catch{setError('Não foi possível salvar o vínculo. Confira o fornecedor do documento e tente novamente.');}
    finally{setSaving(false);}
  };
  return <section className="space-y-2" aria-label={'Ficha de '+card.cardName}>
    {files.map(s=><div key={s.id} className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={()=>view(s.ibiag_file_path,s.ibiag_file_name)}>Visualizar ficha IBIAG</Button><Button size="sm" variant="outline" onClick={()=>download(s.ibiag_file_path,s.ibiag_file_name)}>Baixar PDF</Button></div>)}
    {!files.length&&<><p className="text-xs">Ficha IBIAG ainda não vinculada a esta variação.</p><Button size="sm" variant="outline" disabled>Visualizar ficha IBIAG</Button> <Button size="sm" variant="outline" disabled>Baixar PDF</Button></>}
    {user?.role==='admin'&&<Button size="sm" variant="outline" onClick={choose}>{files.length?'Alterar ficha IBIAG':'Vincular ficha IBIAG'}</Button>}
    <div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled>Enviar por e-mail · Integração pendente</Button><Button size="sm" variant="outline" disabled>Enviar por WhatsApp · Integração pendente</Button></div>
    {picker&&<div role="dialog" aria-modal="true" aria-label="Vincular ficha IBIAG" className="fixed inset-0 z-[90] bg-black/50 p-4 flex items-center justify-center"><div className="bg-white rounded-xl p-5 max-w-xl w-full space-y-4"><h2 className="font-bold">Ficha IBIAG · {card.cardName}</h2><label className="block">Fornecedor<select aria-label="Fornecedor da ficha" className="w-full border rounded p-2" value={supplier} onChange={e=>{setSupplier(e.target.value);setConfirmed(false);}}><option value="">Selecione o fornecedor</option>{suppliers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>{loading&&<p role="status">Carregando PDFs…</p>}<label className="block">PDF da Central de Documentos<select aria-label="PDF IBIAG" className="w-full border rounded p-2" value={selected} onChange={e=>{setSelected(e.target.value);setConfirmed(false);}}><option value="">Selecione um PDF</option>{documents.map(d=><option key={d.id} value={d.id}>{d.title||d.file_name}</option>)}</select></label><Button disabled={!selected} variant="outline" onClick={()=>{const d=documents.find(x=>x.id===selected);if(d)view(d.file_path,d.file_name);}}>Conferir PDF</Button><label className="flex gap-2"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Conferi: este PDF está no padrão IBIAG, sem identificação do fornecedor, e corresponde exatamente a esta variação.</label>{error&&<p role="alert">{error}</p>}<div className="flex flex-wrap gap-2"><Button disabled={saving} variant="outline" onClick={()=>setPicker(false)}>Cancelar</Button><Button disabled={!selected||!confirmed||!supplier||saving} onClick={save}>{saving?'Salvando…':'Salvar vínculo'}</Button></div></div></div>}
    {preview&&<div role="dialog" aria-modal="true" aria-label="Visualização da ficha" className="fixed inset-0 z-[100] bg-black/50 p-4 flex flex-col"><div className="bg-white p-3 flex flex-wrap gap-3"><b>{preview.title}</b><Button variant="outline" onClick={()=>download(preview.path,preview.title)}>Baixar arquivo</Button><Button className="ml-auto" variant="outline" onClick={()=>{request.current+=1;setPreview(null);}}>Fechar ficha</Button></div>{preview.kind==='pdf'?<object aria-label="Prévia da ficha IBIAG" data={preview.url} type="application/pdf" className="bg-white w-full flex-1"><p>Use Baixar arquivo para abrir.</p></object>:preview.kind==='image'?<div className="overflow-auto bg-white flex-1"><img alt={preview.title} src={preview.url} className="max-w-full mx-auto"/></div>:<p className="bg-white p-5">Formato sem prévia. Use Baixar arquivo.</p>}</div>}
  </section>;
}
