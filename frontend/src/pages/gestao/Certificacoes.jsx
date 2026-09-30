import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { SectionBar, SupplierTabs, ExpiryBadge, Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Pencil, Upload, Download, downloadFile } from "@/components/erp";
import { ShieldCheck, Leaf } from "lucide-react";

const empty = { supplier_id: "", supplier_name: "", name: "", kind: "organic", issuer: "", number: "", issue_date: "", expiry_date: "", alert_days: 30, file_path: "", file_name: "", notes: "" };

export default function Certificacoes() {
  const [sp, setSp] = useSearchParams();
  const active = sp.get("supplier") || "";
  const [suppliers, setSuppliers] = useState([]);
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();

  const loadSup = () => api.get("/suppliers").then(r => setSuppliers(r.data));
  const load = () => api.get("/certifications", { params: active ? { supplier_id: active } : {} }).then(r => setItems(r.data));
  useEffect(() => { loadSup(); }, []);
  useEffect(() => { load(); }, [active]); // eslint-disable-line

  const setActive = (id) => { const n = new URLSearchParams(sp); if (id) n.set("supplier", id); else n.delete("supplier"); setSp(n); };
  const openNew = () => { const s = suppliers.find(x => x.id === active); setForm({ ...empty, supplier_id: active, supplier_name: s?.name || "" }); setDialog(true); };
  const save = async () => {
    if (!form.name) return toast.error("Nome da certificação obrigatório");
    if (!form.supplier_id) return toast.error("Selecione o fornecedor");
    if (form.id) await api.put(`/certifications/${form.id}`, form); else await api.post("/certifications", form);
    setDialog(false); toast.success("Certificação salva"); load();
  };
  const del = async (id) => { await api.delete(`/certifications/${id}`); load(); };
  const setSup = (id) => { const s = suppliers.find(x => x.id === id); setForm({ ...form, supplier_id: id, supplier_name: s?.name || "" }); };
  const activeName = suppliers.find(x => x.id === active)?.name;

  return (
    <div data-testid="certificacoes-panel">
      {el}
      <SectionBar title={activeName ? `Certificações · ${activeName}` : "Certificações de fornecedores"} subtitle="Orgânicas e demais certificações, com alerta antes do vencimento"
        action={<Button onClick={openNew} data-testid="new-cert-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Nova Certificação</Button>} />
      <SupplierTabs suppliers={suppliers} active={active} onChange={setActive} onCreate={(s) => { loadSup(); setActive(s.id); }} allLabel="Todas" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map(c => (
          <Card key={c.id} className="bg-white border-[#0F382C]/10" data-testid={`cert-${c.id}`}>
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${c.kind === "organic" ? "bg-emerald-50" : "bg-[#EFECE6]"}`}>
                  {c.kind === "organic" ? <Leaf className="w-5 h-5 text-emerald-700" /> : <ShieldCheck className="w-5 h-5 text-[#0F382C]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] font-mono-alt uppercase tracking-widest text-amber-700">{c.kind === "organic" ? "Orgânica" : "Outra"} {!active && c.supplier_name && `· ${c.supplier_name}`}</div>
                  <div className="font-semibold text-[#0F382C]">{c.name}</div>
                  <div className="text-xs text-[#0F382C]/60">{c.issuer}{c.number && ` · Nº ${c.number}`}</div>
                  <div className="text-xs text-[#0F382C]/70 mt-1">Emissão {c.issue_date || "—"} → Validade <b>{c.expiry_date || "—"}</b></div>
                </div>
                <ExpiryBadge date={c.expiry_date} alertDays={c.alert_days} />
              </div>
              {c.notes && <div className="text-xs text-[#0F382C]/70 mt-2">{c.notes}</div>}
              <div className="flex gap-2 mt-3">
                {c.file_path && <Button size="sm" variant="outline" onClick={() => downloadFile(c.file_path, c.file_name)}><Download className="w-3 h-3 mr-1" />Certificado</Button>}
                <Button size="sm" variant="ghost" onClick={() => { setForm(c); setDialog(true); }} className="ml-auto" data-testid={`edit-cert-${c.id}`}><Pencil className="w-3 h-3" /></Button>
                <Button size="sm" variant="ghost" onClick={() => del(c.id)} className="text-rose-600" data-testid={`delete-cert-${c.id}`}><Trash2 className="w-3 h-3" /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <div className="col-span-full text-sm text-[#0F382C]/50 italic" data-testid="certs-empty">Nenhuma certificação cadastrada{activeName ? ` para ${activeName}` : ""}.</div>}
      </div>

      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Certificação</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Select value={form.supplier_id} onValueChange={setSup}>
              <SelectTrigger className="bg-white col-span-2" data-testid="cert-supplier-select"><SelectValue placeholder="Fornecedor" /></SelectTrigger>
              <SelectContent className="bg-white">{suppliers.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
            <Input placeholder="Nome (ex: Orgânico Brasil, USDA Organic, Kosher)" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="col-span-2" data-testid="cert-name-input" />
            <Select value={form.kind} onValueChange={v => setForm({ ...form, kind: v })}>
              <SelectTrigger className="bg-white" data-testid="cert-kind-select"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white"><SelectItem value="organic">Orgânica</SelectItem><SelectItem value="other">Outra</SelectItem></SelectContent>
            </Select>
            <Input placeholder="Certificadora (IBD, Ecocert...)" value={form.issuer} onChange={e => setForm({ ...form, issuer: e.target.value })} />
            <Input placeholder="Nº do certificado" value={form.number} onChange={e => setForm({ ...form, number: e.target.value })} />
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#0F382C]/60 whitespace-nowrap">Avisar (dias)</span>
              <Input type="number" value={form.alert_days} onChange={e => setForm({ ...form, alert_days: parseInt(e.target.value) || 30 })} data-testid="cert-alert-days-input" />
            </div>
            <div><label className="text-[10px] uppercase text-[#0F382C]/60">Emissão</label><Input type="date" value={form.issue_date} onChange={e => setForm({ ...form, issue_date: e.target.value })} /></div>
            <div><label className="text-[10px] uppercase text-[#0F382C]/60">Validade</label><Input type="date" value={form.expiry_date} onChange={e => setForm({ ...form, expiry_date: e.target.value })} data-testid="cert-expiry-input" /></div>
            <Textarea placeholder="Notas / escopo" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2} className="col-span-2" />
            <Button onClick={() => doUpload(f => setForm({ ...form, file_path: f.path, file_name: f.name }))} variant="outline" className="col-span-2" disabled={uploading}>
              <Upload className="w-4 h-4 mr-1" />{form.file_name || (uploading ? "Enviando..." : "Anexar certificado (PDF)")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-cert-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
