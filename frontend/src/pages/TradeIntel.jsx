import { useEffect, useState } from "react";
import { api, flag, fmtUSD, INDUSTRIES } from "@/lib/api";
import { useLang } from "@/i18n";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Globe2, Users } from "lucide-react";
import { toast } from "sonner";

const TradeIntel = () => {
  const { t } = useLang();
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("all");
  const [industry, setIndustry] = useState("all");
  const [countries, setCountries] = useState([]);
  const [comexSearch, setComexSearch] = useState("");
  const [ncmOptions, setNcmOptions] = useState([]);
  const [selectedNcm, setSelectedNcm] = useState("");
  const [comexFrom, setComexFrom] = useState("2026-01");
  const [comexTo, setComexTo] = useState("2026-08");
  const [comexFlow, setComexFlow] = useState("export");
  const [comexRows, setComexRows] = useState([]);
  const [prospectSummary, setProspectSummary] = useState(null);
  const [comexLoading, setComexLoading] = useState(false);
  const [marketRows, setMarketRows] = useState([]);
  const [marketTotals, setMarketTotals] = useState({ volume_kg: 0, fob_usd: 0 });
  const [buyerResults, setBuyerResults] = useState([]);
  const [buyerCountry, setBuyerCountry] = useState("");
  const [buyerProduct, setBuyerProduct] = useState("");
  const [buyerLoading, setBuyerLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState({});

  const load = () => {
    const params = {};
    if (search) params.search = search;
    if (country !== "all") params.country = country;
    if (industry !== "all") params.industry = industry;
    api.get("/trade-data", { params }).then(r => {
      setRecords(r.data);
      if (countries.length === 0 && r.data.length > 0) {
        const uniq = [...new Set(r.data.map(x => `${x.country_code}|${x.importer_country}`))];
        setCountries(uniq);
      }
    }).catch(() => {});
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [country, industry]);

  useEffect(() => {
    api.get("/trade-data").then(r => {
      const uniq = [...new Set(r.data.map(x => `${x.country_code}|${x.importer_country}`))];
      setCountries(uniq);
    }).catch(() => {});
  }, []);

  const searchNcm = async () => {
    if (!comexSearch.trim()) return;
    try {
      const r = await api.get("/comexstat/ncm", { params: { search: comexSearch, per_page: 30 } });
      const raw = r.data?.data || r.data?.items || r.data?.results || r.data || [];
      const list = Array.isArray(raw) ? raw : [];
      setNcmOptions(list);
      if (list.length === 1) {
        const x = list[0];
        setSelectedNcm(String(x.coNcm ?? x.co_ncm ?? x.code ?? x.codigo ?? ""));
      }
    } catch (e) {
      toast.error("Não foi possível consultar os NCMs no Comex Stat.");
    }
  };

  const queryComex = async () => {
    setComexLoading(true);
    try {
      const r = await api.post("/comexstat/prospect", {
        flow: comexFlow,
        period: { from: comexFrom, to: comexTo },
        ncm: selectedNcm
      });
      const raw = r.data?.data?.list || r.data?.data?.data || r.data?.data || r.data?.items || r.data?.results || r.data || [];
      setComexRows(Array.isArray(raw) ? raw : []);
      const markets = r.data?.markets?.rows || [];
      if (markets.length) {
        setMarketRows(markets);
        setMarketTotals(r.data?.markets?.totals || { volume_kg: 0, fob_usd: 0 });
      } else {
        const rows = Array.isArray(raw) ? raw : [];
        const get = (obj, keys) => keys.map(k => obj?.[k]).find(v => v !== undefined && v !== null && v !== "");
        const grouped = {};
        rows.forEach(row => {
          const country = get(row, ["country", "noPais", "countryName", "pais", "coPais"]);
          const kg = Number(get(row, ["metricKG", "kg", "kgLiquido", "kg_liquido", "netWeight", "quantity"]) || 0);
          const fob = Number(get(row, ["metricFOB", "fob", "vlFob", "vl_fob", "valueFOB", "value"]) || 0);
          if (!country) return;
          if (!grouped[country]) grouped[country] = { country: String(country), volume_kg: 0, fob_usd: 0 };
          grouped[country].volume_kg += Number.isFinite(kg) ? kg : 0;
          grouped[country].fob_usd += Number.isFinite(fob) ? fob : 0;
        });
        const values = Object.values(grouped);
        const totalFob = values.reduce((a, x) => a + x.fob_usd, 0);
        values.forEach(x => {
          x.share_pct = totalFob ? (x.fob_usd * 100 / totalFob) : 0;
          x.avg_usd_kg = x.volume_kg ? x.fob_usd / x.volume_kg : 0;
        });
        values.sort((a, b) => b.fob_usd - a.fob_usd);
        setMarketRows(values);
        setMarketTotals({ volume_kg: values.reduce((a, x) => a + x.volume_kg, 0), fob_usd: totalFob });
      }
      setProspectSummary(r.data);
    } catch (e) {
      toast.error("Comex Stat não respondeu. Verifique o período e o NCM.");
      setComexRows([]);
    } finally {
      setComexLoading(false);
    }
  };

  const discoverBuyers = async (market) => {
    const opt = ncmOptions.find(x => String(x.coNcm ?? x.co_ncm ?? x.code ?? x.codigo ?? "") === String(selectedNcm));
    const product = selectedNcm ? (opt?.noNcm || opt?.no_ncm || opt?.description || selectedNcm) : (comexSearch || "Brazilian tropical ingredients");
    const countryName = market.country || "";
    setBuyerCountry(countryName); setBuyerProduct(product); setBuyerLoading(true);
    try {
      const r = await api.post("/buyer-discovery/search", { product, country: countryName, limit: 10 });
      setBuyerResults(r.data?.results || []);
      if (!(r.data?.results || []).length) toast.info("Nenhuma empresa encontrada nesta pesquisa.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Não foi possível pesquisar compradores.");
      setBuyerResults([]);
    } finally { setBuyerLoading(false); }
  };

  const findDecisionMaker = async (buyer) => {
    setDecisionLoading(prev => ({...prev, [buyer.company]: true}));
    try {
      const r = await api.post("/buyer-discovery/" + encodeURIComponent(buyer.company) + "/decision-maker", null, { params: { product: buyerProduct, country: buyerCountry } });
      setBuyerResults(prev => prev.map(x => x.company === buyer.company ? {...x, ...r.data} : x));
      toast.success("Pesquisa de decisor concluída.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Não foi possível pesquisar o decisor."); }
    finally { setDecisionLoading(prev => ({...prev, [buyer.company]: false})); }
  };

  const addBuyerToCrm = async (buyer) => {
    try {
      await api.post("/buyer-discovery/to-crm", {...buyer, country: buyerCountry, product_interest: buyerProduct});
      toast.success(buyer.company + " enviado para o CRM.");
    } catch (e) { toast.error(e?.response?.data?.detail || "Não foi possível enviar para o CRM."); }
  };

  const addToCrm = async (id) => {
    await api.post(`/trade-data/${id}/add-to-crm`);
    toast.success(t("added_to_crm"));
  };

  return (
    <div className="space-y-6" data-testid="trade-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2 flex items-center gap-1">
          <Globe2 className="w-3 h-3" /> 04 · Trade Intelligence
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{t("trade_title")}</h1>
        <p className="text-base text-[#0F382C]/70 mt-1">{t("trade_subtitle")}</p>
      </div>



      <div className="rounded-xl border border-[#0F382C]/10 bg-white/95 p-5 space-y-4" data-testid="comexstat-panel">
        <div>
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60">COMEX STAT · MDIC</div>
          <h2 className="font-display text-xl font-bold text-[#0F382C]">Inteligência oficial de comércio exterior</h2>
          <p className="text-sm text-[#0F382C]/60 mt-1">Consulte NCM, destino/mercado e valores oficiais. O Comex Stat não divulga o nome das empresas importadoras.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <div className="md:col-span-2 flex gap-2">
            <Input value={comexSearch} onChange={e => setComexSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && searchNcm()} placeholder="Buscar NCM / descrição" className="bg-white" />
            <Button onClick={searchNcm} variant="outline">Buscar NCM</Button>
          </div>
          <Select value={selectedNcm || "none"} onValueChange={v => setSelectedNcm(v === "none" ? "" : v)}>
            <SelectTrigger className="bg-white"><SelectValue placeholder="NCM" /></SelectTrigger>
            <SelectContent className="bg-white max-h-72">
              <SelectItem value="none">Todos os NCMs</SelectItem>
              {ncmOptions.map((x, i) => {
                const code = String(x.coNcm ?? x.co_ncm ?? x.code ?? x.codigo ?? "");
                const label = x.noNcm ?? x.no_ncm ?? x.description ?? x.nome ?? code;
                return <SelectItem key={code || i} value={code}>{code} — {label}</SelectItem>;
              })}
            </SelectContent>
          </Select>
          <Select value={comexFlow} onValueChange={setComexFlow}>
            <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="export">Exportação</SelectItem>
              <SelectItem value="import">Importação</SelectItem>
            </SelectContent>
          </Select>
          <Input type="month" value={comexFrom} onChange={e => setComexFrom(e.target.value)} className="bg-white" />
          <Input type="month" value={comexTo} onChange={e => setComexTo(e.target.value)} className="bg-white" />
          <Button onClick={queryComex} disabled={comexLoading} className="bg-[#0F382C] hover:bg-[#0A2920] text-white">
            {comexLoading ? "Consultando..." : "Consultar Comex Stat"}
          </Button>
        </div>

        {prospectSummary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="rounded-lg border p-3 bg-[#F9F6F0]">
              <div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">NCM</div>
              <div className="font-semibold text-[#0F382C]">{prospectSummary.ncm || "Todos"}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#F9F6F0]">
              <div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">Período</div>
              <div className="font-semibold text-[#0F382C]">{prospectSummary.period?.from} → {prospectSummary.period?.to}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#F9F6F0]">
              <div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">Fluxo</div>
              <div className="font-semibold text-[#0F382C]">{prospectSummary.flow === "import" ? "Importação" : "Exportação"}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#F9F6F0]">
              <div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">Fonte</div>
              <div className="font-semibold text-[#0F382C]">Comex Stat / MDIC</div>
            </div>
          </div>
        )}

        {marketRows.length > 0 && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg border p-3 bg-[#F9F6F0]"><div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">Mercados</div><div className="font-semibold text-[#0F382C]">{marketRows.length}</div></div>
              <div className="rounded-lg border p-3 bg-[#F9F6F0]"><div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">Volume</div><div className="font-semibold text-[#0F382C]">{marketTotals.volume_kg.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} kg</div></div>
              <div className="rounded-lg border p-3 bg-[#F9F6F0]"><div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">FOB</div><div className="font-semibold text-[#0F382C]">USD {marketTotals.fob_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</div></div>
            </div>
            <div className="overflow-x-auto rounded-lg border border-[#0F382C]/10">
              <Table><TableHeader><TableRow className="bg-[#0F382C] hover:bg-[#0F382C]">
                <TableHead className="text-amber-300 text-[10px] uppercase">Mercado / País</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">Volume kg</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">FOB USD</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">USD/kg</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">% FOB</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">Ação</TableHead>
              </TableRow></TableHeader>
              <TableBody>{marketRows.slice(0, 50).map((m, i) => (
                <TableRow key={i}>
                  <TableCell className="font-semibold text-[#0F382C]">{m.country}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">{Number(m.volume_kg || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">USD {Number(m.fob_usd || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">USD {Number(m.avg_usd_kg || 0).toFixed(2)}</TableCell>
                  <TableCell className="text-right text-xs">{Number(m.share_pct || 0).toFixed(2)}%</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" onClick={() => discoverBuyers(m)}><Users className="w-3 h-3 mr-1" />{buyerLoading ? "Pesquisando..." : "Buscar compradores"}</Button></TableCell>
                </TableRow>
              ))}</TableBody></Table>
            </div>
          </div>
        )}

        {buyerResults.length > 0 && (
          <div className="rounded-lg border border-[#0F382C]/10 bg-[#F9F6F0] p-4 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div><div className="text-[10px] uppercase tracking-widest text-[#0F382C]/50">BUSCA WEB · COMPRADORES</div><div className="font-display text-lg font-bold text-[#0F382C]">{buyerCountry}</div><div className="text-xs text-[#0F382C]/60">{buyerProduct}</div></div>
              <Badge variant="outline">{buyerResults.length} empresas</Badge>
            </div>
            <div className="space-y-2">{buyerResults.map((b) => (
              <div key={b.domain || b.company} className="rounded-lg border bg-white p-3">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-[#0F382C]">{b.company}</div>
                    <div className="text-xs text-[#0F382C]/60">{b.domain || b.website} · Score {b.priority_score}</div>
                    {b.decision_maker && <div className="text-xs mt-1">Decisor: <b>{b.decision_maker}</b>{b.decision_maker_title ? " · " + b.decision_maker_title : ""}</div>}
                    {b.linkedin && <a className="text-xs underline text-[#0F382C]" href={b.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button size="sm" variant="outline" onClick={() => findDecisionMaker(b)} disabled={decisionLoading[b.company]}>{decisionLoading[b.company] ? "Pesquisando..." : "Buscar decisor"}</Button>
                    <Button size="sm" onClick={() => addBuyerToCrm(b)} className="bg-[#0F382C] hover:bg-[#0A2920] text-white">Adicionar ao CRM</Button>
                  </div>
                </div>
                {b.source_url && <div className="text-[10px] mt-2 text-[#0F382C]/50 truncate">Fonte: {b.source_url}</div>}
              </div>
            ))}</div>
          </div>
        )}

        {comexRows.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-[#0F382C]/10">
            <Table>
              <TableHeader>
                <TableRow className="bg-[#0F382C] hover:bg-[#0F382C]">
                  {Object.keys(comexRows[0]).slice(0, 8).map(k => <TableHead key={k} className="text-amber-300 text-[10px] uppercase">{k}</TableHead>)}
                </TableRow>
              </TableHeader>
              <TableBody>
                {comexRows.slice(0, 100).map((row, i) => (
                  <TableRow key={i}>
                    {Object.keys(comexRows[0]).slice(0, 8).map(k => <TableCell key={k} className="text-xs">{typeof row[k] === "number" ? row[k].toLocaleString("pt-BR") : String(row[k] ?? "")}</TableCell>)}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="relative col-span-2">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#0F382C]/40" />
          <Input
            placeholder={t("search_placeholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            className="pl-9 bg-white"
            data-testid="trade-search-input"
          />
        </div>
        <Select value={country} onValueChange={setCountry}>
          <SelectTrigger className="bg-white" data-testid="trade-country-filter"><SelectValue placeholder={t("country")} /></SelectTrigger>
          <SelectContent className="bg-white max-h-72">
            <SelectItem value="all">{t("all_countries")}</SelectItem>
            {countries.map(c => {
              const [code, name] = c.split("|");
              return <SelectItem key={code} value={code}>{flag(code)} {name}</SelectItem>;
            })}
          </SelectContent>
        </Select>
        <Select value={industry} onValueChange={setIndustry}>
          <SelectTrigger className="bg-white" data-testid="trade-industry-filter"><SelectValue placeholder={t("industry")} /></SelectTrigger>
          <SelectContent className="bg-white">
            <SelectItem value="all">{t("all_industries")}</SelectItem>
            {INDUSTRIES.map(i => <SelectItem key={i} value={i}>{t(`industry_${i}`)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/50">
        {records.length} {t("records_short")}
      </div>

      <div className="rounded-xl overflow-hidden border border-[#0F382C]/10 bg-white/95" data-testid="trade-table-wrap">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-[#0F382C] hover:bg-[#0F382C]">
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest">{t("company")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest">{t("country")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest">HS / {t("product")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest text-right">{t("volume")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest text-right">{t("value_usd")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest">{t("last_shipment")}</TableHead>
                <TableHead className="text-amber-300 font-mono-alt text-[11px] uppercase tracking-widest text-right">{t("action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-center py-10 text-[#0F382C]/50 italic">{t("no_results")}</TableCell></TableRow>
              )}
              {records.map(r => (
                <TableRow key={r.id} data-testid={`trade-row-${r.id}`} className="hover:bg-[#F9F6F0]">
                  <TableCell>
                    <div className="font-semibold text-[#0F382C]">{r.importer_company}</div>
                    <div className="text-[10px] text-[#0F382C]/50 font-mono-alt">{r.contact_hint}</div>
                  </TableCell>
                  <TableCell className="text-sm"><span className="mr-1">{flag(r.country_code)}</span>{r.importer_country}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px] mr-2 border-amber-600/40 text-amber-800 bg-amber-50">{r.hs_code}</Badge>
                    <span className="text-sm text-[#0F382C]/80">{r.product_description}</span>
                  </TableCell>
                  <TableCell className="text-right font-mono-alt text-sm">{r.volume_kg.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono-alt text-sm text-amber-700 font-semibold">{fmtUSD(r.value_usd)}</TableCell>
                  <TableCell className="text-sm text-[#0F382C]/70">{r.last_shipment_date}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      onClick={() => addToCrm(r.id)}
                      data-testid={`add-crm-${r.id}`}
                      className="bg-[#0F382C] hover:bg-[#0A2920] text-white text-xs"
                    ><Plus className="w-3 h-3 mr-1" />{t("add_to_crm")}</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
};

export default TradeIntel;
