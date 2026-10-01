// Generic CRUD list page factory helpers
import { useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trash2, Plus, Upload, Download, FileText, Pencil, Search, Truck, FileCheck2 } from "lucide-react";
import { toast } from "sonner";
import { fmtBRL, fmtUSD } from "@/lib/api";

export const PageHeader = ({ number, title, subtitle, action }) => (
  <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
    <div>
      <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">{number}</div>
      <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">{title}</h1>
      {subtitle && <p className="text-base text-[#0F382C]/70 mt-1">{subtitle}</p>}
    </div>
    {action}
  </div>
);

export const SectionBar = ({ title, subtitle, action, testId }) => (
  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4" data-testid={testId}>
    <div>
      <h2 className="font-display text-lg md:text-xl font-bold text-[#0F382C]">{title}</h2>
      {subtitle && <p className="text-sm text-[#0F382C]/60">{subtitle}</p>}
    </div>
    {action}
  </div>
);

export const SubTabs = ({ tabs, param = "tab" }) => {
  const [sp, setSp] = useSearchParams();
  const active = sp.get(param) || tabs[0].key;
  const current = tabs.find(t => t.key === active) || tabs[0];
  return (
    <div>
      <div className="flex gap-1 mb-6 overflow-x-auto scrollbar-thin border-b border-[#0F382C]/10" data-testid="sub-tabs">
        {tabs.map(t => (
          <button key={t.key} data-testid={`tab-${t.key}`} onClick={() => setSp({ [param]: t.key })}
            className={`px-4 py-2.5 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${current.key === t.key ? "border-amber-600 text-[#0F382C]" : "border-transparent text-[#0F382C]/55 hover:text-[#0F382C]"}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div data-testid={`tab-panel-${current.key}`}>{current.content}</div>
    </div>
  );
};

export const SupplierTabs = ({ suppliers, active, onChange, onCreate, allLabel = "Todos" }) => {
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);
  const create = async () => {
    if (!name.trim()) return;
    const r = await api.post("/suppliers", { name: name.trim() });
    setName(""); setAdding(false); onCreate(r.data);
  };
  return (
    <div className="flex flex-wrap items-center gap-2 mb-5" data-testid="supplier-tabs">
      <button onClick={() => onChange("")} data-testid="supplier-tab-all"
        className={`px-3 py-1.5 text-sm rounded-full border ${!active ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15"}`}>{allLabel}</button>
      {suppliers.map(s => (
        <button key={s.id} onClick={() => onChange(s.id)} data-testid={`supplier-tab-${s.id}`}
          className={`px-3 py-1.5 text-sm rounded-full border ${active === s.id ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15 hover:border-amber-600/50"}`}>{s.name}</button>
      ))}
      {adding ? (
        <div className="flex gap-1 items-center">
          <Input autoFocus value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === "Enter" && create()} placeholder="Nome do fornecedor" className="h-8 w-48 bg-white" data-testid="new-supplier-tab-input" />
          <Button size="sm" onClick={create} className="h-8 bg-[#0F382C] text-white" data-testid="new-supplier-tab-save">OK</Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(false)} className="h-8">✕</Button>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} data-testid="new-supplier-tab-button" className="px-3 py-1.5 text-sm rounded-full border border-dashed border-amber-600/60 text-amber-700 hover:bg-amber-50 flex items-center gap-1"><Plus className="w-3 h-3" />Nova aba</button>
      )}
    </div>
  );
};

export const downloadFile = async (path, name) => {
  const r = await api.get(`/files/${path}`, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a"); a.href = url; a.download = name || "arquivo"; a.click();
  URL.revokeObjectURL(url);
};

export const daysUntil = (d) => { if (!d) return null; return Math.ceil((new Date(d) - new Date()) / 86400000); };

export const ExpiryBadge = ({ date, alertDays = 30 }) => {
  const days = daysUntil(date);
  if (days === null) return null;
  const expired = days < 0, expiring = days >= 0 && days <= alertDays;
  const cls = expired ? "bg-rose-50 text-rose-700 border-rose-200" : expiring ? "bg-amber-50 text-amber-800 border-amber-300" : "bg-emerald-50 text-emerald-700 border-emerald-200";
  const txt = expired ? `Vencido há ${Math.abs(days)}d` : expiring ? `Vence em ${days}d` : `Válido · ${days}d`;
  return <span data-testid="expiry-badge" className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cls}`}>{txt}</span>;
};

export const useUpload = () => {
  const inputRef = useRef();
  const [uploading, setUploading] = useState(false);
  const doUpload = (onDone) => {
    const el = inputRef.current;
    if (!el) return;
    el.onchange = async () => {
      const f = el.files?.[0]; if (!f) return;
      setUploading(true);
      try {
        const fd = new FormData(); fd.append("file", f);
        const r = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
        onDone(r.data);
      } catch (e) { toast.error("Upload falhou"); }
      finally { setUploading(false); el.value = ""; }
    };
    el.click();
  };
  const el = <input ref={inputRef} type="file" className="hidden" />;
  return { el, doUpload, uploading };
};

export { Button, Input, Textarea, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Trash2, Plus, Upload, Download, FileText, Pencil, Search, Truck, FileCheck2, toast, fmtBRL, fmtUSD };
