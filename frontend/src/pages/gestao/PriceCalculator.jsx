import { useEffect, useState } from "react";
import { Button, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Plus, Trash2, fmtBRL, fmtUSD } from "@/components/erp";

export const DEFAULT_TAXES = [{ name: "ICMS", pct: 0 }, { name: "PIS/COFINS", pct: 0 }, { name: "Simples / IRPJ", pct: 6 }, { name: "Comissão", pct: 0 }];
export const DEFAULT_EXTRAS = [{ name: "Frete interno", value: 0 }, { name: "Embalagem", value: 0 }, { name: "Despachante / logística", value: 0 }];

export const computePrice = (f) => {
  const extras = f.extras.reduce((a, b) => a + (parseFloat(b.value) || 0), 0);
  const taxes = f.taxes.reduce((a, b) => a + (parseFloat(b.pct) || 0), 0);
  const cost = (parseFloat(f.supplier_price) || 0) + extras;
  let price;
  if (f.margin_mode === "markup") {
    const base = cost * (1 + (parseFloat(f.margin_pct) || 0) / 100);
    price = taxes < 100 ? base / (1 - taxes / 100) : base;
  } else {
    const div = 1 - ((parseFloat(f.margin_pct) || 0) + taxes) / 100;
    price = div > 0 ? cost / div : cost;
  }
  const taxValue = price * taxes / 100;
  const profit = price - taxValue - cost;
  const rate = parseFloat(f.exchange_rate) || 0;
  return { extras, taxes, cost, price, taxValue, profit, priceUsd: rate > 0 ? price / rate : 0, marginReal: price > 0 ? (profit / price) * 100 : 0, markupReal: cost > 0 ? (profit / cost) * 100 : 0 };
};

const Row = ({ label, children }) => (
  <div className="grid grid-cols-[1fr_auto] items-center gap-3"><span className="text-sm text-[#0F382C]/80">{label}</span>{children}</div>
);

