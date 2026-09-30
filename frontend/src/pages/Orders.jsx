import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, toast, Plus, Trash2 } from "@/components/erp";
import { fmtUSD } from "@/lib/api";

const empty = { number: "", customer: "", customer_country: "", products: "", incoterm: "FOB", total_usd: 0, status: "draft", order_date: "", delivery_date: "", notes: "" };
const STATUSES = ["draft", "confirmed", "shipped", "delivered", "cancelled"];
const STATUS_COLORS = { draft: "bg-slate-100 text-slate-700", confirmed: "bg-blue-100 text-blue-800", shipped: "bg-amber-100 text-amber-800", delivered: "bg-green-100 text-green-800", cancelled: "bg-rose-100 text-rose-700" };

export default function Orders() {
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const load = () => api.get("/orders").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.customer) return toast.error("Cliente obrigatório");
    if (form.id) await api.put(`/orders/${form.id}`, form); else await api.post("/orders", form);
    setDialog(false); setForm(empty); load();
  };
  const del = async (id) => { await api.delete(`/orders/${id}`); load(); };
  const total = items.reduce((a, b) => a + (b.total_usd || 0), 0);

  return (
    <div data-testid="orders-page">
      <PageHeader number="04 · Pedidos de Venda" title="Pedidos" subtitle="Pedidos de exportação"
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-order-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo Pedido</Button>} />
      <Card className="bg-white border-[#0F382C]/10 mb-4"><CardContent className="p-4">
        <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">Total em Pedidos</div>
        <div className="font-display text-2xl font-bold text-amber-700">{fmtUSD(total)}</div>
      </CardContent></Card>
      <div className="space-y-2">
        {items.map(o => (
          <Card key={o.id} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-1 rounded text-[10px] font-mono-alt uppercase ${STATUS_COLORS[o.status]}`}>{o.status}</span>
                <div className="flex-1">
                  <div className="font-semibold text-[#0F382C]">{o.number || "Pedido"} — {o.customer}</div>
                  <div className="text-xs text-[#0F382C]/60">{o.customer_country} · {o.incoterm} · {o.order_date}</div>
                </div>
                <div className="font-mono-alt font-semibold text-amber-700">{fmtUSD(o.total_usd)}</div>
                <Button size="sm" variant="ghost" onClick={() => { setForm(o); setDialog(true); }}>Editar</Button>
                <Button size="sm" variant="ghost" onClick={() => del(o.id)} className="text-rose-600"><Trash2 className="w-3 h-3" /></Button>
              </div>
              {o.products && <div className="text-xs text-[#0F382C]/70 mt-2">{o.products}</div>}
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="text-sm text-[#0F382C]/50 italic">Nenhum pedido ainda.</div>}
      </div>
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Pedido</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Número" value={form.number} onChange={e => setForm({...form, number: e.target.value})} />
            <Select value={form.status} onValueChange={v => setForm({...form, status: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white">{STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Cliente" value={form.customer} onChange={e => setForm({...form, customer: e.target.value})} className="col-span-2" data-testid="ord-customer-input" />
            <Input placeholder="País" value={form.customer_country} onChange={e => setForm({...form, customer_country: e.target.value})} />
            <Select value={form.incoterm} onValueChange={v => setForm({...form, incoterm: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white">{["FOB", "CIF", "CFR", "EXW", "DDP"].map(i => <SelectItem key={i} value={i}>{i}</SelectItem>)}</SelectContent>
            </Select>
            <Input type="date" value={form.order_date} onChange={e => setForm({...form, order_date: e.target.value})} />
            <Input type="date" value={form.delivery_date} onChange={e => setForm({...form, delivery_date: e.target.value})} />
            <Input type="number" step="0.01" placeholder="Total USD" value={form.total_usd} onChange={e => setForm({...form, total_usd: parseFloat(e.target.value) || 0})} className="col-span-2" />
            <Textarea placeholder="Produtos" value={form.products} onChange={e => setForm({...form, products: e.target.value})} rows={2} className="col-span-2" />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} rows={2} className="col-span-2" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-order-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
