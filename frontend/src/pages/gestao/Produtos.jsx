import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Input, Textarea, toast, Plus, Pencil, Search, Truck, FileCheck2 } from "@/components/erp";
import { Link } from "react-router-dom";

const empty = {
  name: "", category: "acai", hs_code: "", ncm: "", technical_name: "", origin: "",
  description_pt: "", description_en: "", moq: "", packaging: "", unit: "kg",
  certifications: [], specs: "", price_range: "", image_url: "", sku: "", stock: 0,
  available_capacity: "", incoterm: "", lead_time: "", payment_terms: "",
  current_customers: "", target_markets: "", price_history_notes: ""
};

const field = (label, key, form, setForm, props = {}) => (
  <div className={props.className || ""}>
    <label className="block text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/55 mb-1">{label}</label>
    <Input value={form[key] ?? ""} onChange={e => setForm({ ...form, [key]: e.target.value })} className="bg-white" {...props.inputProps} />
  </div>
);

export default function Produtos() {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const [prices, setPrices] = useState([]);

  const load = () => Promise.all([api.get("/products"), api.get("/prices")]).then(([p, pr]) => { setItems(p.data || []); setPrices(pr.data || []); }).catch(() => {});
  useEffect(() => { load(); }, []);

  const filtered = items.filter(p => {
    const q = search.toLowerCase();
    return !q || [p.name, p.technical_name, p.ncm, p.hs_code, p.origin].join(" ").toLowerCase().includes(q);
  });

  const openNew = () => { setForm({ ...empty, certifications: [] }); setDialog(true); };
  const edit = p => setForm({ ...empty, ...p, certifications: p.certifications || [] });

  const save = async () => {
    if (!form.name.trim()) return toast.error("Informe o nome comercial");
    const body = { ...form, stock: parseFloat(form.stock) || 0, certifications: Array.isArray(form.certifications) ? form.certifications : [] };
    if (form.id) await api.put(`/products/${form.id}`, body);
    else await api.post("/products", body);
    setDialog(false); toast.success("Produto salvo"); load();
  };

  const remove = async id => {
    if (!window.confirm("Excluir este produto?")) return;
    await api.delete(`/products/${id}`); load(); toast.success("Produto excluído");
  };

  return (
    <div data-testid="produtos-page" className="space-y-5">
      <PageHeader number="02 · Produtos" title="Portfólio de Produtos" subtitle="Tudo o que a IBIAG vende: formas, fornecedores, custos, preços e acesso rápido à documentação"
        action={<Button onClick={openNew} className="bg-[#0F382C] text-white"><Plus className="w-4 h-4 mr-1" />Novo produto</Button>} />

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xl"><Search className="absolute left-3 top-2.5 w-4 h-4 text-[#0F382C]/40" /><Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar produto, NCM, HS, origem..." className="pl-9 bg-white" /></div>
        <span className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/45">{filtered.length} produtos</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(p => (
          <Card key={p.id} className="bg-white border-[#0F382C]/10 hover:border-[#0F382C]/25 transition-colors">
            <CardContent className="p-5">
              <div className="flex justify-between gap-3">
                <div>
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">{p.category} · {p.unit}</div>
                  <h3 className="font-display text-xl font-bold text-[#0F382C] mt-1">{p.name}</h3>
                  <p className="text-xs text-[#0F382C]/55 mt-1">{p.technical_name || "Nome técnico não informado"}</p>
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => { edit(p); setDialog(true); }}><Pencil className="w-3 h-3" /></Button>
                </div>
              </div>
              <div className="mt-5 rounded-xl border border-[#0F382C]/8 bg-[#F9F6F0]/50 p-3">
                <div className="flex items-center gap-2 text-[10px] font-mono-alt uppercase tracking-widest text-amber-700 mb-2"><Truck className="w-3.5 h-3.5" /> Fornecedores e preços</div>
                {prices.filter(x => (x.product_name || "").trim().toLowerCase() === (p.name || "").trim().toLowerCase()).map(o => (
                  <div key={o.id} className="flex items-center justify-between gap-3 py-2 border-t first:border-t-0 border-[#0F382C]/8 text-xs">
                    <div><div className="font-semibold">{o.supplier_name || "Fornecedor não informado"}</div><div className="text-[#0F382C]/45">{o.unit || p.unit} · custo fornecedor</div></div>
                    <div className="text-right"><div className="font-mono-alt font-semibold">{Number(o.supplier_price || 0).toLocaleString("pt-BR",{style:"currency",currency:"BRL"})}</div><div className="text-amber-700">${Number(o.sell_price_usd || 0).toFixed(2)}</div></div>
                  </div>
                ))}
                {!prices.some(x => (x.product_name || "").trim().toLowerCase() === (p.name || "").trim().toLowerCase()) && <div className="text-xs text-[#0F382C]/45">Nenhum fornecedor/preço vinculado. Cadastre em Preços & calculadora.</div>}
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <Link to="/gestao/prospeccao"><Button size="sm" variant="outline"><FileCheck2 className="w-3.5 h-3.5 mr-1" />Specs & documentos</Button></Link>
                <Link to="/gestao/precos"><Button size="sm" variant="outline">Preços</Button></Link>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-5 text-xs">
                <div><span className="text-[#0F382C]/45">NCM / HS</span><div className="font-semibold">{p.ncm || "—"} {p.hs_code ? `/ ${p.hs_code}` : ""}</div></div>
                <div><span className="text-[#0F382C]/45">Origem</span><div className="font-semibold">{p.origin || "—"}</div></div>
                <div><span className="text-[#0F382C]/45">MOQ</span><div className="font-semibold">{p.moq || "—"}</div></div>
                <div><span className="text-[#0F382C]/45">Capacidade</span><div className="font-semibold">{p.available_capacity || "—"}</div></div>
              </div>
              <div className="flex flex-wrap gap-1 mt-4">
                {(p.certifications || []).slice(0, 5).map(c => <span key={c} className="px-2 py-1 rounded-full bg-[#F9F6F0] border border-[#0F382C]/10 text-[10px]">{c}</span>)}
              </div>
              <div className="flex gap-2 mt-5">
                <Button size="sm" variant="outline" className="flex-1" onClick={() => { edit(p); setDialog(true); }}>Abrir dossiê</Button>
                <Button size="sm" variant="ghost" className="text-rose-600" onClick={() => remove(p.id)}>Excluir</Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {!filtered.length && <Card className="col-span-full bg-white"><CardContent className="py-12 text-center text-sm text-[#0F382C]/50">Nenhum produto cadastrado.</CardContent></Card>}
      </div>

      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-[#F9F6F0] max-w-4xl max-h-[92vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display text-[#0F382C]">{form.id ? "Dossiê do produto" : "Novo produto"}</DialogTitle></DialogHeader>
          <div className="space-y-6">
            <section>
              <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700 mb-3">Identidade e classificação</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {field("Nome comercial", "name", form, setForm, { className: "sm:col-span-2" })}
                {field("Nome técnico", "technical_name", form, setForm)}
                {field("Categoria", "category", form, setForm)}
                {field("NCM", "ncm", form, setForm)}
                {field("HS Code", "hs_code", form, setForm)}
                {field("Origem", "origin", form, setForm)}
                {field("SKU / código interno", "sku", form, setForm)}
                {field("Unidade", "unit", form, setForm)}
              </div>
            </section>

            <section>
              <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700 mb-3">Oferta e operação</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {field("MOQ", "moq", form, setForm)}
                {field("Embalagem", "packaging", form, setForm)}
                {field("Capacidade disponível", "available_capacity", form, setForm)}
                {field("Lead time", "lead_time", form, setForm)}
                {field("Incoterm", "incoterm", form, setForm)}
                {field("Condições de pagamento", "payment_terms", form, setForm)}
                {field("Faixa de preço", "price_range", form, setForm)}
                {field("Imagem / URL", "image_url", form, setForm)}
              </div>
            </section>

            <section>
              <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700 mb-3">Mercado e documentação</div>
              <div className="grid gap-3">
                {field("Certificações (separe por vírgula)", "certifications", { ...form, certifications: (form.certifications || []).join(", ") }, f => setForm({ ...form, certifications: f.certifications.split(",").map(x => x.trim()).filter(Boolean) }))}
                <Textarea placeholder="Especificações / parâmetros principais" value={form.specs || ""} onChange={e => setForm({ ...form, specs: e.target.value })} className="bg-white" rows={3} />
                <Textarea placeholder="Descrição comercial em português" value={form.description_pt || ""} onChange={e => setForm({ ...form, description_pt: e.target.value })} className="bg-white" rows={3} />
                <Textarea placeholder="Mercados-alvo / países" value={form.target_markets || ""} onChange={e => setForm({ ...form, target_markets: e.target.value })} className="bg-white" rows={2} />
                <Textarea placeholder="Clientes atuais / referências comerciais" value={form.current_customers || ""} onChange={e => setForm({ ...form, current_customers: e.target.value })} className="bg-white" rows={2} />
                <Textarea placeholder="Observações e histórico de preços" value={form.price_history_notes || ""} onChange={e => setForm({ ...form, price_history_notes: e.target.value })} className="bg-white" rows={3} />
              </div>
            </section>
          </div>
          <DialogFooter>
            {form.id && <Button variant="ghost" className="mr-auto text-rose-600" onClick={() => { remove(form.id); setDialog(false); }}>Excluir</Button>}
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-[#0F382C] text-white">Salvar dossiê</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
