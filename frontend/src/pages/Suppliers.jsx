import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, toast, Plus, Trash2 } from "@/components/erp";

const empty = { name: "", cnpj: "", contact: "", email: "", phone: "", address: "", products: "", notes: "" };

export default function Suppliers() {
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const load = () => api.get("/suppliers").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.name) return toast.error("Nome obrigatório");
    if (form.id) await api.put(`/suppliers/${form.id}`, form); else await api.post("/suppliers", form);
    setDialog(false); setForm(empty); load();
  };
  const del = async (id) => { await api.delete(`/suppliers/${id}`); load(); };

  return (
    <div data-testid="suppliers-page">
      <PageHeader number="03 · Fornecedores" title="Fornecedores" subtitle="Cadastro de fornecedores e parceiros"
        action={<Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-supplier-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Novo</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map(s => (
          <Card key={s.id} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4">
              <div className="flex justify-between">
                <div className="font-semibold text-[#0F382C]">{s.name}</div>
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => { setForm(s); setDialog(true); }}>Editar</Button>
                  <Button size="sm" variant="ghost" onClick={() => del(s.id)} className="text-rose-600"><Trash2 className="w-3 h-3" /></Button>
                </div>
              </div>
              <div className="text-xs text-[#0F382C]/60 mt-1">{s.cnpj}</div>
              <div className="text-sm text-[#0F382C]/80 mt-2">{s.contact} · {s.email} · {s.phone}</div>
              {s.products && <div className="text-xs text-amber-700 mt-2">Produtos: {s.products}</div>}
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic">Nenhum fornecedor ainda.</div>}
      </div>
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Fornecedor</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Input placeholder="Nome" value={form.name} onChange={e => setForm({...form, name: e.target.value})} data-testid="sup-name-input" />
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="CNPJ" value={form.cnpj} onChange={e => setForm({...form, cnpj: e.target.value})} />
              <Input placeholder="Contato" value={form.contact} onChange={e => setForm({...form, contact: e.target.value})} />
              <Input placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
              <Input placeholder="Telefone" value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} />
            </div>
            <Input placeholder="Endereço" value={form.address} onChange={e => setForm({...form, address: e.target.value})} />
            <Input placeholder="Produtos que fornece" value={form.products} onChange={e => setForm({...form, products: e.target.value})} />
            <Textarea placeholder="Notas" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} rows={2} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-supplier-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
