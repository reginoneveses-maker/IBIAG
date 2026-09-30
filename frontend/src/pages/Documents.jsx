import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Upload, FileText, Download } from "@/components/erp";

const CATEGORIES = ["general", "legal", "technical", "financial", "certification", "other"];

export default function Documents() {
  const [items, setItems] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ title: "", category: "general", notes: "", file_path: "", file_name: "", content_type: "", size: 0 });
  const { el, doUpload, uploading } = useUpload();

  const load = () => api.get("/documents").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.title || !form.file_path) return toast.error("Título e arquivo obrigatórios");
    await api.post("/documents", form);
    setDialogOpen(false); setForm({ title: "", category: "general", notes: "", file_path: "", file_name: "", content_type: "", size: 0 });
    toast.success("Documento salvo"); load();
  };
  const del = async (id) => { await api.delete(`/documents/${id}`); load(); };
  const dl = async (path, name) => {
    const r = await api.get(`/files/${path}`, { responseType: "blob" });
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
  };

  return (
    <div data-testid="documents-page">
      {el}
      <PageHeader number="01 · Documentos" title="Documentos" subtitle="Todos os documentos da sua empresa em um só lugar"
        action={<Button onClick={() => setDialogOpen(true)} data-testid="new-doc-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo Documento</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map(d => (
          <Card key={d.id} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#EFECE6] flex items-center justify-center"><FileText className="w-5 h-5 text-[#0F382C]" /></div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[#0F382C] truncate">{d.title}</div>
                  <div className="text-xs text-[#0F382C]/60 truncate">{d.file_name}</div>
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700 mt-1">{d.category}</div>
                </div>
              </div>
              {d.notes && <div className="text-xs text-[#0F382C]/70 mt-2 line-clamp-2">{d.notes}</div>}
              <div className="flex gap-2 mt-3">
                <Button size="sm" variant="outline" onClick={() => dl(d.file_path, d.file_name)}><Download className="w-3 h-3 mr-1" />Baixar</Button>
                <Button size="sm" variant="ghost" onClick={() => del(d.id)} className="text-rose-600 ml-auto"><Trash2 className="w-3 h-3" /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic">Nenhum documento ainda. Adicione o primeiro!</div>}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader><DialogTitle>Novo Documento</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Título" value={form.title} onChange={e => setForm({...form, title: e.target.value})} data-testid="doc-title-input" />
            <Select value={form.category} onValueChange={v => setForm({...form, category: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white">{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Notas" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />
            <Button onClick={() => doUpload(f => setForm({...form, file_path: f.path, file_name: f.name, content_type: f.content_type, size: f.size}))} disabled={uploading} variant="outline" data-testid="doc-upload-button" className="w-full">
              <Upload className="w-4 h-4 mr-2" />{form.file_name || (uploading ? "Enviando..." : "Enviar Arquivo")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-doc-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
