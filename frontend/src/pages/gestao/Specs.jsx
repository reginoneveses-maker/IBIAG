import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, useAuth } from "@/AuthContext";
import { PageHeader, SupplierTabs, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Pencil, Upload, Download, FileText, downloadFile } from "@/components/erp";

import { documentPreview } from "@/lib/api";

const empty = { supplier_id: "", supplier_name: "", product_name: "", code: "", version: "1.0", description: "", original_file_path: "", original_file_name: "", ibiag_file_path: "", ibiag_file_name: "", notes: "" };

const FileSlot = ({ label, path, name, onUpload, onDownload, onPreview, allowUpload = true, testId }) => (
  <div className="rounded-lg border border-dashed border-[#0F382C]/20 p-3 bg-[#F9F6F0]" data-testid={testId}>
    <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-1">{label}</div>
    {path ? (
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-[#0F382C]" />
        <span className="text-xs text-[#0F382C] truncate flex-1">{name}</span>
        <Button size="sm" variant="outline" onClick={onPreview} className="h-7 text-xs">Visualizar</Button>
        <Button aria-label={`Baixar ${name}`} size="sm" variant="outline" onClick={onDownload} className="h-7"><Download className="w-3 h-3" /></Button>
        {allowUpload && <Button size="sm" variant="ghost" onClick={onUpload} className="h-7 text-xs">Trocar</Button>}
      </div>
    ) : (
      allowUpload ? <Button size="sm" variant="ghost" onClick={onUpload} className="h-7 text-xs text-amber-700"><Upload className="w-3 h-3 mr-1" />Enviar arquivo</Button> : <span className="text-xs">Arquivo não disponível</span>
    )}
  </div>
);

export default function Specs() {
  const [sp, setSp] = useSearchParams();
  const active = sp.get("supplier") || "";
  const [suppliers, setSuppliers] = useState([]);
  const [library, setLibrary] = useState({items: [], unassigned: [], counts: {}});
  const [loading, setLoading] = useState(true), [error, setError] = useState("");
  const [assignment, setAssignment] = useState({}), [assigning, setAssigning] = useState("");
  const [preview, setPreview] = useState(null);
  const {user} = useAuth();
  const requestId = useRef(0), previewRequest = useRef(0);
  const items = useMemo(() => active === "__unassigned__" ? library.unassigned : library.items.filter(s => !active || s.supplier_id === active), [library, active]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();

  const loadSup = () => api.get("/suppliers").then(r => setSuppliers(r.data)).catch(() => toast.error("Não foi possível carregar os fornecedores."));
  const load = useCallback(async () => {
    const request = ++requestId.current; setLoading(true); setError("");
    try { const r = await api.get("/specs/library"); if (request === requestId.current) setLibrary(r.data); }
    catch(e) { if (request === requestId.current) { setLibrary({items:[],unassigned:[],counts:{}}); setError("Não foi possível carregar os specs: " + (e.response?.data?.detail || e.message)); } }
    finally { if (request === requestId.current) setLoading(false); }
  }, []);
  useEffect(() => { loadSup(); }, []);
  useEffect(() => { load(); return () => { requestId.current += 1; }; }, [load]);
  useEffect(() => { previewRequest.current += 1; setPreview(null); }, [active]);
  useEffect(() => () => { previewRequest.current += 1; }, []);
  useEffect(() => () => { if(preview?.url) URL.revokeObjectURL(preview.url); }, [preview]);
  const download = async (path, name) => { try { await downloadFile(path, name); } catch(e) { toast.error("Não foi possível baixar a spec."); } };
  const viewFile = async (path, name) => {
    const request = ++previewRequest.current;
    try {
      const r = await api.get(`/files/${path}`, {responseType:"blob"});
      if (request !== previewRequest.current) return;
      const file = await documentPreview(r.data);
      if (request !== previewRequest.current) { if(file.url) URL.revokeObjectURL(file.url); return; }
      setPreview({title:name,path,...file});
    } catch(e) { if (request === previewRequest.current) toast.error("Não foi possível visualizar a spec."); }
  };
  const assignDocument = async row => {
    setAssigning(row.id);
    try { await api.patch(`/specs/documents/${encodeURIComponent(row.document_id)}/supplier`, {supplier_id: assignment[row.id]}); toast.success("Spec vinculada ao fornecedor."); await load(); }
    catch(e) { toast.error(e.response?.data?.detail || "Não foi possível vincular a spec."); }
    finally { setAssigning(""); }
  };

  const setActive = (id) => { const n = new URLSearchParams(sp); if (id) n.set("supplier", id); else n.delete("supplier"); setSp(n); };
  const openNew = () => { const s = suppliers.find(x => x.id === active); setForm({ ...empty, supplier_id: s?.id || "", supplier_name: s?.name || "" }); setDialog(true); };
  const save = async () => {
    if (!form.product_name) return toast.error("Nome do produto obrigatório");
    if (!form.supplier_id) return toast.error("Selecione o fornecedor");
    try {
      if (form.id) await api.put(`/specs/${form.id}`, form); else await api.post("/specs", form);
      setDialog(false); toast.success("Spec salva"); await load();
    } catch(e) { toast.error(e.response?.data?.detail || "Não foi possível salvar a spec."); }
  };
  const del = async (id) => { try { await api.delete(`/specs/${id}`); await load(); } catch(e) { toast.error("Não foi possível excluir a spec."); } };
  const attach = async (spec, slot) => {
    doUpload(async f => {
      const body = { ...spec, [`${slot}_file_path`]: f.path, [`${slot}_file_name`]: f.name };
      try { await api.put(`/specs/${spec.id}`, body); toast.success("Arquivo anexado"); await load(); } catch(e) { toast.error(e.response?.data?.detail || "Não foi possível anexar o arquivo."); }
    });
  };
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "" }); };

  return (
    <div data-testid="specs-page">
      {el}
      <PageHeader number="04 · Prospecção IBIAG" title="Specs por Fornecedor" subtitle="Ficha técnica original do fornecedor e a versão IBIAG de cada produto"
        action={<Button onClick={openNew} data-testid="new-spec-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Nova Spec</Button>} />
      <SupplierTabs suppliers={suppliers} active={active} counts={library.counts} onChange={setActive} onCreate={(s) => { loadSup(); setActive(s.id); }} allLabel="Todos" />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <span className="text-sm">{active === "__unassigned__" ? "Specs sem fornecedor confirmado" : active ? `Specs de ${suppliers.find(s => s.id === active)?.name || "fornecedor"}` : "Specs de todos os fornecedores"} · {items.length} specs</span>
        <Button variant="outline" onClick={load} disabled={loading}>Atualizar specs</Button>
        {library.unassigned.length > 0 && <Button variant="outline" onClick={() => setActive("__unassigned__")}>Sem fornecedor ({library.unassigned.length})</Button>}
      </div>
      <p className="text-xs text-slate-500 mb-4">Inclui os cadastros de specs, as fichas técnicas da Central de Documentos e os arquivos vinculados às ofertas. Cada fornecedor mostra apenas seus specs identificados.</p>
      {loading && <p role="status">Carregando specs...</p>}
      {error && <p role="alert">{error}</p>}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {!loading && items.map(s => (
          <Card key={s.id} className="bg-white border-[#0F382C]/10" data-testid={`spec-${s.id}`}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0">
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">{s.supplier_name} {s.code && `· ${s.code}`} {s.version && `· v${s.version}`}</div>
                  <div className="font-semibold text-[#0F382C] text-lg">{s.product_name}</div>
                  {s.description && <div className="text-xs text-[#0F382C]/70 mt-1 line-clamp-2">{s.description}</div>}
                </div>
                {s.source_type !== "document" && <div className="flex gap-1 shrink-0">
                  <Button size="sm" variant="ghost" onClick={() => { setForm(s); setDialog(true); }} data-testid={`edit-spec-${s.id}`}><Pencil className="w-3 h-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => del(s.id)} className="text-rose-600" data-testid={`delete-spec-${s.id}`}><Trash2 className="w-3 h-3" /></Button>
                </div>}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
                <FileSlot label={s.source_type === "document" ? "Spec vinculada ao fornecedor" : "Spec original (fornecedor)"} path={s.original_file_path} name={s.original_file_name} testId={`spec-original-${s.id}`}
                  allowUpload={s.source_type !== "document"} onPreview={() => viewFile(s.original_file_path, s.original_file_name)} onUpload={() => attach(s, "original")} onDownload={() => download(s.original_file_path, s.original_file_name)} />
                {s.source_type !== "document" && <FileSlot label="Versão IBIAG" path={s.ibiag_file_path} name={s.ibiag_file_name} testId={`spec-ibiag-${s.id}`}
                  onPreview={() => viewFile(s.ibiag_file_path, s.ibiag_file_name)} onUpload={() => attach(s, "ibiag")} onDownload={() => download(s.ibiag_file_path, s.ibiag_file_name)} />}
              </div>
              {s.source_type === "document" && <p className="text-xs mt-2 text-slate-500">Arquivo da Central de Documentos{s.title && ` · ${s.title}`}</p>}
              {active === "__unassigned__" && <div className="mt-3 space-y-2"><p className="text-xs text-amber-800">{s.assignment_reason}</p>{user?.role === "admin" && s.source_type === "document" && <div className="flex gap-2"><select aria-label={`Fornecedor de ${s.product_name}`} value={assignment[s.id] || ""} onChange={e => setAssignment(prev => ({...prev,[s.id]:e.target.value}))} className="border rounded p-2 text-sm"><option value="">Selecione o fornecedor correspondente</option>{suppliers.map(supplier => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select><Button disabled={!assignment[s.id] || !!assigning} onClick={() => assignDocument(s)}>Vincular fornecedor</Button></div>}</div>}
              {uploading && <div className="text-[10px] text-[#0F382C]/50 mt-1">Enviando...</div>}
            </CardContent>
          </Card>
        ))}
        {!loading && !error && items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic" data-testid="specs-empty">Nenhuma spec vinculada a este fornecedor. Confira também a aba Sem fornecedor ou cadastre uma nova spec.</div>}
      </div>

      {preview && <div className="fixed inset-0 z-50 bg-black/50 p-4 flex flex-col"><div className="bg-white p-3 flex flex-wrap gap-4 items-center"><b>{preview.title}</b><button className="underline" onClick={() => download(preview.path,preview.title)}>Baixar arquivo</button>{preview.kind !== "unsupported" && <a className="underline" href={preview.url} target="_blank" rel="noreferrer">Abrir em nova aba</a>}<button aria-label="Fechar visualização da spec" onClick={() => { previewRequest.current += 1; setPreview(null); }} className="ml-auto">Fechar</button></div>{preview.kind === "pdf" ? <object aria-label={`Prévia PDF ${preview.title}`} data={preview.url} type="application/pdf" className="w-full flex-1 bg-white"><p>Use Abrir em nova aba ou Baixar arquivo.</p></object> : preview.kind === "image" ? <div className="flex-1 overflow-auto bg-white"><img alt={preview.title} src={preview.url} className="max-w-full mx-auto" /></div> : <div className="bg-white p-6 flex-1">Este formato deve ser baixado para abrir no aplicativo correspondente.</div>}</div>}
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Spec do produto</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Select value={form.supplier_id} onValueChange={setSup}>
              <SelectTrigger className="bg-white col-span-2" data-testid="spec-supplier-select"><SelectValue placeholder="Fornecedor" /></SelectTrigger>
              <SelectContent className="bg-white">{suppliers.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Produto" value={form.product_name} onChange={e => setForm({ ...form, product_name: e.target.value })} className="col-span-2" data-testid="spec-product-input" />
            <Input placeholder="Código interno" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} />
            <Input placeholder="Versão" value={form.version} onChange={e => setForm({ ...form, version: e.target.value })} />
            <Textarea placeholder="Descrição / parâmetros principais" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={3} className="col-span-2" />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2} className="col-span-2" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-spec-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
