import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Upload, Database, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const ImportCRM = () => {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const submit = async () => {
    if (!file) return toast.error("Selecione um arquivo CSV ou XLSX.");
    setBusy(true); setResult(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const r = await api.post("/leads/import", body, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data);
      toast.success("Importação concluída.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Não foi possível importar o arquivo.");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="crm-import-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">05 · Importação CRM</div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#0F382C]">Importar empresas</h1>
        <p className="text-base text-[#0F382C]/70 mt-2 max-w-3xl">
          Traga as empresas do seu CRM atual para o IBIAG. O importador aceita CSV e Excel e evita duplicar empresas já cadastradas.
        </p>
      </div>

      <Card className="border-[#0F382C]/10 bg-white">
        <CardContent className="p-6 space-y-5">
          <div className="rounded-xl border-2 border-dashed border-[#0F382C]/15 p-8 text-center">
            <Database className="w-10 h-10 mx-auto text-amber-600 mb-3" />
            <div className="font-semibold text-[#0F382C]">Arquivo do CRM atual</div>
            <div className="text-sm text-[#0F382C]/60 mt-1">CSV ou XLSX · pode conter as 1.500 empresas de uma vez</div>
            <input
              type="file" accept=".csv,.xlsx,.xls"
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="mt-4 block w-full text-sm"
              data-testid="crm-import-file"
            />
          </div>

          <div className="text-sm text-[#0F382C]/70">
            <strong>Campos reconhecidos:</strong> empresa, contato, e-mail, telefone, site, LinkedIn, país, indústria,
            produto, decisor, cargo, e-mail/telefone do decisor, fornecedor atual, prioridade, valor e observações.
          </div>

          <Button onClick={submit} disabled={!file || busy} className="bg-[#0F382C] hover:bg-[#0A2920] text-white" data-testid="crm-import-button">
            <Upload className="w-4 h-4 mr-2" />{busy ? "Importando..." : "Importar para o IBIAG"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card className="border-emerald-700/20 bg-white">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 font-semibold text-[#0F382C] mb-4"><CheckCircle2 className="w-5 h-5 text-emerald-700" /> Resultado</div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><div className="text-2xl font-bold">{result.imported}</div><div className="text-xs text-[#0F382C]/60">novas</div></div>
              <div><div className="text-2xl font-bold">{result.updated}</div><div className="text-xs text-[#0F382C]/60">atualizadas</div></div>
              <div><div className="text-2xl font-bold">{result.skipped}</div><div className="text-xs text-[#0F382C]/60">já existentes</div></div>
            </div>
            {result.errors?.length > 0 && <div className="mt-4 text-xs text-rose-700">{result.errors.slice(0,10).join(" · ")}</div>}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ImportCRM;
