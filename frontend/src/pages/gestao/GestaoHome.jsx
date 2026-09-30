import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/AuthContext";
import { Card, CardContent, fmtBRL } from "@/components/erp";
import { AlertTriangle, ClipboardList, Receipt, Truck, FlaskConical, Calculator, ShieldCheck, Wallet } from "lucide-react";

export default function GestaoHome() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/gestao/stats").then(r => setS(r.data)).catch(() => {}); }, []);
  const tiles = [
    { to: "/gestao/procedimentos", icon: ClipboardList, label: "POPs", value: s?.pops ?? 0, id: "tile-pops" },
    { to: "/gestao/financeiro?tab=nf_saida", icon: Receipt, label: "NF Saída / Entrada", value: `${s?.invoices_out ?? 0} / ${s?.invoices_in ?? 0}`, id: "tile-nf" },
    { to: "/gestao/financeiro?tab=fluxo", icon: Wallet, label: "A receber", value: fmtBRL(s?.finance_receivable ?? 0), sub: `Pagar: ${fmtBRL(s?.finance_payable ?? 0)}`, id: "tile-finance" },
    { to: "/gestao/fornecedores?tab=fornecedores", icon: Truck, label: "Fornecedores", value: s?.suppliers ?? 0, id: "tile-suppliers" },
    { to: "/gestao/fornecedores?tab=certificacoes", icon: ShieldCheck, label: "Certificações", value: s?.certs_total ?? 0, id: "tile-certs" },
    { to: "/gestao/fornecedores?tab=compras", icon: Truck, label: "Compras abertas", value: s?.purchases_open ?? 0, id: "tile-purchases" },
    { to: "/gestao/prospeccao", icon: FlaskConical, label: "Specs IBIAG", value: s?.specs ?? 0, id: "tile-specs" },
    { to: "/gestao/precos", icon: Calculator, label: "Preços calculados", value: s?.prices ?? 0, id: "tile-prices" },
  ];
  const alerts = [...(s?.certs_expired || []), ...(s?.certs_expiring || [])];

  return (
    <div className="space-y-8" data-testid="gestao-home">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">IBIAG · Sistema de Gestão</div>
        <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F382C] tracking-tight">Visão geral</h1>
        <p className="text-base text-[#0F382C]/70 mt-2 max-w-2xl">Procedimentos, financeiro, fornecedores, certificações, specs e preços — tudo em um só lugar.</p>
      </div>

      <Card className={`border ${alerts.length ? "border-amber-400 bg-amber-50/60" : "border-[#0F382C]/10 bg-white/90"}`} data-testid="alerts-card">
        <CardContent className="p-5">
          <div className="flex items-center gap-2 font-display font-bold text-[#0F382C]"><AlertTriangle className={`w-5 h-5 ${alerts.length ? "text-amber-600" : "text-[#0F382C]/40"}`} />Alertas de validade</div>
          {alerts.length === 0 && <div className="text-sm text-[#0F382C]/60 mt-2" data-testid="alerts-empty">Nenhuma certificação vencida ou próxima do vencimento.</div>}
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            {alerts.map(a => (
              <Link key={a.id} to={`/gestao/fornecedores?tab=certificacoes&supplier=${a.supplier_id}`} data-testid={`alert-${a.id}`}
                className={`flex items-center justify-between p-3 rounded-lg border bg-white ${a.days < 0 ? "border-rose-300" : "border-amber-300"}`}>
                <div>
                  <div className="font-semibold text-sm text-[#0F382C]">{a.name}</div>
                  <div className="text-xs text-[#0F382C]/60">{a.supplier_name} · {a.expiry_date}</div>
                </div>
                <span className={`text-xs font-bold ${a.days < 0 ? "text-rose-700" : "text-amber-700"}`}>{a.days < 0 ? `Vencida há ${-a.days}d` : `Vence em ${a.days}d`}</span>
              </Link>
            ))}
          </div>
          {(s?.contracts_expiring ?? 0) > 0 && <div className="text-xs text-amber-800 mt-3" data-testid="contracts-expiring-note">{s.contracts_expiring} contrato(s) vencendo nos próximos 30 dias.</div>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {tiles.map(({ to, icon: Icon, label, value, sub, id }) => (
          <Link key={id} to={to} data-testid={id} className="p-4 rounded-xl bg-white border border-[#0F382C]/10 hover:border-amber-600/40 hover:-translate-y-0.5 transition-all">
            <Icon className="w-5 h-5 text-[#0F382C]" />
            <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mt-3">{label}</div>
            <div className="font-display text-xl font-bold text-[#0F382C]">{value}</div>
            {sub && <div className="text-[10px] text-rose-600 mt-1">{sub}</div>}
          </Link>
        ))}
      </div>
    </div>
  );
}
