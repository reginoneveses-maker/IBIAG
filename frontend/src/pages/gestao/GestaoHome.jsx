import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/AuthContext";
import { Card, CardContent, fmtBRL } from "@/components/erp";
import {
  AlertTriangle, ClipboardList, Receipt, Truck, FlaskConical, Calculator,
  ShieldCheck, Wallet, ArrowUpRight, FileText, ShoppingCart, Package
} from "lucide-react";

const AreaCard = ({ to, icon: Icon, eyebrow, title, text, children }) => (
  <Link to={to} className="group block rounded-2xl bg-white border border-[#102F27]/10 p-5 sm:p-6 hover:border-amber-500/40 hover:-translate-y-0.5 transition-all shadow-[0_1px_2px_rgba(16,47,39,0.03)]">
    <div className="flex items-start justify-between gap-4">
      <div className="w-10 h-10 rounded-xl bg-[#102F27]/6 flex items-center justify-center">
        <Icon className="w-5 h-5 text-[#102F27]" />
      </div>
      <ArrowUpRight className="w-4 h-4 text-[#102F27]/25 group-hover:text-amber-600 transition-colors" />
    </div>
    <div className="mt-5 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">{eyebrow}</div>
    <h2 className="font-display text-xl font-bold text-[#102F27] mt-1">{title}</h2>
    <p className="text-sm text-[#102F27]/55 mt-1.5">{text}</p>
    {children && <div className="mt-4 pt-4 border-t border-[#102F27]/8">{children}</div>}
  </Link>
);

export default function GestaoHome() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/gestao/stats").then(r => setS(r.data)).catch(() => {}); }, []);
  const alerts = [...(s?.certs_expired || []), ...(s?.certs_expiring || [])];

  return (
    <div className="space-y-8" data-testid="gestao-home">
      <section className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-700 mb-2">IBIAG · Gestão</div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-[#102F27] tracking-tight">Tudo no lugar certo.</h1>
          <p className="text-sm sm:text-base text-[#102F27]/55 mt-2 max-w-2xl">Acesse cada área pelo que você quer resolver — sem misturar financeiro, fornecedores, produtos e documentos.</p>
        </div>
      </section>

      {alerts.length > 0 && (
        <Card className="border-amber-300 bg-amber-50/70">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-center gap-2 font-semibold text-[#102F27]"><AlertTriangle className="w-5 h-5 text-amber-600" />Atenção</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
              {alerts.slice(0,4).map(a => (
                <Link key={a.id} to={`/gestao/fornecedores?tab=certificacoes&supplier=${a.supplier_id}`} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-white border border-amber-200">
                  <div className="min-w-0"><div className="font-medium text-sm truncate">{a.name}</div><div className="text-xs text-[#102F27]/50 truncate">{a.supplier_name} · {a.expiry_date}</div></div>
                  <span className="text-xs font-bold text-amber-700 whitespace-nowrap">{a.days < 0 ? `Vencida há ${-a.days}d` : `Vence em ${a.days}d`}</span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <section>
        <div className="flex items-center gap-2 mb-3"><div className="w-1.5 h-5 rounded-full bg-amber-600" /><h2 className="font-display text-lg font-bold text-[#102F27]">Áreas principais</h2></div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <AreaCard to="/gestao/fornecedores?tab=fornecedores" icon={Truck} eyebrow="Cadastros" title="Fornecedores" text="Empresas, contratos, compras e certificações.">
            <span className="text-xs text-[#102F27]/55">{s?.suppliers ?? 0} fornecedores cadastrados</span>
          </AreaCard>
          <AreaCard to="/gestao/financeiro?tab=fluxo" icon={Wallet} eyebrow="Financeiro" title="Financeiro & NF" text="Contas, fluxo de caixa e notas de entrada e saída.">
            <div className="flex gap-4 text-xs"><span>Receber <b>{fmtBRL(s?.finance_receivable ?? 0)}</b></span><span>Pagar <b>{fmtBRL(s?.finance_payable ?? 0)}</b></span></div>
          </AreaCard>
          <AreaCard to="/gestao/prospeccao" icon={FlaskConical} eyebrow="Produtos" title="Specs & documentos" text="Fichas técnicas, versões IBIAG e arquivos dos produtos.">
            <span className="text-xs text-[#102F27]/55">{s?.specs ?? 0} specs cadastradas</span>
          </AreaCard>
          <AreaCard to="/gestao/precos" icon={Calculator} eyebrow="Comercial" title="Preços & calculadora" text="Custos, frete, impostos, margem, câmbio e preço de venda.">
            <span className="text-xs text-[#102F27]/55">{s?.prices ?? 0} cálculos salvos</span>
          </AreaCard>
        </div>
      </section>

      <section>
        <div className="flex items-center gap-2 mb-3"><div className="w-1.5 h-5 rounded-full bg-[#102F27]/25" /><h2 className="font-display text-lg font-bold text-[#102F27]">Atalhos</h2></div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ["/gestao/procedimentos", ClipboardList, "Procedimentos", s?.pops ?? 0],
            ["/gestao/financeiro?tab=nf_saida", Receipt, "NF de saída", s?.invoices_out ?? 0],
            ["/gestao/fornecedores?tab=compras", ShoppingCart, "Compras abertas", s?.purchases_open ?? 0],
            ["/gestao/fornecedores?tab=certificacoes", ShieldCheck, "Certificações", s?.certs_total ?? 0],
          ].map(([to, Icon, label, value]) => (
            <Link key={to} to={to} className="flex items-center gap-3 p-4 rounded-xl bg-white border border-[#102F27]/8 hover:border-amber-500/30 transition-all">
              <Icon className="w-4 h-4 text-[#102F27]/65" />
              <div className="min-w-0"><div className="text-xs font-medium text-[#102F27] truncate">{label}</div><div className="text-[11px] text-[#102F27]/45">{value}</div></div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
