import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, SectionBar, ExpiryBadge, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Pencil, Upload, Download, fmtBRL, downloadFile } from "@/components/erp";

const empty = { title: "", kind: "contract", party: "", supplier_id: "", start_date: "", end_date: "", value: 0, file_path: "", file_name: "", notes: "" };

export default function Contracts({ embedded }) {
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();
  const load = () => api.get("/contracts", { params: { kind: "contract" } }).then(r => setItems(r.data));
  useEffect(() => { load(); api.get("/suppliers").then(r => setSuppliers(r.data)); }, []);
  const save = async () => {
    if (!form.title) return toast.error("Título obrigatório");
    if (form.id) await api.put(`/contracts/${form.id}`, form); else await api.post("/contracts", form);
    setDialog(false); setForm(empty); toast.success("Contrato salvo"); load();
  };
  const del = async (id) => { await api.delete(`/contracts/${id}`); load(); };
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, party: s?.name || form.party }); };
  const action = <Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-contract-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo Contrato</Button>;

  return (
    <div data-testid="contracts-page">
      {el}
      {embedded
        ? <SectionBar title="Contratos com Fornecedores" subtitle="Vigência, valor e arquivo assinado — alerta a 30 dias do vencimento" action={action} />
        : <PageHeader number="06 · Contratos" title="Contratos" subtitle="Nunca perca uma renovação — alerta a 30 dias do vencimento" action={action} />}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map(c => (
          <Card key={c.id} className="bg-white border-[#0F382C]/10" data-testid={`contract-${c.id}`}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">Contrato</div>
                  <div className="font-semibold text-[#0F382C]">{c.title}</div>
                  <div className="text-xs text-[#0F382C]/60">{c.party}</div>
                </div>
                <div className="flex items-center gap-1">
                  <ExpiryBadge date={c.end_date} />
                  <Button size="sm" variant="ghost" onClick={() => { setForm({ ...empty, ...c }); setDialog(true); }} data-testid={`edit-contract-${c.id}`}><Pencil className="w-3 h-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => del(c.id)} className="text-rose-600" data-testid={`delete-contract-${c.id}`}><Trash2 className="w-3 h-3" /></Button>
                </div>
              </div>
              <div className="mt-2 text-sm text-[#0F382C]/80">Vigência: {c.start_date || "—"} → {c.end_date || "—"}</div>
              {c.value > 0 && <div className="text-sm text-amber-700 font-mono-alt">{fmtBRL(c.value)}</div>}
              {c.notes && <div className="text-xs text-[#0F382C]/70 mt-1">{c.notes}</div>}
              {c.file_path && <Button size="sm" variant="outline" onClick={() => downloadFile(c.file_path, c.file_name)} className="mt-2"><Download className="w-3 h-3 mr-1" />Baixar</Button>}
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic" data-testid="contracts-empty">Nenhum contrato ainda.</div>}
      </div>
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Contrato</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Input placeholder="Título" value={form.title} onChange={e => setForm({...form, title: e.target.value})} data-testid="con-title-input" />
            <Select value={form.supplier_id} onValueChange={setSup}>
              <SelectTrigger className="bg-white" data-testid="con-supplier-select"><SelectValue placeholder="Fornecedor (opcional)" /></SelectTrigger>
              <SelectContent className="bg-white">{suppliers.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Parte contratada" value={form.party} onChange={e => setForm({...form, party: e.target.value})} data-testid="con-party-input" />
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-[10px] uppercase text-[#0F382C]/60">Início</label><Input type="date" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} /></div>
              <div><label className="text-[10px] uppercase text-[#0F382C]/60">Fim</label><Input type="date" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} data-testid="con-end-date-input" /></div>
            </div>
            <Input type="number" step="0.01" placeholder="Valor (BRL)" value={form.value} onChange={e => setForm({...form, value: parseFloat(e.target.value) || 0})} />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} rows={2} />
            <Button onClick={() => doUpload(f => setForm({...form, file_path: f.path, file_name: f.name}))} variant="outline" disabled={uploading} className="w-full">
              <Upload className="w-4 h-4 mr-1" />{form.file_name || (uploading ? "..." : "Anexar contrato assinado")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-contract-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
