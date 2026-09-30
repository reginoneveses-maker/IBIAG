import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { PageHeader, SupplierTabs, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Pencil, Upload, Download, FileText, downloadFile } from "@/components/erp";

const empty = { supplier_id: "", supplier_name: "", product_name: "", code: "", version: "1.0", description: "", original_file_path: "", original_file_name: "", ibiag_file_path: "", ibiag_file_name: "", notes: "" };

const FileSlot = ({ label, path, name, onUpload, onDownload, testId }) => (
  <div className="rounded-lg border border-dashed border-[#0F382C]/20 p-3 bg-[#F9F6F0]" data-testid={testId}>
    <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-1">{label}</div>
    {path ? (
      <div className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-[#0F382C]" />
        <span className="text-xs text-[#0F382C] truncate flex-1">{name}</span>
        <Button size="sm" variant="outline" onClick={onDownload} className="h-7"><Download className="w-3 h-3" /></Button>
        <Button size="sm" variant="ghost" onClick={onUpload} className="h-7 text-xs">Trocar</Button>
      </div>
    ) : (
      <Button size="sm" variant="ghost" onClick={onUpload} className="h-7 text-xs text-amber-700"><Upload className="w-3 h-3 mr-1" />Enviar arquivo</Button>
    )}
  </div>
);

export default function Specs() {
  const [sp, setSp] = useSearchParams();
  const active = sp.get("supplier") || "";
  const [suppliers, setSuppliers] = useState([]);
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();

  const loadSup = () => api.get("/suppliers").then(r => setSuppliers(r.data));
  const load = () => api.get("/specs", { params: active ? { supplier_id: active } : {} }).then(r => setItems(r.data));
  useEffect(() => { loadSup(); }, []);
  useEffect(() => { load(); }, [active]); // eslint-disable-line

  const setActive = (id) => { const n = new URLSearchParams(sp); if (id) n.set("supplier", id); else n.delete("supplier"); setSp(n); };
  const openNew = () => { const s = suppliers.find(x => x.id === active); setForm({ ...empty, supplier_id: active, supplier_name: s?.name || "" }); setDialog(true); };
  const save = async () => {
    if (!form.product_name) return toast.error("Nome do produto obrigatório");
    if (!form.supplier_id) return toast.error("Selecione o fornecedor");
    if (form.id) await api.put(`/specs/${form.id}`, form); else await api.post("/specs", form);
    setDialog(false); toast.success("Spec salva"); load();
  };
  const del = async (id) => { await api.delete(`/specs/${id}`); load(); };
  const attach = async (spec, slot) => {
    doUpload(async f => {
      const body = { ...spec, [`${slot}_file_path`]: f.path, [`${slot}_file_name`]: f.name };
      await api.put(`/specs/${spec.id}`, body); toast.success("Arquivo anexado"); load();
    });
  };
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "" }); };

  return (
    <div data-testid="specs-page">
      {el}
      <PageHeader number="04 · Prospecção IBIAG" title="Specs por Fornecedor" subtitle="Ficha técnica original do fornecedor e a versão IBIAG de cada produto"
        action={<Button onClick={openNew} data-testid="new-spec-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Nova Spec</Button>} />
      <SupplierTabs suppliers={suppliers} active={active} onChange={setActive} onCreate={(s) => { loadSup(); setActive(s.id); }} allLabel="Todos" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {items.map(s => (
          <Card key={s.id} className="bg-white border-[#0F382C]/10" data-testid={`spec-${s.id}`}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0">
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">{s.supplier_name} {s.code && `· ${s.code}`} · v{s.version}</div>
                  <div className="font-semibold text-[#0F382C] text-lg">{s.product_name}</div>
                  {s.description && <div className="text-xs text-[#0F382C]/70 mt-1 line-clamp-2">{s.description}</div>}
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button size="sm" variant="ghost" onClick={() => { setForm(s); setDialog(true); }} data-testid={`edit-spec-${s.id}`}><Pencil className="w-3 h-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => del(s.id)} className="text-rose-600" data-testid={`delete-spec-${s.id}`}><Trash2 className="w-3 h-3" /></Button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
                <FileSlot label="Spec original (fornecedor)" path={s.original_file_path} name={s.original_file_name} testId={`spec-original-${s.id}`}
                  onUpload={() => attach(s, "original")} onDownload={() => downloadFile(s.original_file_path, s.original_file_name)} />
                <FileSlot label="Versão IBIAG" path={s.ibiag_file_path} name={s.ibiag_file_name} testId={`spec-ibiag-${s.id}`}
                  onUpload={() => attach(s, "ibiag")} onDownload={() => downloadFile(s.ibiag_file_path, s.ibiag_file_name)} />
              </div>
              {uploading && <div className="text-[10px] text-[#0F382C]/50 mt-1">Enviando...</div>}
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic" data-testid="specs-empty">Nenhuma spec cadastrada. Crie uma aba de fornecedor e adicione a primeira.</div>}
      </div>

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