export const PriceCalculator = ({ form, setForm, suppliers }) => {
  const [r, setR] = useState(computePrice(form));
  useEffect(() => { setR(computePrice(form)); }, [form]);
  const upd = (k, v) => setForm({ ...form, [k]: v });
  const updList = (key, i, field, v) => { const l = form[key].map((x, j) => j === i ? { ...x, [field]: v } : x); upd(key, l); };
  const addItem = (key, item) => upd(key, [...form[key], item]);
  const rmItem = (key, i) => upd(key, form[key].filter((_, j) => j !== i));
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "" }); };
  const inCls = "h-8 bg-white text-right w-28";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6" data-testid="price-calculator">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-2">
          <Input placeholder="Produto" value={form.product_name} onChange={e => upd("product_name", e.target.value)} className="col-span-2 bg-white" data-testid="price-product-input" />
          <Select value={form.supplier_id} onValueChange={setSup}>
            <SelectTrigger className="bg-white" data-testid="price-supplier-select"><SelectValue placeholder="Fornecedor" /></SelectTrigger>
            <SelectContent className="bg-white">{suppliers.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
          </Select>
          <Input placeholder="Unidade (kg, L, un)" value={form.unit} onChange={e => upd("unit", e.target.value)} className="bg-white" />
        </div>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">1 · Custo de aquisição (BRL / {form.unit})</div>
          <Row label="Preço que o fornecedor me passa"><Input type="number" step="0.0001" value={form.supplier_price} onChange={e => upd("supplier_price", e.target.value)} className={inCls} data-testid="price-supplier-price-input" /></Row>
        </section>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">2 · Custos adicionais por {form.unit} (BRL)</div>
          <div className="space-y-2">
            {form.extras.map((x, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                <Input value={x.name} onChange={e => updList("extras", i, "name", e.target.value)} className="h-8 bg-white" />
                <Input type="number" step="0.0001" value={x.value} onChange={e => updList("extras", i, "value", e.target.value)} className={inCls} data-testid={`price-extra-${i}`} />
                <Button size="sm" variant="ghost" onClick={() => rmItem("extras", i)} className="h-8 text-rose-600"><Trash2 className="w-3 h-3" /></Button>
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={() => addItem("extras", { name: "Outro custo", value: 0 })} className="text-amber-700 h-7" data-testid="price-add-extra"><Plus className="w-3 h-3 mr-1" />Adicionar custo</Button>
          </div>
        </section>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">3 · Impostos e taxas sobre a venda (%)</div>
          <div className="space-y-2">
            {form.taxes.map((x, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                <Input value={x.name} onChange={e => updList("taxes", i, "name", e.target.value)} className="h-8 bg-white" />
                <Input type="number" step="0.01" value={x.pct} onChange={e => updList("taxes", i, "pct", e.target.value)} className={inCls} data-testid={`price-tax-${i}`} />
                <Button size="sm" variant="ghost" onClick={() => rmItem("taxes", i)} className="h-8 text-rose-600"><Trash2 className="w-3 h-3" /></Button>
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={() => addItem("taxes", { name: "Outro imposto", pct: 0 })} className="text-amber-700 h-7" data-testid="price-add-tax"><Plus className="w-3 h-3 mr-1" />Adicionar imposto</Button>
          </div>
          <div className="text-xs text-[#0F382C]/50 mt-2">Dica: exportação é isenta de ICMS, PIS/COFINS e IPI — deixe 0% para venda externa.</div>
        </section>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">4 · Margem e moeda</div>
          <div className="space-y-2">
            <Row label="Modo de margem">
              <Select value={form.margin_mode} onValueChange={v => upd("margin_mode", v)}>
                <SelectTrigger className="h-8 bg-white w-56" data-testid="price-margin-mode"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-white"><SelectItem value="margin">Margem sobre o preço de venda</SelectItem><SelectItem value="markup">Markup sobre o custo</SelectItem></SelectContent>
              </Select>
            </Row>
            <Row label="Minha margem (%)"><Input type="number" step="0.1" value={form.margin_pct} onChange={e => upd("margin_pct", e.target.value)} className={inCls} data-testid="price-margin-input" /></Row>
            <Row label="Moeda de venda">
              <div className="flex gap-1 p-1 rounded-full border border-[#0F382C]/15 bg-white">
                {["BRL", "USD"].map(c => <button key={c} onClick={() => upd("currency", c)} data-testid={`price-currency-${c}`} className={`px-3 py-0.5 text-xs font-semibold rounded-full ${form.currency === c ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70"}`}>{c}</button>)}
              </div>
            </Row>
            <Row label="Câmbio (BRL por 1 USD)"><Input type="number" step="0.01" value={form.exchange_rate} onChange={e => upd("exchange_rate", e.target.value)} className={inCls} data-testid="price-exchange-input" /></Row>
          </div>
        </section>
      </div>

      <aside className="rounded-2xl bg-[#0F382C] text-white p-5 self-start sticky top-24" data-testid="price-result">
        <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-300">Preço de venda sugerido</div>
        <div className="font-display text-3xl sm:text-4xl font-extrabold mt-1" data-testid="price-result-main">{form.currency === "USD" ? fmtUSD(r.priceUsd).replace(/\$(\d+)$/, "$$$1") : fmtBRL(r.price)}<span className="text-base font-normal text-white/60"> / {form.unit}</span></div>
        <div className="text-sm text-white/70 mt-1" data-testid="price-result-secondary">{form.currency === "USD" ? fmtBRL(r.price) : `USD ${r.priceUsd.toFixed(2)}`}</div>
        <div className="mt-5 space-y-2 text-sm">
          {[["Custo fornecedor", fmtBRL(parseFloat(form.supplier_price) || 0)], ["Custos adicionais", fmtBRL(r.extras)], ["Custo total", fmtBRL(r.cost), true],
            [`Impostos (${r.taxes.toFixed(2)}%)`, fmtBRL(r.taxValue)], ["Lucro por " + form.unit, fmtBRL(r.profit), true],
            ["Margem real", `${r.marginReal.toFixed(1)}%`], ["Markup real", `${r.markupReal.toFixed(1)}%`]].map(([l, v, b]) => (
            <div key={l} className={`flex justify-between ${b ? "font-semibold border-t border-white/10 pt-2" : "text-white/80"}`}><span>{l}</span><span className="font-mono-alt">{v}</span></div>
          ))}
        </div>
      </aside>
    </div>
  );
};
