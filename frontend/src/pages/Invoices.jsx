import { useEffect, useState, useRef } from "react";
import { api } from "@/AuthContext";
import { PageHeader, Button, Input, Card, CardContent, Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, useUpload, toast, Plus, Trash2, Upload, Download, fmtBRL } from "@/components/erp";

const empty = { number: "", kind: "entrada", party_name: "", party_cnpj: "", issue_date: "", total: 0, description: "", file_path: "", file_name: "" };

export default function Invoices() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [dialog, setDialog] = useState(false);
  const [form, setForm] = useState(empty);
  const { el, doUpload, uploading } = useUpload();
  const xmlRef = useRef();

  const load = () => api.get("/invoices").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.number) return toast.error("Número obrigatório");
    await api.post("/invoices", form);
    setDialog(false); setForm(empty); toast.success("NF salva"); load();
  };
  const del = async (id) => { await api.delete(`/invoices/${id}`); load(); };
  const dl = async (p, n) => {
    const r = await api.get(`/files/${p}`, { responseType: "blob" });
    const url = URL.createObjectURL(r.data); const a = document.createElement("a"); a.href = url; a.download = n; a.click();
  };

  const parseXML = () => {
    xmlRef.current.onchange = async () => {
      const f = xmlRef.current.files?.[0]; if (!f) return;
      const fd = new FormData(); fd.append("file", f);
      try {
        const r = await api.post("/invoices/parse-xml", fd, { headers: { "Content-Type": "multipart/form-data" } });
        // Also upload the file
        const fd2 = new FormData(); fd2.append("file", f);
        const up = await api.post("/upload", fd2, { headers: { "Content-Type": "multipart/form-data" } });
        setForm({ ...empty, ...r.data, file_path: up.data.path, file_name: up.data.name });
        setDialog(true);
        toast.success("XML processado");
      } catch { toast.error("Falha ao ler XML"); }
      xmlRef.current.value = "";
    };
    xmlRef.current.click();
  };

  const filtered = filter === "all" ? items : items.filter(x => x.kind === filter);
  const totalIn = items.filter(x => x.kind === "entrada").reduce((a, b) => a + (b.total || 0), 0);
  const totalOut = items.filter(x => x.kind === "saida").reduce((a, b) => a + (b.total || 0), 0);

  return (
    <div data-testid="invoices-page">
      {el}<input ref={xmlRef} type="file" accept=".xml" className="hidden" />
      <PageHeader number="02 · Notas Fiscais" title="Notas Fiscais" subtitle="Entrada e saída — XML NF-e ou registro manual"
        action={<div className="flex gap-2">
          <Button onClick={parseXML} variant="outline" data-testid="parse-xml-button"><Upload className="w-4 h-4 mr-1" />Importar XML</Button>
          <Button onClick={() => { setForm(empty); setDialog(true); }} data-testid="new-invoice-button" className="bg-amber-600 hover:bg-amber-700 text-white"><Plus className="w-4 h-4 mr-1" />Nova NF</Button>
        </div>} />

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="bg-white border-[#0F382C]/10"><CardContent className="p-4">
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">Entradas</div>
          <div className="font-display text-2xl font-bold text-[#0F382C]">{fmtBRL(totalIn)}</div>
        </CardContent></Card>
        <Card className="bg-white border-[#0F382C]/10"><CardContent className="p-4">
          <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">Saídas</div>
          <div className="font-display text-2xl font-bold text-amber-700">{fmtBRL(totalOut)}</div>
        </CardContent></Card>
      </div>

      <div className="flex gap-2 mb-4">
        {[["all", "Todas"], ["entrada", "Entrada"], ["saida", "Saída"]].map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} data-testid={`inv-filter-${k}`} className={`px-3 py-1.5 text-sm rounded-full border ${filter === k ? "bg-[#0F382C] text-white border-[#0F382C]" : "bg-white text-[#0F382C] border-[#0F382C]/15"}`}>{l}</button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.map(i => (
          <Card key={i.id} className="bg-white border-[#0F382C]/10">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`px-2 py-1 rounded text-[10px] font-mono-alt uppercase ${i.kind === "entrada" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800"}`}>{i.kind}</div>
              <div className="flex-1">
                <div className="font-semibold text-[#0F382C]">NF {i.number} — {i.party_name}</div>
                <div className="text-xs text-[#0F382C]/60">{i.party_cnpj} · {i.issue_date}</div>
              </div>
              <div className="font-mono-alt font-semibold text-[#0F382C]">{fmtBRL(i.total)}</div>
              {i.file_path && <Button size="sm" variant="ghost" onClick={() => dl(i.file_path, i.file_name)}><Download className="w-3 h-3" /></Button>}
              <Button size="sm" variant="ghost" onClick={() => del(i.id)} className="text-rose-600"><Trash2 className="w-3 h-3" /></Button>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && <div className="text-sm text-[#0F382C]/50 italic">Nenhuma NF ainda.</div>}
      </div>

      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent className="bg-white max-w-lg">
          <DialogHeader><DialogTitle>Nota Fiscal</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Número" value={form.number} onChange={e => setForm({...form, number: e.target.value})} data-testid="inv-number-input" />
            <Select value={form.kind} onValueChange={v => setForm({...form, kind: v})}>
              <SelectTrigger className="bg-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-white"><SelectItem value="entrada">Entrada</SelectItem><SelectItem value="saida">Saída</SelectItem></SelectContent>
            </Select>
            <Input placeholder="Parte (Fornecedor/Cliente)" value={form.party_name} onChange={e => setForm({...form, party_name: e.target.value})} className="col-span-2" />
            <Input placeholder="CNPJ" value={form.party_cnpj} onChange={e => setForm({...form, party_cnpj: e.target.value})} />
            <Input type="date" value={form.issue_date} onChange={e => setForm({...form, issue_date: e.target.value})} />
            <Input type="number" step="0.01" placeholder="Total (BRL)" value={form.total} onChange={e => setForm({...form, total: parseFloat(e.target.value) || 0})} className="col-span-2" data-testid="inv-total-input" />
            <Input placeholder="Descrição" value={form.description} onChange={e => setForm({...form, description: e.target.value})} className="col-span-2" />
            <Button onClick={() => doUpload(f => setForm({...form, file_path: f.path, file_name: f.name}))} variant="outline" className="col-span-2" disabled={uploading}>
              <Upload className="w-4 h-4 mr-1" />{form.file_name || (uploading ? "Enviando..." : "Anexar PDF/XML")}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialog(false)}>Cancelar</Button>
            <Button onClick={save} data-testid="save-invoice-button" className="bg-[#0F382C] text-white">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
