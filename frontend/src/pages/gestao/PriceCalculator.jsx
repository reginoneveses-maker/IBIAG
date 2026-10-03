import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { computePrice, priceMoney } from "@/lib/pricing";
export { computePrice } from "@/lib/pricing";
import { Button, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Plus, Trash2 } from "@/components/erp";

export const DEFAULT_TAXES = [{ name: "ICMS", pct: 0 }, { name: "PIS/COFINS", pct: 0 }, { name: "Simples / IRPJ", pct: 6 }, { name: "Comissão", pct: 0 }];
export const DEFAULT_EXTRAS = [{ name: "Frete interno", value: 0 }, { name: "Embalagem", value: 0 }, { name: "Despachante / logística", value: 0 }];

const Row = ({ label, children }) => (
  <div className="grid grid-cols-[1fr_auto] items-center gap-3"><span className="text-sm text-[#0F382C]/80">{label}</span>{children}</div>
);

export const PriceCalculator = ({ form, setForm, suppliers = [] }) => {
  const r = computePrice(form);
  const [offers, setOffers] = useState([]), [offersLoading, setOffersLoading] = useState(false), [offersError, setOffersError] = useState(false), [reloadOffers, setReloadOffers] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setOffers([]); setOffersError(false);
    if (!form.supplier_id) { setOffersLoading(false); return () => { current = false; controller.abort(); }; }
    setOffersLoading(true);
    api.get("/product-offers", {params:{supplier_id:form.supplier_id,active:true},signal:controller.signal})
      .then(response => { if (current) setOffers(response.data.filter(o => o.supplier_id === form.supplier_id && o.active !== false)
        .sort((a,b) => (a.product_name || "").localeCompare(b.product_name || "", "pt-BR"))); })
      .catch(() => { if(current) setOffersError(true); })
      .finally(() => { if(current) setOffersLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [form.supplier_id,reloadOffers]);
  const savedChoice = form.product_name && !offers.some(o => o.id === form.offer_id);
  const chooseProduct = id => {
    if (id === "saved" || !id) return;
    const offer = offers.find(o => o.id === id);
    if (offer) setForm({...form,offer_id:offer.id,product_id:offer.product_id,product_name:offer.product_name,unit:offer.unit||"kg",supplier_price:0});
  };
  const upd = (k, v) => setForm({ ...form, [k]: v });
  const updList = (key, i, field, v) => { const l = form[key].map((x, j) => j === i ? { ...x, [field]: v } : x); upd(key, l); };
  const addItem = (key, item) => upd(key, [...form[key], item]);
  const rmItem = (key, i) => upd(key, form[key].filter((_, j) => j !== i));
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "", product_name:"", product_id:"", offer_id:"", supplier_price:0 }); };
  const inCls = "h-8 bg-white text-right w-28";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6" data-testid="price-calculator">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2 space-y-1 text-sm">Fornecedor
            <select aria-label="Fornecedor" value={form.supplier_id} onChange={e=>setSup(e.target.value)} className="block w-full h-10 rounded-md border bg-white px-3" data-testid="price-supplier-select">
              <option value="">Selecione o fornecedor</option>
              {suppliers.map(s=><option key={s.id} value={s.id} children={s.name}/>)}
            </select>
          </label>
          <label className="col-span-2 space-y-1 text-sm">Produto do fornecedor
            <select aria-label="Produto do fornecedor" value={form.offer_id || (form.product_name ? "saved" : "")} onChange={e=>chooseProduct(e.target.value)}
              disabled={!form.supplier_id || offersLoading || offersError || (!offers.length && !savedChoice)}
              className="block w-full h-10 rounded-md border bg-white px-3 disabled:opacity-60" data-testid="price-product-select">
              <option value="">Selecione o produto</option>
              {savedChoice && <option value={form.offer_id||"saved"} children={`${form.product_name} (cálculo salvo)`}/>}
              {offers.map(o=><option key={o.id} value={o.id} children={`${o.product_name}${o.form && o.form !== o.product_name ? " · " + o.form : ""}`}/>)}
            </select>
          </label>
          {offersLoading && <p role="status" className="col-span-2 text-xs">Carregando produtos do fornecedor…</p>}
          {offersError && <div role="alert" className="col-span-2 text-xs">Não foi possível carregar os produtos. <Button variant="outline" size="sm" onClick={()=>setReloadOffers(x=>x+1)}>Tentar novamente</Button></div>}
          {!offersLoading && !offersError && form.supplier_id && !offers.length && <p className="col-span-2 text-xs">Este fornecedor não tem ofertas ativas cadastradas. Vincule os produtos em Gestão → Produtos.</p>}
          <label className="space-y-1 text-sm">Quantidade
            <Input aria-label="Quantidade" inputMode="decimal" value={form.quantity??1} onChange={e=>upd("quantity",e.target.value)} placeholder="Ex.: 1000" className="bg-white" data-testid="price-quantity-input"/>
          </label>
          <label className="space-y-1 text-sm">Unidade
            <select aria-label="Unidade" value={form.unit} disabled={!!form.offer_id} onChange={e=>upd("unit",e.target.value)} className="block w-full h-10 rounded-md border bg-white px-3" data-testid="price-unit-select">
              {[...new Set(["kg","L","un","t",form.unit])].filter(Boolean).map(unit=><option key={unit} value={unit} children={unit}/>)}
            </select>
          </label>
        </div>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">1 · Custo de aquisição (BRL / {form.unit})</div>
          <Row label="Preço do fornecedor por unidade (BRL)"><Input aria-label="Preço do fornecedor por unidade" inputMode="decimal" value={form.supplier_price} onChange={e => upd("supplier_price", e.target.value)} className={inCls} data-testid="price-supplier-price-input" /></Row>
        </section>

        <section>
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-2">2 · Custos adicionais por {form.unit} (BRL)</div>
          <div className="space-y-2">
            {form.extras.map((x, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                <Input value={x.name} onChange={e => updList("extras", i, "name", e.target.value)} className="h-8 bg-white" />
                <Input inputMode="decimal" value={x.value} onChange={e => updList("extras", i, "value", e.target.value)} className={inCls} data-testid={`price-extra-${i}`} />
                <Button size="sm" variant="ghost" aria-label={`Remover custo ${x.name}`} onClick={() => rmItem("extras", i)} className="h-8 text-rose-600"><Trash2 className="w-3 h-3" /></Button>
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
                <Input inputMode="decimal" value={x.pct} onChange={e => updList("taxes", i, "pct", e.target.value)} className={inCls} data-testid={`price-tax-${i}`} />
                <Button size="sm" variant="ghost" aria-label={`Remover imposto ${x.name}`} onClick={() => rmItem("taxes", i)} className="h-8 text-rose-600"><Trash2 className="w-3 h-3" /></Button>
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={() => addItem("taxes", { name: "Outro imposto", pct: 0 })} className="text-amber-700 h-7" data-testid="price-add-tax"><Plus className="w-3 h-3 mr-1" />Adicionar imposto</Button>
          </div>
          <div className="text-xs text-[#0F382C]/50 mt-2">Informe os percentuais aplicáveis à operação. Custos adicionais são valores por unidade, não o total do lote.</div>
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
            <Row label="Minha margem (%)"><Input inputMode="decimal" value={form.margin_pct} onChange={e => upd("margin_pct", e.target.value)} className={inCls} data-testid="price-margin-input" /></Row>
            <Row label="Moeda de venda">
              <div className="flex gap-1 p-1 rounded-full border border-[#0F382C]/15 bg-white">
                {["BRL", "USD"].map(c => <button key={c} onClick={() => upd("currency", c)} data-testid={`price-currency-${c}`} className={`px-3 py-0.5 text-xs font-semibold rounded-full ${form.currency === c ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70"}`}>{c}</button>)}
              </div>
            </Row>
            <Row label="Câmbio (BRL por 1 USD)"><Input inputMode="decimal" value={form.exchange_rate} onChange={e => upd("exchange_rate", e.target.value)} className={inCls} data-testid="price-exchange-input" /></Row>
          </div>
        </section>
      </div>

      <aside className="rounded-2xl bg-[#0F382C] text-white p-5 self-start sticky top-24" data-testid="price-result">
        {r.error ? <p role="alert" data-testid="price-calculation-error">{r.error}</p> : <>
        <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-300">Preço de venda sugerido por unidade</div>
        <div className="font-display text-3xl font-extrabold mt-1" data-testid="price-result-main">{priceMoney(form.currency === "USD" ? r.priceUsd : r.price,form.currency,true)}<span className="text-base font-normal text-white/60"> / {form.unit}</span></div>
        <div className="text-sm text-white/70 mt-1" data-testid="price-result-secondary">{form.currency === "USD" ? priceMoney(r.price,"BRL",true) : r.rate>0 ? priceMoney(r.priceUsd,"USD",true) : "Câmbio não informado"}</div>
        <div className="mt-5 space-y-2 text-sm">
          {[[`Fornecedor / ${form.unit}`, priceMoney(r.supplier,"BRL",true)], ["Custos adicionais / unidade", priceMoney(r.extras,"BRL",true)], ["Custo total / unidade", priceMoney(r.cost,"BRL",true), true],
            [`Impostos (${r.taxes.toFixed(2)}%) / unidade`, priceMoney(r.taxValue,"BRL",true)], ["Lucro por " + form.unit, priceMoney(r.profit,"BRL",true), true],
            ["Margem real", `${r.marginReal.toFixed(1)}%`], ["Markup real", `${r.markupReal.toFixed(1)}%`]].map(([l, v, b]) => (
            <div key={l} className={`flex justify-between gap-2 ${b ? "font-semibold border-t border-white/10 pt-2" : "text-white/80"}`}><span>{l}</span><span className="font-mono-alt whitespace-nowrap">{v}</span></div>
          ))}
        </div>
        <div className="mt-5 border-t border-white/20 pt-4 space-y-2" data-testid="price-operation-totals">
          <h3 className="font-semibold">Totais para {r.quantity.toLocaleString("pt-BR",{maximumFractionDigits:6})} {form.unit}</h3>
          <div className="flex justify-between gap-2"><span>Aquisição do fornecedor</span><strong data-testid="price-supplier-total">{priceMoney(r.supplierTotal)}</strong></div>
          <div className="flex justify-between gap-2"><span>Custos adicionais</span><span>{priceMoney(r.extrasTotal)}</span></div>
          <div className="flex justify-between gap-2"><span>Custo total da operação</span><strong data-testid="price-cost-total">{priceMoney(r.costTotal)}</strong></div>
          <div className="flex justify-between gap-2 text-amber-300"><span>Venda total sugerida</span><strong data-testid="price-sale-total">{priceMoney(form.currency === "USD" ? r.saleTotalUsd : r.saleTotal,form.currency)}</strong></div>
          <div className="flex justify-between gap-2"><span>Impostos totais (BRL)</span><span>{priceMoney(r.taxTotal)}</span></div>
          <div className="flex justify-between gap-2"><span>Lucro total (BRL)</span><strong data-testid="price-profit-total">{priceMoney(r.profitTotal)}</strong></div>
        </div>
        </>}
      </aside>
    </div>
  );
};
