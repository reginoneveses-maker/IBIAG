import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { SectionBar, Button, Input, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, useUpload, toast, Plus, Trash2, Upload, FileText, Download, downloadFile } from "@/components/erp";

export const DocumentsPanel = ({ category, title, subtitle, testId }) => {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const blank = { title: "", category, notes: "", file_path: "", file_name: "", content_type: "", size: 0 };
  const [form, setForm] = useState(blank);
  const { el, doUpload, uploading } = useUpload();

  const load = () => api.get("/documents", { params: { category } }).then(r => setItems(r.data));
  useEffect(() => { load(); }, [category]); // eslint-disable-line

  const save = async () => {
    if (!form.title || !form.file_path) return toast.error("Título e arquivo obrigatórios");
    await api.post("/documents", form);
    setOpen(false); setForm(blank); toast.success("Documento salvo"); load();
  };
  const del = async (id) => { await api.delete(`/documents/${id}`); load(); };

  return (
    <div data-testid={testId || `docs-${category}`}>
      {el}
      <SectionBar title={title} subtitle={subtitle}
        action={<Button onClick={() => { setForm(blank); setOpen(true); }} data-testid={`new-doc-${category}`} className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Adicionar</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map(d => (
          <Card key={d.id} className="bg-white border-[#0F382C]/10" data-testid={`doc-card-${d.id}`}>
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#EFECE6] flex items-center justify-center shrink-0"><FileText className="w-5 h-5 text-[#0F382C]" /></div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[#0F382C] truncate">{d.title}</div>
                  <div className="text-xs text-[#0F382C]/60 truncate">{d.file_name}</div>
                  <div className="text-[10px] font-mono-alt text-[#0F382C]/50 mt-1">{(d.created_at || "").slice(0, 10)}</div>
                </div>
              </div>
              {d.notes && <div className="text-xs text-[#0F382C]/70 mt-2 line-clamp-2">{d.notes}</div>}
              <div className="flex gap-2 mt-3">
                <Button size="sm" variant="outline" onClick={() => downloadFile(d.file_path, d.file_name)} data-testid={`doc-download-${d.id}`}><Download className="w-3 h-3 mr-1" />Baixar</Button>
                <Button size="sm" variant="ghost" onClick={() => del(d.id)} className="text-rose-600 ml-auto" data-testid={`doc-delete-${d.id}`}><Trash2 className="w-3 h-3" /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic" data-testid="docs-empty">Nenhum arquivo ainda. Clique em Adicionar.</div>}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-white">
          <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Título" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="doc-title-input" />
            <Input placeholder="Notas (opcional)" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} data-testid="doc-notes-input" />
            <Button onClick={() => doUpload(f => setForm({ ...form, file_path: f.path, file_name: f.name, content_type: f.content_type, size: f.size }))} disabled={uploading} variant="outline" data-testid="doc-upload-button" className="w-full">
              <Upload className="w-4 h-4 mr-2" />{form.file_name || (uploading ? "Enviando..." : "Enviar Arquivo (PDF, imagem, XML...)")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-doc-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
