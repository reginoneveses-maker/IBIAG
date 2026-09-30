import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, toast, Plus, Trash2, fmtBRL } from "@/components/erp";
import { Checkbox } from "@/components/ui/checkbox";

const empty = { kind: "receivable", description: "", party: "", amount: 0, currency: "BRL", due_date: "", category: "" };

export default function Finance() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const load = () => api.get("/finance").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.description) return toast.error("Descrição obrigatória");
    await api.post("/finance", form); setDialog(false); setForm(empty); load();
  };
  const toggle = async (id) => { await api.patch(`/finance/${id}/toggle-paid`); load(); };
  const del = async (id) => { await api.delete(`/finance/${id}`); load(); };
  const filtered = filter === "all" ? items : items.filter(x => filter === "paid" ? x.paid : filter === "pending" ? !x.paid : x.kind === filter);
  const recv = items.filter(x => x.kind === "receivable" && !x.paid).reduce((a, b) => a + b.amount, 0);
  const pay = items.filter(x => x.kind === "payable" && !x.paid).reduce((a, b) => a + b.amount, 0);

  return (
    <div data-testid="finance-page">
      <PageHeader number="05 · Financeiro" title="Financeiro" subtitle="Contas a pagar e a receber"
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-finance-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo Lançamento</Button>} />
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="bg-white border-[#0F382C]/10"><CardContent className="p-4">
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">A Receber</div>
          <div className="font-display text-2xl font-bold text-emerald-700">{fmtBRL(recv)}</div>
        </CardContent></Card>
        <Card className="bg-white border-[#0F382C]/10"><CardContent className="p-4">
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">A Pagar</div>
          <div className="font-display text-2xl font-bold text-rose-600">{fmtBRL(pay)}</div>
        </CardContent></Card>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {[["all", "Todos"], ["receivable", "A Receber"], ["payable", "A Pagar"], ["pending", "Pendentes"], ["paid", "Pagos"]].map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} data-testid={`fin-filter-${k}`} className={`px-3 py-1.5 text-sm rounded-full border ${filter === k ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15"}`}>{l}</button>
        ))}
      </div>
      <div className="space-y-2">
        {filtered.map(f => (
          <Card key={f.id} className={`bg-white border-[#0F382C]/10 ${f.paid ? "opacity-60" : ""}`}>
            <CardContent className="p-4 flex items-center gap-3">
              <Checkbox checked={f.paid} onCheckedChange={() => toggle(f.id)} data-testid={`fin-toggle-${f.id}`} />
              <div className={`px-2 py-1 rounded text-[10px] font-mono-alt uppercase ${f.kind === "receivable" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-700"}`}>{f.kind === "receivable" ? "Receber" : "Pagar"}</div>
              <div className="flex-1">
                <div className={`font-semibold text-[#0F382C] ${f.paid ? "line-through" : ""}`}>{f.description}</div>
                <div className="text-xs text-[#0F382C]/60">{f.party} · vence {f.due_date || "—"}</div>
              </div>
              <div className="font-mono-alt font-semibold">{fmtBRL(f.amount)}</div>
              <Button size="sm" variant="ghost" onClick={() => del(f.id)} className="text-rose-600"><Trash2 className="w-3 h-3" /></Button>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && <div className="text-sm text-[#0F382C]/50 italic">Sem lançamentos.</div>}
      </div>
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Lançamento</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Select value={form.kind} onValueChange={v => setForm({...form, kind: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white"><SelectItem value="receivable">A Receber</SelectItem><SelectItem value="payable">A Pagar</SelectItem></SelectContent>
            </Select>
            <Input placeholder="Categoria (opcional)" value={form.category} onChange={e => setForm({...form, category: e.target.value})} />
            <Input placeholder="Descrição" value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="col-span-2" data-testid="fin-desc-input" />
            <Input placeholder="Parte" value={form.party} onChange={e => setForm({...form, party: e.target.value})} />
            <Input type="number" step="0.01" placeholder="Valor" value={form.amount} onChange={e => setForm({...form, amount: parseFloat(e.target.value) || 0})} data-testid="fin-amount-input" />
            <Input type="date" value={form.due_date} onChange={e => setForm({...form, due_date: e.target.value})} className="col-span-2" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-finance-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
