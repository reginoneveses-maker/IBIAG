import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Upload, Download, fmtBRL } from "@/components/erp";
import { AlertTriangle } from "lucide-react";

const empty = { title: "", kind: "contract", party: "", start_date: "", end_date: "", value: 0, file_path: "", file_name: "", notes: "" };

export default function Contracts() {
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();
  const load = () => api.get("/contracts").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.title) return toast.error("Título obrigatório");
    await api.post("/contracts", form); setDialog(false); setForm(empty); load();
  };
  const del = async (id) => { await api.delete(`/contracts/${id}`); load(); };
  const dl = async (p, n) => { const r = await api.get(`/files/${p}`, { responseType: "blob" }); const u = URL.createObjectURL(r.data); const a = document.createElement("a"); a.href = u; a.download = n; a.click(); };

  const daysUntil = (d) => { if (!d) return null; const dt = new Date(d) - new Date(); return Math.ceil(dt / 86400000); };

  return (
    <div data-testid="contracts-page">
      {el}
      <PageHeader number="06 · Contratos & Certificações" title="Contratos & Certificações" subtitle="Nunca perca uma renovação — alerta a 30 dias do vencimento"
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-contract-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map(c => {
          const days = daysUntil(c.end_date);
          const expiring = days !== null && days >= 0 && days <= 30;
          const expired = days !== null && days < 0;
          return (
            <Card key={c.id} className={`bg-white border-[#0F382C]/10 ${expired ? "border-rose-300" : expiring ? "border-amber-400" : ""}`}>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">{c.kind}</div>
                    <div className="font-semibold text-[#0F382C]">{c.title}</div>
                    <div className="text-xs text-[#0F382C]/60">{c.party}</div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => del(c.id)} className="text-rose-600"><Trash2 className="w-3 h-3" /></Button>
                </div>
                <div className="mt-2 text-sm text-[#0F382C]/80">Vigência: {c.start_date || "—"} → {c.end_date || "—"}</div>
                {c.value > 0 && <div className="text-sm text-amber-700 font-mono-alt">{fmtBRL(c.value)}</div>}
                {(expiring || expired) && (
                  <div className={`mt-2 p-2 rounded text-xs flex items-center gap-1 ${expired ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-800"}`}>
                    <AlertTriangle className="w-3 h-3" />{expired ? `Vencido há ${Math.abs(days)} dias` : `Vence em ${days} dias`}
                  </div>
                )}
                {c.file_path && <Button size="sm" variant="outline" onClick={() => dl(c.file_path, c.file_name)} className="mt-2"><Download className="w-3 h-3 mr-1" />Baixar</Button>}
              </CardContent>
            </Card>
          );
        })}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic">Nenhum contrato ainda.</div>}
      </div>
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Contrato / Certificação</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Input placeholder="Título" value={form.title} onChange={e => setForm({...form, title: e.target.value})} data-testid="con-title-input" />
            <Select value={form.kind} onValueChange={v => setForm({...form, kind: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white"><SelectItem value="contract">Contrato</SelectItem><SelectItem value="certification">Certificação</SelectItem></SelectContent>
            </Select>
            <Input placeholder="Parte / Órgão" value={form.party} onChange={e => setForm({...form, party: e.target.value})} />
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} />
              <Input type="date" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} data-testid="con-end-date-input" />
            </div>
            <Input type="number" step="0.01" placeholder="Valor (BRL)" value={form.value} onChange={e => setForm({...form, value: parseFloat(e.target.value) || 0})} />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} rows={2} />
            <Button onClick={() => doUpload(f => setForm({...form, file_path: f.path, file_name: f.name}))} variant="outline" disabled={uploading} className="w-full">
              <Upload className="w-4 h-4 mr-1" />{form.file_name || (uploading ? "..." : "Anexar Arquivo")}
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
