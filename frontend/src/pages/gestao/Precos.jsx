import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast, Plus, Trash2, Pencil, fmtBRL } from "@/components/erp";
import { PriceCalculator, DEFAULT_TAXES, DEFAULT_EXTRAS } from "@/pages/gestao/PriceCalculator";
import { Calculator } from "lucide-react";

const empty = { product_name: "", supplier_id: "", supplier_name: "", unit: "kg", supplier_price: 0, extras: DEFAULT_EXTRAS, taxes: DEFAULT_TAXES, margin_pct: 30, margin_mode: "margin", currency: "BRL", exchange_rate: 5.2, notes: "" };

export default function Precos() {
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const load = () => api.get("/prices").then(r => setItems(r.data));
  useEffect(() => { load(); api.get("/suppliers").then(r => setSuppliers(r.data)); }, []);

  const save = async () => {
    if (!form.product_name) return toast.error("Informe o produto");
    const body = { ...form, supplier_price: parseFloat(form.supplier_price) || 0, margin_pct: parseFloat(form.margin_pct) || 0, exchange_rate: parseFloat(form.exchange_rate) || 0,
      extras: form.extras.map(x => ({ name: x.name, value: parseFloat(x.value) || 0 })), taxes: form.taxes.map(x => ({ name: x.name, pct: parseFloat(x.pct) || 0 })) };
    if (form.id) await api.put(`/prices/${form.id}`, body); else await api.post("/prices", body);
    setDialog(false); toast.success("Preço salvo"); load();
  };
  const del = async (id) => { await api.delete(`/prices/${id}`); load(); };
  const edit = (p) => setForm({ ...p, extras: p.extras?.length ? p.extras : DEFAULT_EXTRAS, taxes: p.taxes?.length ? p.taxes : DEFAULT_TAXES });

  return (
    <div data-testid="precos-page">
      <PageHeader number="05 · Preços" title="Preços dos Produtos" subtitle="Preço do fornecedor, preço de venda e calculadora profissional com margem e impostos"
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-price-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Calculator className="w-4 h-4 mr-1" />Calcular novo preço</Button>} />

      <Card className="bg-white border-[#0F382C]/10 overflow-hidden">
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-sm" data-testid="prices-table">
            <thead className="bg-[#EFECE6] text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/70">
              <tr>
                <th className="text-left px-4 py-3">Produto</th><th className="text-left px-4 py-3">Fornecedor</th>
                <th className="text-right px-4 py-3">Custo fornec.</th><th className="text-right px-4 py-3">Custo total</th>
                <th className="text-right px-4 py-3">Impostos</th><th className="text-right px-4 py-3">Margem</th>
                <th className="text-right px-4 py-3">Venda BRL</th><th className="text-right px-4 py-3">Venda USD</th><th className="px-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(p => (
                <tr key={p.id} className="border-t border-[#0F382C]/5 hover:bg-[#F9F6F0]" data-testid={`price-row-${p.id}`}>
                  <td className="px-4 py-3 font-semibold text-[#0F382C]">{p.product_name}<div className="text-[10px] text-[#0F382C]/50 font-normal">/ {p.unit} · {p.margin_mode === "markup" ? "markup" : "margem"}</div></td>
                  <td className="px-4 py-3 text-[#0F382C]/80">{p.supplier_name || "—"}</td>
                  <td className="px-4 py-3 text-right font-mono-alt">{fmtBRL(p.supplier_price)}</td>
                  <td className="px-4 py-3 text-right font-mono-alt">{fmtBRL(p.supplier_price + p.extra_costs)}</td>
                  <td className="px-4 py-3 text-right font-mono-alt">{p.taxes_pct.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-right font-mono-alt">{p.margin_pct.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-right font-mono-alt font-bold text-[#0F382C]">{fmtBRL(p.sell_price_brl)}</td>
                  <td className="px-4 py-3 text-right font-mono-alt font-bold text-amber-700">${p.sell_price_usd.toFixed(2)}</td>
                  <td className="px-2 py-3 whitespace-nowrap">
                    <Button size="sm" variant="ghost" onClick={() => { edit(p); setDialog(true); }} data-testid={`edit-price-${p.id}`}><Pencil className="w-3 h-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => del(p.id)} className="text-rose-600" data-testid={`delete-price-${p.id}`}><Trash2 className="w-3 h-3" /></Button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-[#0F382C]/50 italic" data-testid="prices-empty">Nenhum preço calculado. Clique em "Calcular novo preço".</td></tr>}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-[#F9F6F0] max-w-4xl max-h-[92vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display text-[#0F382C]">Calculadora de Preços</DialogTitle></DialogHeader>
          <PriceCalculator form={form} setForm={setForm} suppliers={suppliers} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-price-button" className="bg-[#0F382C] text-white"><Plus className="w-4 h-4 mr-1" />Salvar na tabela</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
