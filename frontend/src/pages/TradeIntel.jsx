import { useEffect, useState } from "react";
import { api, flag, fmtUSD, INDUSTRIES } from "@/lib/api";
import { useLang } from "@/i18n";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Globe2 } from "lucide-react";
import { toast } from "sonner";

const TradeIntel = () => {
  const { t } = useLang();
  const [records, setRecords] = useState([]);
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("all");
  const [industry, setIndustry] = useState("all");
  const [countries, setCountries] = useState([]);

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
