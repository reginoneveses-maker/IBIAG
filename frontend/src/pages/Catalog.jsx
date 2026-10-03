import { useEffect, useState } from "react";
import { api, CATEGORIES } from "@/lib/api";
import { useLang } from "@/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import ProductPhoto from "@/components/ProductPhoto";
import { INGREDIENTS, ingredientKeys, matchesCatalogFilter } from "@/lib/catalogIngredients";

const Catalog = () => {
  const { t, lang } = useLang();
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("all");
  const [offerProduct, setOfferProduct] = useState(null);
  const [offerText, setOfferText] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = () => {
    setLoading(true); setLoadError(false);
    return api.get("/products").then(r => setProducts(r.data))
      .catch(() => setLoadError(true)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const filtered = products.filter(p => matchesCatalogFilter(p, filter));
  const availableIngredients = new Set(products.flatMap(ingredientKeys));
  const extraIngredients = INGREDIENTS.filter(([key]) => !CATEGORIES.includes(key) && availableIngredients.has(key));
  const primaryFilters = [["all", "filter_all"], ...CATEGORIES.map(c => [c, `cat_${c}`])];

  const openOffer = (p) => {
    setOfferProduct(p);
    const desc = lang === "pt" ? p.description_pt : p.description_en;
    const text = lang === "pt"
      ? `Prezado cliente,\n\nSegue nossa oferta técnica para ${p.name}:\n\n• ${desc}\n• MOQ: ${p.moq}\n• Embalagem: ${p.packaging}\n• Preço: ${p.price_range}\n• Especificações: ${p.specs}\n• NCM/HS: ${p.hs_code}\n• Certificações: ${p.certifications.join(", ")}\n\nAguardo seu retorno para amostras e detalhes de logística.\n\nAtenciosamente,`
      : `Dear customer,\n\nPlease find our technical offer for ${p.name}:\n\n• ${desc}\n• MOQ: ${p.moq}\n• Packaging: ${p.packaging}\n• Price: ${p.price_range}\n• Specifications: ${p.specs}\n• HS Code: ${p.hs_code}\n• Certifications: ${p.certifications.join(", ")}\n\nLooking forward to your feedback on samples and logistics.\n\nBest regards,`;
    setOfferText(text);
  };

  const copyOffer = () => {
    navigator.clipboard.writeText(offerText);
    toast.success(t("copied"));
  };

  return (
    <div className="space-y-6" data-testid="catalog-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">02 · Catalog</div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{t("catalog_title")}</h1>
        <p className="text-base text-[#0F382C]/70 mt-2 max-w-2xl">{t("catalog_subtitle")}</p>
      </div>

      <div className="flex flex-wrap gap-2" data-testid="category-filters">
        {primaryFilters.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            data-testid={`filter-${key}`}
            aria-pressed={filter === key}
            className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${
              filter === key
                ? "bg-[#0F382C] text-white border-[#0F382C]"
                : "bg-white text-[#0F382C] border-[#0F382C]/15 hover:border-[#0F382C]/40"
            }`}
          >{t(label)} <span className="opacity-70">({products.filter(p => matchesCatalogFilter(p, key)).length})</span></button>
        ))}
        {(extraIngredients.length > 0 || availableIngredients.has("other")) && <label className="flex items-center gap-2 text-sm text-[#0F382C]">
          <span>{lang === "pt" ? "Mais ingredientes" : "More ingredients"}</span>
          <select data-testid="ingredient-filter" aria-label={lang === "pt" ? "Filtrar por ingrediente" : "Filter by ingredient"}
            value={primaryFilters.some(([key]) => key === filter) ? "" : filter}
            onChange={e => setFilter(e.target.value || "all")} className="rounded-full border border-[#0F382C]/20 bg-white px-3 py-2 max-w-[230px]">
            <option value="">{lang === "pt" ? "Selecione um ingrediente" : "Select an ingredient"}</option>
            {extraIngredients.map(([key, pt, en]) => <option key={key} value={key}>{lang === "pt" ? pt : en} ({products.filter(p => matchesCatalogFilter(p, key)).length})</option>)}
            {availableIngredients.has("other") && <option value="other">{lang === "pt" ? "Outros" : "Other"} ({products.filter(p => matchesCatalogFilter(p, "other")).length})</option>}
          </select>
        </label>}
        <div className="ml-auto text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/50 self-center">
          {filtered.length} {t("products_short")}
        </div>
      </div>

      {loading && <p role="status">{lang === "pt" ? "Carregando produtos…" : "Loading products…"}</p>}
      {loadError && <div role="alert" className="flex items-center gap-3">
        <span>{lang === "pt" ? "Não foi possível carregar o catálogo." : "Could not load the catalog."}</span>
        <Button variant="outline" onClick={load}>{lang === "pt" ? "Tentar novamente" : "Try again"}</Button>
      </div>}
      {!loading && !loadError && !filtered.length && <p role="status">{lang === "pt" ? "Nenhum produto disponível para este ingrediente." : "No products available for this ingredient."}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map(p => (
          <Card
            key={p.id}
            data-testid={`product-card-${p.id}`}
            className="overflow-hidden border-[#0F382C]/10 bg-white hover:-translate-y-0.5 hover:shadow-md hover:border-[#0F382C]/30 transition-all group"
          >
            <ProductPhoto key={`${p.id}:${p.image_url || ""}`} product={p} lang={lang} />
            <CardContent className="p-5 space-y-3">
              <div>
                <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">HS {p.hs_code}</div>
                <h3 className="font-display font-bold text-lg text-[#0F382C] mt-1">{p.name}</h3>
                <p className="text-sm text-[#0F382C]/70 mt-1 line-clamp-2">{lang === "pt" ? p.description_pt : p.description_en}</p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <div className="font-mono-alt uppercase tracking-wider text-[#0F382C]/50 text-[10px]">{t("moq")}</div>
                  <div className="text-[#0F382C] font-medium">{p.moq}</div>
                </div>
                <div>
                  <div className="font-mono-alt uppercase tracking-wider text-[#0F382C]/50 text-[10px]">{t("price")}</div>
                  <div className="text-[#0F382C] font-medium">{p.price_range}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                {p.certifications.slice(0, 3).map(c => (
                  <Badge key={c} variant="outline" className="text-[10px] border-amber-600/40 text-amber-800 bg-amber-50">{c}</Badge>
                ))}
              </div>
              <Button
                onClick={() => openOffer(p)}
                data-testid={`generate-offer-${p.id}`}
                className="w-full bg-[#0F382C] hover:bg-[#0A2920] text-white"
              >{t("generate_offer")}</Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!offerProduct} onOpenChange={(o) => !o && setOfferProduct(null)}>
        <DialogContent className="max-w-2xl bg-white" data-testid="offer-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-[#0F382C]">{t("generate_offer")}: {offerProduct?.name}</DialogTitle>
          </DialogHeader>
          <Textarea
            value={offerText}
            onChange={(e) => setOfferText(e.target.value)}
            rows={16}
            className="font-mono text-sm"
            data-testid="offer-textarea"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setOfferProduct(null)}>{t("close")}</Button>
            <Button onClick={copyOffer} className="bg-amber-600 hover:bg-amber-700" data-testid="copy-offer-button">{t("copy")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Catalog;
