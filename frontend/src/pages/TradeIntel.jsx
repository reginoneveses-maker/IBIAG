import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, flag, fmtUSD, INDUSTRIES, externalUrl } from "@/lib/api";
import { useLang } from "@/i18n";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Globe2, Users } from "lucide-react";
import { toast } from "sonner";
import { Link, useSearchParams } from "react-router-dom";

const previousMonth = new Date(new Date().getFullYear(), new Date().getMonth()-1, 1);
const initialEnd = `${previousMonth.getFullYear()}-${String(previousMonth.getMonth()+1).padStart(2,"0")}`;
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
  const [comexFrom, setComexFrom] = useState(`${previousMonth.getFullYear()}-01`);
  const [comexTo, setComexTo] = useState(initialEnd);
  const [comexFlow, setComexFlow] = useState("export");
  const [comexRows, setComexRows] = useState([]);
  const [prospectSummary, setProspectSummary] = useState(null);
  const [comexLoading, setComexLoading] = useState(false);
  const [marketRows, setMarketRows] = useState([]);
  const [marketTotals, setMarketTotals] = useState({ volume_kg: 0, fob_usd: 0 });
  const [buyerResults, setBuyerResults] = useState([]);
  const [buyerCountry, setBuyerCountry] = useState("");
  const [buyerProduct, setBuyerProduct] = useState("");
  const [directCountry, setDirectCountry] = useState("");
  const [directProduct, setDirectProduct] = useState("");
  const [buyerLoading, setBuyerLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState({});
  const [crmLoading, setCrmLoading] = useState({});
  const [crmLinks, setCrmLinks] = useState({});
  const [params, setParams] = useSearchParams();
  const jobId = params.get("buyer_job") || "";
  const [buyerJob, setBuyerJob] = useState(null);
  const [directRegion, setDirectRegion] = useState("");
  const [marketCatalog, setMarketCatalog] = useState({countries: [], regions: []});
  const [resultCountry, setResultCountry] = useState("");
  const [pollRetry, setPollRetry] = useState(0);
  const [pollError, setPollError] = useState("");
  const changeJob = id => setParams(prev => { const next = new URLSearchParams(prev); id ? next.set("buyer_job", id) : next.delete("buyer_job"); return next; });
  const buyerRequest = useRef(0);
  const buyerAbort = useRef(null);
  const pollAbort = useRef(null);
  const resetBuyerSearch = (clearFields = false) => {
    const previousJob = buyerJob?.id || jobId;
    buyerRequest.current += 1;
    buyerAbort.current?.abort(); pollAbort.current?.abort();
    changeJob(""); setBuyerJob(null); setBuyerResults([]); setBuyerLoading(false);
    setBuyerCountry(""); setBuyerProduct(""); setResultCountry(""); setPollError("");
    setDecisionLoading({}); setCrmLoading({}); setCrmLinks({});
    if (clearFields) { setDirectProduct(""); setDirectCountry(""); setDirectRegion(""); }
    if (previousJob && (!buyerJob || ["pending", "running"].includes(buyerJob.status))) {
      api.post(`/buyer-discovery/search-jobs/${encodeURIComponent(previousJob)}/cancel`).catch(() => toast.error("Os resultados foram limpos, mas não foi possível interromper a pesquisa anterior no servidor."));
    }
  };
  const editBuyerSearch = () => {
    if (buyerLoading || buyerResults.length || buyerJob || jobId || pollError) resetBuyerSearch();
  };
  const tradeRequest = useRef(0);
  useEffect(() => { api.get("/buyer-discovery/markets").then(r => setMarketCatalog({countries: r.data?.countries || [], regions: r.data?.regions || []})).catch(() => {}); }, []);
  useEffect(() => {
    if (!jobId) return;
    let active = true, timer, errors = 0;
    const request = ++buyerRequest.current;
    const controller = new AbortController(); pollAbort.current = controller;
    setBuyerLoading(true); setPollError("");
    const poll = async () => {
      try {
        const r = await api.get(`/buyer-discovery/search-jobs/${encodeURIComponent(jobId)}`, {signal: controller.signal});
        if (!active || request !== buyerRequest.current) return;
        const job = r.data; errors = 0;
        setBuyerJob(job); setBuyerCountry(job.label); setBuyerProduct(job.product);
        setBuyerResults(prev => (job.results || []).map(row => {
          const previous = prev.find(old => buyerKey(old) === buyerKey(row));
          const local = Object.fromEntries(Object.entries(previous || {}).filter(([key]) => key.startsWith("decision_") || ["linkedin","evidence_urls","contact_candidates","validation_status"].includes(key)));
          return {...row, ...local};
        }));
        const running = ["pending", "running"].includes(job.status);
        setBuyerLoading(running);
        if (running) timer = setTimeout(poll, 2000);
      } catch (e) {
        if (!active || request !== buyerRequest.current) return;
        if (++errors < 3) timer = setTimeout(poll, 3000);
        else { setPollError(e?.response?.data?.detail || "Não foi possível atualizar o progresso."); setBuyerLoading(false); }
      }
    };
    poll();
    return () => { active = false; clearTimeout(timer); controller.abort(); };
    // A job keeps its own product and markets when the page is reloaded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, pollRetry]);
  const displayBuyerResults = useMemo(() => {
    const unique = new Map();
    buyerResults.forEach(row => {
      const key = `${row.company}|${row.domain || row.website}`;
      const market = row.search_country || row.country;
      const previous = unique.get(key);
      if (previous) previous.search_countries = [...new Set([...previous.search_countries, market].filter(Boolean))];
      else unique.set(key, {...row, search_countries: [market].filter(Boolean)});
    });
    return [...unique.values()];
  }, [buyerResults]);
  const buyerKey = b => `${b.company}|${b.country}|${b.website}`;
  useEffect(() => () => { buyerRequest.current += 1; tradeRequest.current += 1; buyerAbort.current?.abort(); pollAbort.current?.abort(); }, []);

  const load = useCallback(() => {
    const params = {};
    if (search) params.search = search;
    if (country !== "all") params.country = country;
    if (industry !== "all") params.industry = industry;
    const request = ++tradeRequest.current;
    api.get("/trade-data", { params }).then(r => {
      if (request !== tradeRequest.current) return;
      setRecords(r.data);
      if (countries.length === 0 && r.data.length > 0) {
        const uniq = [...new Set(r.data.map(x => `${x.country_code}|${x.importer_country}`))];
        setCountries(uniq);
      }
    }).catch(() => { if (request === tradeRequest.current) { setRecords([]); toast.error("Não foi possível carregar os registros comerciais."); } });
  }, [search, country, industry, countries.length]);

  useEffect(() => { load(); }, [load]);

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
    setComexRows([]); setMarketRows([]); setProspectSummary(null);
    setMarketTotals({volume_kg: 0, fob_usd: 0});
    resetBuyerSearch();
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

  const searchBuyers = async (product, countryName) => {
    if (!product.trim() || !countryName.trim()) return toast.error("Informe o produto e o país.");
    resetBuyerSearch();
    const request = ++buyerRequest.current;
    const controller = new AbortController(); buyerAbort.current = controller;
    setBuyerCountry(countryName); setBuyerProduct(product); setBuyerLoading(true);
    try {
      const r = await api.post("/buyer-discovery/search", { product, country: countryName, limit: 10 }, {signal: controller.signal, timeout: 360000});
      if (request !== buyerRequest.current) return;
      const results = (r.data?.results || []).map(b => ({...b, search_country: b.search_country || countryName, product_interest: product}));
      setBuyerResults(results);
      if (r.data?.warnings?.length) toast.info(r.data.warnings.join(" "));
      if (!results.length) toast.info("Nenhuma empresa com venda ou uso do ingrediente comprovado nas páginas consultadas.");
    } catch (e) {
      if (request === buyerRequest.current) toast.error(e?.response?.data?.detail || "Não foi possível pesquisar compradores.");
    } finally { if (request === buyerRequest.current) setBuyerLoading(false); }
  };
  const directDiscoverBuyers = async () => {
    if (buyerLoading) return;
    const product = directProduct.trim(), entered = directCountry.trim();
    const region = directRegion || ({europa: "europe", europe: "europe", asia: "asia", "ásia": "asia"}[entered.toLowerCase()] || "");
    const selected = entered.split(/[,;\n]+/).map(x => x.trim()).filter(Boolean);
    if (!region && selected.length <= 1) return searchBuyers(product, entered);
    if (!product) return toast.error("Informe o produto.");
    resetBuyerSearch();
    const request = ++buyerRequest.current;
    setBuyerLoading(true);
    try {
      const r = await api.post("/buyer-discovery/search-jobs", {product, countries: region ? [] : selected, region, limit: 10, replace_previous: true});
      if (request !== buyerRequest.current) {
        if (r.data?.id) api.post(`/buyer-discovery/search-jobs/${encodeURIComponent(r.data.id)}/cancel`).catch(() => {});
        return;
      }
      setBuyerJob(r.data); changeJob(r.data.id);
    } catch (e) {
      if (request === buyerRequest.current) { setBuyerLoading(false); toast.error(e?.response?.data?.detail || "Não foi possível iniciar a pesquisa."); }
    }
  };
  const discoverBuyers = (market) => {
    const opt = ncmOptions.find(x => String(x.coNcm ?? x.co_ncm ?? x.code ?? x.codigo ?? "") === String(selectedNcm));
    const product = selectedNcm ? (opt?.noNcm || opt?.no_ncm || opt?.description || selectedNcm) : (comexSearch || "Brazilian tropical ingredients");
    return searchBuyers(product, market.country || "");
  };

  const findDecisionMaker = async (buyer) => {
    const key = buyerKey(buyer), request = buyerRequest.current;
    setDecisionLoading(prev => ({...prev, [key]: true}));
    try {
      const r = await api.post("/buyer-discovery/" + encodeURIComponent(buyer.company) + "/decision-maker", null, {params: {product: buyer.product_interest, country: buyer.country}});
      if (request !== buyerRequest.current) return;
      const {source_url, source, ...decision} = r.data;
      setBuyerResults(prev => prev.map(x => buyerKey(x) === key ? {...x, ...decision, decision_source_url: decision.decision_source_url || source_url || ""} : x));
      if (decision.validation_status === "not_found") toast.info("Nenhum decisor encontrado.");
      else toast.info("Contatos encontrados; confira as fontes antes de abordar.");
    } catch (e) { if (request === buyerRequest.current) toast.error(e?.response?.data?.detail || "Não foi possível pesquisar o decisor."); }
    finally { if (request === buyerRequest.current) setDecisionLoading(prev => ({...prev, [key]: false})); }
  };
  const addBuyerToCrm = async (buyer) => {
    const key = buyerKey(buyer), request = buyerRequest.current;
    setCrmLoading(prev => ({...prev, [key]: true}));
    try {
      const r = await api.post("/buyer-discovery/to-crm", buyer, {timeout:90000});
      if (request === buyerRequest.current) {
        setCrmLinks(prev => ({...prev, [key]: r.data.id}));
        toast.success(r.data.company + " disponível no CRM.");
        if(r.data.enrichment_message)toast.info(r.data.enrichment_message);
      }
    } catch (e) { if (request === buyerRequest.current) toast.error(e?.response?.data?.detail || "Não foi possível enviar para o CRM."); }
    finally { if (request === buyerRequest.current) setCrmLoading(prev => ({...prev, [key]: false})); }
  };
  const addToCrm = async (id) => {
    setCrmLoading(prev => ({...prev, [id]: true}));
    try {
      const r = await api.post(`/trade-data/${id}/add-to-crm`);
      setCrmLinks(prev => ({...prev, [id]: r.data.id}));
      toast.success(t("added_to_crm"));
    } catch (e) { toast.error(e?.response?.data?.detail || "Não foi possível adicionar ao CRM."); }
    finally { setCrmLoading(prev => ({...prev, [id]: false})); }
  };

  return (
    <div className="space-y-6" data-testid="trade-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#104496]/60 mb-2 flex items-center gap-1">
          <Globe2 className="w-3 h-3" /> 04 · Trade Intelligence
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#104496]">{t("trade_title")}</h1>
        <p className="text-base text-[#104496]/70 mt-1">{t("trade_subtitle")}</p>
      </div>



      <div className="rounded-xl border border-[#104496]/10 bg-white/95 p-5 space-y-4" data-testid="direct-buyer-search">
        <div>
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#104496]/60">PROSPECÇÃO WEB</div>
          <h2 className="font-display text-xl font-bold text-[#104496]">Buscar empresas por produto e mercados</h2>
          <p className="text-sm text-[#104496]/60 mt-1">Pesquisa direta em fontes web atuais. Não exige NCM nem consulta prévia ao Comex Stat. Escolha Europa ou Ásia, ou informe vários países separados por vírgula.</p>
          <p className="text-sm text-[#104496]/80 mt-2">Empresas que vendem o ingrediente ou o utilizam em seus próprios produtos. Cada resultado mostra a evidência publicada no site. Livros, pesquisas, artigos genéricos e diretórios são excluídos.</p>
        </div>
        <label className="text-sm block">Região da pesquisa
          <select aria-label="Região da pesquisa" value={directRegion} onChange={e => { editBuyerSearch(); setDirectRegion(e.target.value); setDirectCountry(""); }} className="block border rounded p-2 bg-white mt-1">
            <option value="">Escolher países</option><option value="europe">Europa</option><option value="asia">Ásia</option>
          </select>
        </label>
        {directRegion && <p className="text-sm">{marketCatalog.regions.find(r => r.id === directRegion)?.countries?.length || (directRegion === "europe" ? 51 : 50)} países e territórios. A pesquisa será feita por país e pode levar alguns minutos.</p>}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <Input value={directProduct} onChange={e => { editBuyerSearch(); setDirectProduct(e.target.value); }} onKeyDown={e => e.key === "Enter" && directDiscoverBuyers()} placeholder="Produto, ex.: Acerola Powder" className="bg-white md:col-span-2" />
          <Input value={directCountry} onChange={e => { editBuyerSearch(); setDirectCountry(e.target.value); }} onKeyDown={e => e.key === "Enter" && directDiscoverBuyers()} placeholder="Países, ex.: Alemanha, Espanha, Portugal" disabled={!!directRegion} list="buyer-markets" className="bg-white md:col-span-2" />
          <Button onClick={directDiscoverBuyers} disabled={buyerLoading || !directProduct.trim() || (!directCountry.trim() && !directRegion)} className="bg-[#104496] hover:bg-[#0B3274] text-white">
            <Search className="w-4 h-4 mr-1" />{buyerLoading ? "Pesquisando..." : "Buscar compradores"}
          </Button>
        </div>
        <Button variant="outline" onClick={() => resetBuyerSearch(true)}>Limpar pesquisa</Button>
        <datalist id="buyer-markets">{marketCatalog.countries.map(m => <option key={m.code} value={m.name} />)}</datalist>
        {buyerJob && <div role="status" className="border rounded p-3 space-y-2">
          <p>{buyerJob.label}: {buyerJob.completed}/{buyerJob.total} países finalizados · {({pending:"Na fila",running:"Pesquisando",complete:"Concluída",partial:"Concluída com falhas em alguns países",failed:"Falhou",cancelled:"Interrompida pelo usuário",interrupted:"Interrompida; inicie uma nova pesquisa",outdated:"Pesquisa antiga; refaça a busca"})[buyerJob.status]}</p>
          {buyerJob.failures > 0 && buyerJob.status !== "outdated" && <div role="alert" className="rounded bg-amber-50 p-3 text-amber-900">
            <p>{buyerJob.failures} países com falha ou consulta incompleta. O total de empresas ainda não representa toda a região.</p>
            {buyerJob.service_error && <p>{buyerJob.service_error}</p>}
            {!buyerLoading && <Button variant="outline" onClick={async () => {
              const failed = Object.entries(buyerJob.progress || {}).filter(([,p]) => ["failed","partial","blocked"].includes(p.status)).map(([code]) => code);
              if (!failed.length) return;
              const request = ++buyerRequest.current;
              try {
                setBuyerLoading(true);
                const response = await api.post(`/buyer-discovery/search-jobs/${encodeURIComponent(buyerJob.id)}/retry`);
                if (request !== buyerRequest.current) { api.post(`/buyer-discovery/search-jobs/${encodeURIComponent(response.data.id)}/cancel`).catch(() => {}); return; }
                setBuyerJob(response.data); changeJob(response.data.id); setPollRetry(n => n + 1);
              } catch (e) { if (request === buyerRequest.current) { setBuyerLoading(false); toast.error(e?.response?.data?.detail || "Não foi possível repetir os países com falha."); } }
            }}>Tentar novamente países com falha</Button>}
          </div>}
          {buyerJob.retry_of && <p>Nova tentativa dos países com falha; os resultados anteriores foram preservados.</p>}
          {buyerJob.validation_message && <p>{buyerJob.validation_message}</p>}
          <progress value={buyerJob.completed} max={buyerJob.total} className="w-full" />
          {buyerJob.status === "complete" && !buyerResults.length && <p>Nenhuma empresa com venda ou uso do ingrediente comprovado nas páginas consultadas.</p>}
          {buyerLoading && <Button variant="outline" disabled={buyerJob.cancel_requested} onClick={async () => { try { await api.post(`/buyer-discovery/search-jobs/${encodeURIComponent(jobId)}/cancel`); setBuyerJob(prev => ({...prev,cancel_requested:true})); } catch(e) { toast.error("Não foi possível interromper a pesquisa."); } }}>{buyerJob.cancel_requested ? "Interrupção solicitada" : "Interromper pesquisa"}</Button>}
          <details><summary>Progresso por país</summary>{Object.entries(buyerJob.progress || {}).map(([code,p]) => <p key={code}>{p.country}: {({pending:"Na fila",running:"Pesquisando",complete:`${p.count} empresas`,failed:"Falhou",partial:`${p.count} empresas; conferência incompleta`,blocked:"Não consultado; serviço bloqueado"})[p.status]} {p.error}</p>)}</details>
        </div>}
        {pollError && <p role="alert">{pollError} <Button variant="outline" onClick={() => setPollRetry(x => x+1)}>Atualizar progresso</Button></p>}
        {buyerLoading && <p role="status" className="text-sm">Pesquisando e conferindo os sites das empresas. A verificação pode levar alguns minutos.</p>}
      </div>

      <div className="rounded-xl border border-[#104496]/10 bg-white/95 p-5 space-y-4" data-testid="comexstat-panel">
        <div>
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#104496]/60">COMEX STAT · MDIC</div>
          <h2 className="font-display text-xl font-bold text-[#104496]">Inteligência oficial de comércio exterior</h2>
          <p className="text-sm text-[#104496]/60 mt-1">Consulte NCM, destino/mercado e valores oficiais. O Comex Stat não divulga o nome das empresas importadoras.</p>
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
          <Button onClick={queryComex} disabled={comexLoading} className="bg-[#104496] hover:bg-[#0B3274] text-white">
            {comexLoading ? "Consultando..." : "Consultar Comex Stat"}
          </Button>
        </div>

        {prospectSummary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="rounded-lg border p-3 bg-[#EEF3FB]">
              <div className="text-[10px] uppercase tracking-widest text-[#104496]/50">NCM</div>
              <div className="font-semibold text-[#104496]">{prospectSummary.ncm || "Todos"}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#EEF3FB]">
              <div className="text-[10px] uppercase tracking-widest text-[#104496]/50">Período</div>
              <div className="font-semibold text-[#104496]">{prospectSummary.period?.from} → {prospectSummary.period?.to}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#EEF3FB]">
              <div className="text-[10px] uppercase tracking-widest text-[#104496]/50">Fluxo</div>
              <div className="font-semibold text-[#104496]">{prospectSummary.flow === "import" ? "Importação" : "Exportação"}</div>
            </div>
            <div className="rounded-lg border p-3 bg-[#EEF3FB]">
              <div className="text-[10px] uppercase tracking-widest text-[#104496]/50">Fonte</div>
              <div className="font-semibold text-[#104496]">Comex Stat / MDIC</div>
            </div>
          </div>
        )}

        {marketRows.length > 0 && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="rounded-lg border p-3 bg-[#EEF3FB]"><div className="text-[10px] uppercase tracking-widest text-[#104496]/50">Mercados</div><div className="font-semibold text-[#104496]">{marketRows.length}</div></div>
              <div className="rounded-lg border p-3 bg-[#EEF3FB]"><div className="text-[10px] uppercase tracking-widest text-[#104496]/50">Volume</div><div className="font-semibold text-[#104496]">{marketTotals.volume_kg.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} kg</div></div>
              <div className="rounded-lg border p-3 bg-[#EEF3FB]"><div className="text-[10px] uppercase tracking-widest text-[#104496]/50">FOB</div><div className="font-semibold text-[#104496]">USD {marketTotals.fob_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</div></div>
            </div>
            <div className="overflow-x-auto rounded-lg border border-[#104496]/10">
              <Table><TableHeader><TableRow className="bg-[#104496] hover:bg-[#104496]">
                <TableHead className="text-amber-300 text-[10px] uppercase">Mercado / País</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">Volume kg</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">FOB USD</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">USD/kg</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">% FOB</TableHead>
                <TableHead className="text-amber-300 text-[10px] uppercase text-right">Ação</TableHead>
              </TableRow></TableHeader>
              <TableBody>{marketRows.slice(0, 50).map((m, i) => (
                <TableRow key={i}>
                  <TableCell className="font-semibold text-[#104496]">{m.country}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">{Number(m.volume_kg || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">USD {Number(m.fob_usd || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })}</TableCell>
                  <TableCell className="text-right font-mono-alt text-xs">USD {Number(m.avg_usd_kg || 0).toFixed(2)}</TableCell>
                  <TableCell className="text-right text-xs">{Number(m.share_pct || 0).toFixed(2)}%</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" disabled={buyerLoading || comexLoading} onClick={() => discoverBuyers(m)}><Users className="w-3 h-3 mr-1" />{buyerLoading ? "Pesquisando..." : "Buscar compradores"}</Button></TableCell>
                </TableRow>
              ))}</TableBody></Table>
            </div>
          </div>
        )}

        {buyerResults.length > 0 && (
          <div className="rounded-lg border border-[#104496]/10 bg-[#EEF3FB] p-4 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div><div className="text-[10px] uppercase tracking-widest text-[#104496]/50">BUSCA WEB · EMPRESAS DO INGREDIENTE</div><div className="font-display text-lg font-bold text-[#104496]">{buyerCountry}</div><div className="text-xs text-[#104496]/60">{buyerProduct}</div></div>
              <Badge variant="outline">{displayBuyerResults.length} {displayBuyerResults.length === 1 ? "empresa" : "empresas"}</Badge>
            </div>
            <label className="block text-sm">Filtrar resultados por país <select aria-label="Filtrar resultados por país" value={resultCountry} onChange={e => setResultCountry(e.target.value)} className="border rounded p-2"><option value="">Todos os países</option>{[...new Set(displayBuyerResults.flatMap(b => b.search_countries))].map(c => <option key={c} value={c}>{c}</option>)}</select></label>
            <div className="space-y-2">{displayBuyerResults.filter(b => !resultCountry || b.search_countries.includes(resultCountry)).map((b) => (
              <div key={buyerKey(b)} className="rounded-lg border bg-white p-3">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-[#104496]">{b.company}</div><div className="text-xs">{flag(b.country_code)} Mercados pesquisados: {b.search_countries.join(", ")}</div><div className="text-xs">País da empresa: {b.company_country || "não confirmado"}</div>
                    <div className="flex flex-wrap gap-3 text-xs mt-1">{externalUrl(b.website) && <a href={externalUrl(b.website)} target="_blank" rel="noreferrer" className="underline">{b.is_directory ? "Abrir fonte no diretório" : "Abrir site da empresa"}</a>}{externalUrl(b.source_url) && <a href={externalUrl(b.source_url)} target="_blank" rel="noreferrer" className="underline">Fonte da empresa</a>}</div>
                    <div className="text-xs text-[#104496]/60">{b.domain || b.website} · Score {b.priority_score}</div>{b.is_directory && <div className="text-xs text-amber-800">Fonte em diretório; site oficial da empresa ainda não confirmado.</div>}
                    {b.decision_maker && <div className="text-xs mt-1">Decisor: <b>{b.decision_maker}</b>{b.decision_maker_title ? " · " + b.decision_maker_title : ""}</div>}
                    {externalUrl(b.linkedin) && <a className="text-xs underline text-[#104496]" href={externalUrl(b.linkedin)} target="_blank" rel="noreferrer">LinkedIn</a>}
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    {externalUrl(b.website || b.source_url) && <Button size="sm" variant="outline" asChild><a href={externalUrl(b.website || b.source_url)} target="_blank" rel="noreferrer">{b.is_directory ? "Ver no diretório" : "Ver empresa"}</a></Button>}
                    {externalUrl(b.source_url) && b.source_url !== b.website && <Button size="sm" variant="outline" asChild><a href={externalUrl(b.source_url)} target="_blank" rel="noreferrer">Ver fonte</a></Button>}
                    <Button size="sm" variant="outline" onClick={() => findDecisionMaker(b)} disabled={decisionLoading[buyerKey(b)] || crmLoading[buyerKey(b)]}>{decisionLoading[buyerKey(b)] ? "Pesquisando..." : "Buscar decisor"}</Button>
                    <Button size="sm" disabled={crmLoading[buyerKey(b)] || decisionLoading[buyerKey(b)]} onClick={() => addBuyerToCrm(b)} className="bg-[#104496] hover:bg-[#0B3274] text-white">{crmLoading[buyerKey(b)] ? "Salvando..." : "Adicionar ao CRM"}</Button>
                    {crmLinks[buyerKey(b)] && <Link className="text-sm underline self-center" to={`/prospects/pipeline?lead=${encodeURIComponent(crmLinks[buyerKey(b)])}`}>Ver empresa no CRM</Link>}
                  </div>
                </div>
                {b.relationship_verified && <div className="mt-2 text-sm rounded bg-green-50 p-3 text-[#104496]">
                  <b>{b.product_relationship === "seller" ? "Vende / fornece o ingrediente" : "Utiliza o ingrediente em seus produtos"}</b>
                  <div className="text-xs mt-1">Evidência no site: <q>{b.product_evidence}</q></div>
                </div>}
                {!b.relationship_verified && b.source_description && <div className="text-xs mt-2 text-[#104496]/70">{b.source_description}</div>}
                <div className="text-xs mt-2 space-y-1">
                  {b.decision_maker_email && <div>E-mail: <a className="underline" href={`mailto:${b.decision_maker_email}`}>{b.decision_maker_email}</a></div>}
                  {b.decision_maker_phone && <div>Telefone: {b.decision_maker_phone}</div>}
                  <div>{b.validation_status === "not_found" ? "Decisor não encontrado" : "Candidato à prospecção · requer validação"}</div>
                  {externalUrl(b.decision_source_url) && <a className="underline" href={externalUrl(b.decision_source_url)} target="_blank" rel="noreferrer">Fonte do decisor</a>}
                </div>
              </div>
            ))}</div>
          </div>
        )}

        {comexRows.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-[#104496]/10">
            <Table>
              <TableHeader>
                <TableRow className="bg-[#104496] hover:bg-[#104496]">
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
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#104496]/40" />
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

      <div className="text-xs font-mono-alt uppercase tracking-widest text-[#104496]/50">
        {records.length} {t("records_short")}
      </div>

      <div className="rounded-xl overflow-hidden border border-[#104496]/10 bg-white/95" data-testid="trade-table-wrap">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-[#104496] hover:bg-[#104496]">
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
                <TableRow><TableCell colSpan={7} className="text-center py-10 text-[#104496]/50 italic">{t("no_results")}</TableCell></TableRow>
              )}
              {records.map(r => (
                <TableRow key={r.id} data-testid={`trade-row-${r.id}`} className="hover:bg-[#EEF3FB]">
                  <TableCell>
                    <div className="font-semibold text-[#104496]">{r.importer_company}</div>
                    <div className="text-[10px] text-[#104496]/50 font-mono-alt">{r.contact_hint}</div>
                  </TableCell>
                  <TableCell className="text-sm"><span className="mr-1">{flag(r.country_code)}</span>{r.importer_country}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px] mr-2 border-amber-600/40 text-[#104496] bg-[#F4F7D8]">{r.hs_code}</Badge>
                    <span className="text-sm text-[#104496]/80">{r.product_description}</span>
                  </TableCell>
                  <TableCell className="text-right font-mono-alt text-sm">{r.volume_kg.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono-alt text-sm text-[#104496] font-semibold">{fmtUSD(r.value_usd)}</TableCell>
                  <TableCell className="text-sm text-[#104496]/70">{r.last_shipment_date}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      disabled={crmLoading[r.id]} onClick={() => addToCrm(r.id)}
                      data-testid={`add-crm-${r.id}`}
                      className="bg-[#104496] hover:bg-[#0B3274] text-white text-xs"
                    ><Plus className="w-3 h-3 mr-1" />{t("add_to_crm")}</Button>
                    {crmLinks[r.id] && <Link className="block text-xs underline mt-2" to={`/prospects/pipeline?lead=${encodeURIComponent(crmLinks[r.id])}`}>Ver empresa no CRM</Link>}
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
