import { useEffect, useState } from "react";
import { api, STAGES, INDUSTRIES, stageColor, flag, fmtUSD } from "@/lib/api";
import { useLang } from "@/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Card } from "@/components/ui/card";
import { Plus, MoreVertical, Trash2, Edit3, MessageSquarePlus } from "lucide-react";
import { toast } from "sonner";

const emptyLead = { company: "", contact_name: "", email: "", phone: "", website: "", linkedin: "", country: "", country_code: "", industry: "beverage", stage: "new_lead", product_interest: "", decision_maker: "", decision_maker_title: "", decision_maker_email: "", decision_maker_phone: "", current_supplier: "", priority: "normal", source_url: "", deal_value: 0, notes: "" };

const Pipeline = () => {
  const { t } = useLang();
  const [leads, setLeads] = useState([]);
  const [industryFilter, setIndustryFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(emptyLead);
  const [detailLead, setDetailLead] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [newInter, setNewInter] = useState({ type: "email", subject: "", content: "" });

  const load = () => api.get("/leads").then(r => setLeads(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const filtered = leads.filter(l => {
    if (industryFilter !== "all" && l.industry !== industryFilter) return false;
    if (search && !`${l.company} ${l.contact_name} ${l.country}`.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const byStage = (s) => filtered.filter(l => l.stage === s);

  const openNew = () => { setEditing({ ...emptyLead }); setDialogOpen(true); };
  const openEdit = (l) => { setEditing(l); setDialogOpen(true); };

  const save = async () => {
    if (!editing.company.trim()) return toast.error("Company required");
    if (editing.id) {
      await api.put(`/leads/${editing.id}`, editing);
      toast.success(t("lead_updated"));
    } else {
      await api.post("/leads", editing);
      toast.success(t("lead_created"));
    }
    setDialogOpen(false);
    load();
  };

  const del = async (id) => {
    await api.delete(`/leads/${id}`);
    toast.success(t("lead_deleted"));
    load();
  };

  const moveStage = async (l, newStage) => {
    await api.patch(`/leads/${l.id}/stage`, { stage: newStage });
    toast.success(t("stage_updated"));
    load();
  };

  const openDetail = async (l) => {
    setDetailLead(l);
    const r = await api.get("/interactions", { params: { lead_id: l.id } });
    setInteractions(r.data);
  };

  const addInteraction = async () => {
    if (!newInter.content.trim()) return;
    await api.post("/interactions", { ...newInter, lead_id: detailLead.id });
    setNewInter({ type: "email", subject: "", content: "" });
    toast.success(t("interaction_logged"));
    const r = await api.get("/interactions", { params: { lead_id: detailLead.id } });
    setInteractions(r.data);
  };

  return (
    <div className="space-y-6" data-testid="pipeline-page">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#104496]/60 mb-2">03 · CRM</div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#104496]">{t("pipeline_title")}</h1>
          <p className="text-base text-[#104496]/70 mt-1">{t("pipeline_subtitle")}</p>
        </div>
        <Button onClick={openNew} data-testid="new-lead-button" className="bg-[#104496] hover:bg-[#0B3274] text-white">
          <Plus className="w-4 h-4 mr-1" /> {t("new_lead")}
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Input placeholder={t("search_leads")} value={search} onChange={(e) => setSearch(e.target.value)} data-testid="search-leads-input" className="max-w-sm bg-white" />
        <Select value={industryFilter} onValueChange={setIndustryFilter}>
          <SelectTrigger className="w-full sm:w-56 bg-white" data-testid="industry-filter-select"><SelectValue placeholder={t("filter_industry")} /></SelectTrigger>
          <SelectContent className="bg-white">
            <SelectItem value="all">{t("all_industries")}</SelectItem>
            {INDUSTRIES.map(i => <SelectItem key={i} value={i}>{t(`industry_${i}`)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin" data-testid="kanban-board">
        {STAGES.map(stage => (
          <div key={stage} className="flex-shrink-0 w-72" data-testid={`kanban-column-${stage}`}>
            <div className={`px-3 py-2 rounded-t-lg border ${stageColor(stage)} flex items-center justify-between`}>
              <span className="font-semibold text-xs uppercase tracking-wider">{t(`stage_${stage}`)}</span>
              <span className="text-xs font-mono-alt">{byStage(stage).length}</span>
            </div>
            <div className="bg-white/60 border border-t-0 border-[#104496]/10 rounded-b-lg p-2 min-h-[400px] space-y-2">
              {byStage(stage).map(l => (
                <Card
                  key={l.id}
                  data-testid={`lead-card-${l.id}`}
                  className="p-3 bg-white border border-[#104496]/10 hover:border-[#104496]/30 hover:shadow-md transition-all cursor-pointer animate-card-in"
                  onClick={() => openDetail(l)}
                >
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-[#104496] truncate">{l.company}</div>
                      <div className="text-xs text-[#104496]/60 flex items-center gap-1">
                        <span>{flag(l.country_code)}</span> <span className="truncate">{l.country}</span>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <button data-testid={`lead-menu-${l.id}`} className="p-1 hover:bg-[#EEF3FB] rounded"><MoreVertical className="w-4 h-4" /></button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="bg-white" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenuItem onClick={() => openEdit(l)}><Edit3 className="w-3 h-3 mr-2" />{t("edit")}</DropdownMenuItem>
                        {STAGES.filter(s => s !== stage).map(s => (
                          <DropdownMenuItem key={s} onClick={() => moveStage(l, s)}>→ {t(`stage_${s}`)}</DropdownMenuItem>
                        ))}
                        <DropdownMenuItem onClick={() => del(l.id)} className="text-rose-600"><Trash2 className="w-3 h-3 mr-2" />{t("delete")}</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <div className="mt-2 flex justify-between items-center text-xs">
                    <span className="text-[#104496]/60">{t(`industry_${l.industry}`)}</span>
                    <span className="font-mono-alt text-[#104496] font-semibold">{fmtUSD(l.deal_value)}</span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Lead form dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg bg-white" data-testid="lead-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-[#104496]">{editing.id ? t("edit") : t("new_lead")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input placeholder={t("company")} value={editing.company} onChange={(e) => setEditing({ ...editing, company: e.target.value })} data-testid="lead-company-input" />
            <Input placeholder={t("contact_name")} value={editing.contact_name} onChange={(e) => setEditing({ ...editing, contact_name: e.target.value })} data-testid="lead-contact-input" />
            <Input placeholder={t("email")} value={editing.email} onChange={(e) => setEditing({ ...editing, email: e.target.value })} data-testid="lead-email-input" />
            <Input placeholder={t("phone")} value={editing.phone} onChange={(e) => setEditing({ ...editing, phone: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Website" value={editing.website} onChange={(e) => setEditing({ ...editing, website: e.target.value })} />
              <Input placeholder="LinkedIn" value={editing.linkedin} onChange={(e) => setEditing({ ...editing, linkedin: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Produto de interesse" value={editing.product_interest} onChange={(e) => setEditing({ ...editing, product_interest: e.target.value })} />
              <Input placeholder="Prioridade (high/normal/low)" value={editing.priority} onChange={(e) => setEditing({ ...editing, priority: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Decisor de compras" value={editing.decision_maker} onChange={(e) => setEditing({ ...editing, decision_maker: e.target.value })} />
              <Input placeholder="Cargo do decisor" value={editing.decision_maker_title} onChange={(e) => setEditing({ ...editing, decision_maker_title: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="E-mail do decisor" value={editing.decision_maker_email} onChange={(e) => setEditing({ ...editing, decision_maker_email: e.target.value })} />
              <Input placeholder="Telefone do decisor" value={editing.decision_maker_phone} onChange={(e) => setEditing({ ...editing, decision_maker_phone: e.target.value })} />
            </div>
            <Input placeholder="Fornecedor atual" value={editing.current_supplier} onChange={(e) => setEditing({ ...editing, current_supplier: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder={t("country")} value={editing.country} onChange={(e) => setEditing({ ...editing, country: e.target.value })} />
              <Input placeholder="ISO (US, BR, DE...)" maxLength={2} value={editing.country_code} onChange={(e) => setEditing({ ...editing, country_code: e.target.value.toUpperCase() })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Select value={editing.industry} onValueChange={(v) => setEditing({ ...editing, industry: v })}>
                <SelectTrigger className="bg-white" data-testid="lead-industry-select"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-white">{INDUSTRIES.map(i => <SelectItem key={i} value={i}>{t(`industry_${i}`)}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={editing.stage} onValueChange={(v) => setEditing({ ...editing, stage: v })}>
                <SelectTrigger className="bg-white" data-testid="lead-stage-select"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-white">{STAGES.map(s => <SelectItem key={s} value={s}>{t(`stage_${s}`)}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <Input type="number" placeholder={t("deal_value")} value={editing.deal_value} onChange={(e) => setEditing({ ...editing, deal_value: Number(e.target.value) })} />
            <Textarea placeholder={t("notes")} value={editing.notes} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>{t("cancel")}</Button>
            <Button onClick={save} className="bg-[#104496] hover:bg-[#0B3274] text-white" data-testid="save-lead-button">{t("save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail dialog */}
      <Dialog open={!!detailLead} onOpenChange={(o) => !o && setDetailLead(null)}>
        <DialogContent className="max-w-2xl bg-white max-h-[90vh] overflow-y-auto" data-testid="lead-detail-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-[#104496] flex items-center gap-2">
              <span>{flag(detailLead?.country_code)}</span> {detailLead?.company}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">{t("contact_name")}</span><div>{detailLead?.contact_name || "—"}</div></div>
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">{t("email")}</span><div className="truncate">{detailLead?.email || "—"}</div></div>
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">Decisor</span><div>{detailLead?.decision_maker || "—"} {detailLead?.decision_maker_title ? <span className="text-xs text-[#104496]/50">({detailLead.decision_maker_title})</span> : null}</div></div>
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">Produto</span><div>{detailLead?.product_interest || "—"}</div></div>
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">{t("country")}</span><div>{detailLead?.country || "—"}</div></div>
              <div><span className="text-[#104496]/60 font-mono-alt text-[10px] uppercase tracking-widest">{t("deal_value")}</span><div className="text-[#104496] font-mono-alt">{fmtUSD(detailLead?.deal_value)}</div></div>
            </div>
            {detailLead?.notes && <div className="p-3 bg-[#F7F9FC] rounded-lg text-sm border border-[#104496]/10">{detailLead.notes}</div>}

            <div className="border-t border-[#104496]/10 pt-4">
              <div className="font-display font-semibold text-[#104496] mb-3 flex items-center gap-2"><MessageSquarePlus className="w-4 h-4" />{t("log_interaction")}</div>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <Select value={newInter.type} onValueChange={(v) => setNewInter({ ...newInter, type: v })}>
                  <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="email">{t("email")}</SelectItem>
                    <SelectItem value="call">{t("call")}</SelectItem>
                    <SelectItem value="whatsapp">{t("whatsapp")}</SelectItem>
                    <SelectItem value="meeting">{t("meeting")}</SelectItem>
                    <SelectItem value="sample">{t("sample_int")}</SelectItem>
                  </SelectContent>
                </Select>
                <Input placeholder={t("subject")} value={newInter.subject} onChange={(e) => setNewInter({ ...newInter, subject: e.target.value })} className="col-span-2" />
              </div>
              <Textarea placeholder={t("body")} value={newInter.content} onChange={(e) => setNewInter({ ...newInter, content: e.target.value })} rows={2} data-testid="interaction-content-input" />
              <Button onClick={addInteraction} size="sm" className="mt-2 bg-[#104496] hover:bg-[#0B3274] text-white" data-testid="add-interaction-button">{t("log_interaction")}</Button>
            </div>

            <div>
              <div className="font-display font-semibold text-[#104496] mb-2">{t("interactions")}</div>
              {interactions.length === 0 ? (
                <div className="text-sm text-[#104496]/50 italic">{t("no_interactions")}</div>
              ) : (
                <div className="space-y-2">
                  {interactions.map(i => (
                    <div key={i.id} className="p-3 border border-[#104496]/10 rounded-lg bg-white text-sm">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-mono-alt uppercase tracking-widest text-[#104496]">{t(i.type === "sample" ? "sample_int" : i.type)}</span>
                        <span className="text-xs text-[#104496]/50">{new Date(i.created_at).toLocaleDateString()}</span>
                      </div>
                      {i.subject && <div className="font-medium text-[#104496]">{i.subject}</div>}
                      <div className="text-[#104496]/80 whitespace-pre-wrap">{i.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Pipeline;
