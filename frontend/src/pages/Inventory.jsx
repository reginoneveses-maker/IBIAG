import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Card, CardContent, toast } from "@/components/erp";

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [edits, setEdits] = useState({});
  const load = () => api.get("/products").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  const update = async (id) => {
    const v = edits[id]; if (v === undefined) return;
    await api.patch(`/products/${id}/stock`, { stock: parseFloat(v) || 0 });
    toast.success("Estoque atualizado"); setEdits({ ...edits, [id]: undefined }); load();
  };

  return (
    <div data-testid="inventory-page">
      <PageHeader number="07 · Estoque" title="Estoque" subtitle="Controle de estoque por produto (SKU)" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map(p => (
          <Card key={p.id} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4 flex items-center gap-3">
              <img src={p.image_url} alt="" className="w-16 h-16 rounded-lg object-cover bg-[#EFECE6]" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-[#0F382C] truncate">{p.name}</div>
                <div className="text-xs text-[#0F382C]/60 font-mono-alt">SKU: {p.sku || "—"}</div>
                <div className="text-sm text-amber-700 font-mono-alt mt-1">{(p.stock || 0).toLocaleString()} {p.unit}</div>
              </div>
              <div className="flex flex-col gap-1">
                <Input type="number" placeholder="Novo" value={edits[p.id] ?? ""} onChange={e => setEdits({ ...edits, [p.id]: e.target.value })} className="w-24" data-testid={`stock-input-${p.id}`} />
                <Button size="sm" onClick={() => update(p.id)} data-testid={`update-stock-${p.id}`} className="bg-[#0F382C] text-white">OK</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
