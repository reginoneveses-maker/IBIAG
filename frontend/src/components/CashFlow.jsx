import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { Card, CardContent, fmtBRL } from "@/components/erp";
import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const label = (k) => `${MONTHS[parseInt(k.slice(5, 7), 10) - 1]}/${k.slice(2, 4)}`;

export const CashFlow = () => {
  const [data, setData] = useState([]);
  useEffect(() => { api.get("/finance/cashflow").then(r => setData(r.data.map(d => ({ ...d, label: label(d.month) })))); }, []);
  const totIn = data.reduce((a, b) => a + b.receivable, 0);
  const totOut = data.reduce((a, b) => a + b.payable, 0);
  const cur = data[data.length - 1];

  return (
    <div data-testid="cashflow-panel">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[["Entradas (12m)", totIn, "text-emerald-700", "cf-total-in"], ["Saídas (12m)", totOut, "text-rose-600", "cf-total-out"],
          ["Saldo (12m)", totIn - totOut, totIn - totOut >= 0 ? "text-[#0F382C]" : "text-rose-600", "cf-balance"],
          ["Saldo do mês", cur?.balance ?? 0, (cur?.balance ?? 0) >= 0 ? "text-[#0F382C]" : "text-rose-600", "cf-month-balance"]].map(([l, v, c, id]) => (
          <Card key={l} className="bg-white border-[#0F382C]/10" data-testid={id}><CardContent className="p-4">
            <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">{l}</div>
            <div className={`font-display text-xl sm:text-2xl font-bold ${c}`}>{fmtBRL(v)}</div>
          </CardContent></Card>
        ))}
      </div>
      <Card className="bg-white border-[#0F382C]/10 mb-6"><CardContent className="p-4">
        <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-3">Fluxo de caixa mensal — a receber × a pagar × acumulado</div>
        <div className="h-72" data-testid="cashflow-chart">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0F382C15" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#0F382C99" }} />
              <YAxis tick={{ fontSize: 11, fill: "#0F382C99" }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtBRL(v)} contentStyle={{ borderRadius: 8, borderColor: "#0F382C22" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="receivable" name="A receber" fill="#0F382C" radius={[4, 4, 0, 0]} />
              <Bar dataKey="payable" name="A pagar" fill="#D97706" radius={[4, 4, 0, 0]} />
              <Line type="monotone" dataKey="cumulative" name="Acumulado" stroke="#9F1239" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent></Card>
      <Card className="bg-white border-[#0F382C]/10 mb-6"><CardContent className="p-4">
        <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-3">Notas fiscais por mês — saída × entrada</div>
        <div className="h-52" data-testid="nf-chart">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0F382C15" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#0F382C99" }} />
              <YAxis tick={{ fontSize: 11, fill: "#0F382C99" }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtBRL(v)} contentStyle={{ borderRadius: 8, borderColor: "#0F382C22" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="nf_saida" name="NF Saída" fill="#047857" radius={[4, 4, 0, 0]} />
              <Bar dataKey="nf_entrada" name="NF Entrada" fill="#2563EB" radius={[4, 4, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent></Card>
    </div>
  );
};
