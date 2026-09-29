import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLang } from "@/i18n";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Copy, Mail } from "lucide-react";
import { toast } from "sonner";

const catColor = {
  intro: "bg-blue-50 text-blue-800 border-blue-200",
  follow_up: "bg-purple-50 text-purple-800 border-purple-200",
  sample: "bg-amber-50 text-amber-800 border-amber-200",
  quotation: "bg-emerald-50 text-emerald-800 border-emerald-200",
};

const Templates = () => {
  const { t, lang } = useLang();
  const [tpls, setTpls] = useState([]);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get("/templates", { params: { language: lang } }).then(r => setTpls(r.data)).catch(() => {});
  }, [lang]);

  const filtered = filter === "all" ? tpls : tpls.filter(x => x.category === filter);

  const copy = (text) => {
    navigator.clipboard.writeText(text);
    toast.success(t("copied"));
  };

  return (
    <div className="space-y-6" data-testid="templates-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2 flex items-center gap-1"><Mail className="w-3 h-3" /> 05 · Templates</div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{t("templates_title")}</h1>
        <p className="text-base text-[#0F382C]/70 mt-1">{t("templates_subtitle")}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {[["all", "filter_all"], ["intro", "cat_intro"], ["follow_up", "cat_follow_up"], ["sample", "cat_sample"], ["quotation", "cat_quotation"]].map(([k, l]) => (
          <button
            key={k}
            onClick={() => setFilter(k)}
            data-testid={`tpl-filter-${k}`}
            className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${
              filter === k ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15 hover:border-[#0F382C]/40"
            }`}
          >{t(l)}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map(tp => (
          <Card key={tp.id} data-testid={`template-${tp.id}`} className="bg-white border-[#0F382C]/10 hover:border-[#0F382C]/30 transition-all">
            <CardContent className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className={catColor[tp.category]}>{t(`cat_${tp.category}`)}</Badge>
                <Badge variant="outline" className="text-[10px] font-mono-alt uppercase border-[#0F382C]/20 text-[#0F382C]/70">{tp.language}</Badge>
              </div>
              <h3 className="font-display font-bold text-lg text-[#0F382C]">{lang === "pt" ? tp.name_pt : tp.name_en}</h3>
              {tp.subject && <div className="text-sm text-[#0F382C]/80"><span className="font-mono-alt text-[10px] uppercase tracking-widest text-[#0F382C]/50">{t("subject")}:</span> {tp.subject}</div>}
              <div className="text-sm text-[#0F382C]/70 line-clamp-3 whitespace-pre-wrap">{tp.body}</div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setSelected(tp)} data-testid={`view-tpl-${tp.id}`}>{t("view_details")}</Button>
                <Button size="sm" onClick={() => copy(`${tp.subject}\n\n${tp.body}`)} data-testid={`copy-tpl-${tp.id}`} className="bg-amber-600 hover:bg-amber-700 text-white">
                  <Copy className="w-3 h-3 mr-1" />{t("copy")}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-2xl bg-white" data-testid="tpl-detail-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-[#0F382C]">{selected && (lang === "pt" ? selected.name_pt : selected.name_en)}</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-3">
              <div className="text-sm"><span className="font-mono-alt text-[10px] uppercase tracking-widest text-[#0F382C]/50">{t("subject")}:</span> {selected.subject}</div>
              <Textarea value={selected.body} readOnly rows={16} className="text-sm font-mono" />
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelected(null)}>{t("close")}</Button>
            <Button onClick={() => selected && copy(`${selected.subject}\n\n${selected.body}`)} className="bg-amber-600 hover:bg-amber-700 text-white">{t("copy")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Templates;
