import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { SectionBar, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Pencil, Upload, Download, fmtBRL, downloadFile } from "@/components/erp";

const STATUS = { ordered: ["Pedido", "bg-blue-100 text-blue-800"], received: ["Recebido", "bg-amber-100 text-amber-800"], paid: ["Pago", "bg-emerald-100 text-emerald-800"], cancelled: ["Cancelado", "bg-rose-100 text-rose-700"] };
const empty = { supplier_id: "", supplier_name: "", product: "", quantity: 0, unit: "kg", unit_price: 0, total: 0, currency: "BRL", date: "", status: "ordered", invoice_number: "", file_path: "", file_name: "", notes: "" };

export default function Compras() {
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [filter, setFilter] = useState("all");
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();
  const load = () => api.get("/purchases").then(r => setItems(r.data));
  useEffect(() => { load(); api.get("/suppliers").then(r => setSuppliers(r.data)); }, []);

  const save = async () => {
    if (!form.product) return toast.error("Produto obrigatório");
    const body = { ...form, total: +(form.quantity * form.unit_price).toFixed(2) };
    if (form.id) await api.put(`/purchases/${form.id}`, body); else await api.post("/purchases", body);
    setDialog(false); setForm(empty); toast.success("Compra salva"); load();
  };
  const del = async (id) => { await api.delete(`/purchases/${id}`); load(); };
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "" }); };
  const filtered = filter === "all" ? items : items.filter(x => x.status === filter);
  const total = filtered.filter(x => x.status !== "cancelled").reduce((a, b) => a + (b.total || 0), 0);

  return (
    <div data-testid="compras-panel">
      {el}
      <SectionBar title="Compras" subtitle={`Total ${filter === "all" ? "geral" : STATUS[filter]?.[0]}: ${fmtBRL(total)}`}
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-purchase-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Nova Compra</Button>} />
      <div className="flex gap-2 mb-4 flex-wrap">
        {[["all", "Todas"], ...Object.entries(STATUS).map(([k, v]) => [k, v[0]])].map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} data-testid={`pur-filter-${k}`} className={`px-3 py-1.5 text-sm rounded-full border ${filter === k ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15"}`}>{l}</button>
        ))}
      </div>
      <div className="space-y-2">
        {filtered.map(p => (
          <Card key={p.id} className="bg-white border-[#0F382C]/10" data-testid={`purchase-${p.id}`}>
            <CardContent className="p-4 flex flex-wrap items-center gap-3">
              <span className={`px-2 py-1 rounded text-[10px] font-mono-alt uppercase ${STATUS[p.status]?.[1]}`}>{STATUS[p.status]?.[0] || p.status}</span>
              <div className="flex-1 min-w-[180px]">
                <div className="font-semibold text-[#0F382C]">{p.product} <span className="text-[#0F382C]/50 font-normal">· {p.quantity} {p.unit}</span></div>
                <div className="text-xs text-[#0F382C]/60">{p.supplier_name || "—"} · {p.date || "sem data"} {p.invoice_number && `· NF ${p.invoice_number}`}</div>
              </div>
              <div className="text-right">
                <div className="font-mono-alt font-semibold text-[#0F382C]">{fmtBRL(p.total)}</div>
                <div className="text-[10px] text-[#0F382C]/50">{fmtBRL(p.unit_price)}/{p.unit}</div>
              </div>
              {p.file_path && <Button size="sm" variant="ghost" onClick={() => downloadFile(p.file_path, p.file_name)}><Download className="w-3 h-3" /></Button>}
              <Button size="sm" variant="ghost" onClick={() => { setForm(p); setDialog(true); }} data-testid={`edit-purchase-${p.id}`}><Pencil className="w-3 h-3" /></Button>
              <Button size="sm" variant="ghost" onClick={() => del(p.id)} className="text-rose-600" data-testid={`delete-purchase-${p.id}`}><Trash2 className="w-3 h-3" /></Button>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && <div className="text-sm text-[#0F382C]/50 italic" data-testid="purchases-empty">Nenhuma compra registrada.</div>}
      </div>

      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Compra</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Select value={form.supplier_id} onValueChange={setSup}>
              <SelectTrigger className="bg-white col-span-2" data-testid="pur-supplier-select"><SelectValue placeholder="Fornecedor" /></SelectTrigger>
              <SelectContent className="bg-white">{suppliers.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Produto" value={form.product} onChange={e => setForm({ ...form, product: e.target.value })} className="col-span-2" data-testid="pur-product-input" />
            <Input type="number" step="0.01" placeholder="Quantidade" value={form.quantity} onChange={e => setForm({ ...form, quantity: parseFloat(e.target.value) || 0 })} data-testid="pur-qty-input" />
            <Input placeholder="Unidade (kg, L, un)" value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} />
            <Input type="number" step="0.0001" placeholder="Preço unitário (BRL)" value={form.unit_price} onChange={e => setForm({ ...form, unit_price: parseFloat(e.target.value) || 0 })} data-testid="pur-price-input" />
            <div className="flex items-center px-3 text-sm font-mono-alt text-[#0F382C] bg-[#EFECE6] rounded-md" data-testid="pur-total">Total: {fmtBRL(form.quantity * form.unit_price)}</div>
            <Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} />
            <Select value={form.status} onValueChange={v => setForm({ ...form, status: v })}>
              <SelectTrigger className="bg-white" data-testid="pur-status-select"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white">{Object.entries(STATUS).map(([k, v]) => <SelectItem key={k} value={k}>{v[0]}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Nº NF (opcional)" value={form.invoice_number} onChange={e => setForm({ ...form, invoice_number: e.target.value })} className="col-span-2" />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2} className="col-span-2" />
            <Button onClick={() => doUpload(f => setForm({ ...form, file_path: f.path, file_name: f.name }))} variant="outline" className="col-span-2" disabled={uploading}>
              <Upload className="w-4 h-4 mr-1" />{form.file_name || (uploading ? "Enviando..." : "Anexar pedido / NF / comprovante")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-purchase-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
