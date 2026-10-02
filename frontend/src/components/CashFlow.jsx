import { useEffect, useState } from "react";
import { api } from "@/AuthContext";
import { Card, CardContent, toast } from "@/components/erp";
import { ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const label = (k) => `${MONTHS[parseInt(k.slice(5, 7), 10) - 1]}/${k.slice(2, 4)}`;

export const CashFlow = () => {
  const [data, setData] = useState([]);
  const [currency, setCurrency] = useState("BRL");
  const [period,setPeriod] = useState("forecast");
  const [mode,setMode] = useState("planned");
  const money = (value) => new Intl.NumberFormat("pt-BR", {style:"currency",currency}).format(value || 0);
  useEffect(() => {
    let active=true;
    const load=()=>api.get("/finance/cashflow",{params:{currency,period}}).then(r=>{if(active)setData(r.data.map(d=>({...d,label:label(d.month)})));}).catch(()=>toast.error("Não foi possível carregar o fluxo de caixa."));
    load();window.addEventListener("finance-updated",load);
    return ()=>{active=false;window.removeEventListener("finance-updated",load);};
  }, [currency,period]);
  const inKey=mode==="planned"?"receivable":"received", outKey=mode==="planned"?"payable":"paid";
  const totIn = data.reduce((a, b) => a + b[inKey], 0);
  const totOut = data.reduce((a, b) => a + b[outKey], 0);
  const now=new Date();
  const currentKey=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
  const cur = data.find(row=>row.month===currentKey);
  const currentBalance=mode==="planned"?cur?.balance:cur?.cash_balance;

  return (
    <div data-testid="cashflow-panel">
      <div className="flex flex-wrap items-center gap-3 mb-4"><label htmlFor="cashflow-currency" className="text-sm">Moeda do fluxo de caixa</label><select id="cashflow-currency" value={currency} onChange={e=>setCurrency(e.target.value)} className="border rounded-lg p-2 bg-white">{["BRL","USD","EUR","GBP","CAD","AUD","JPY","CNY"].map(c=><option key={c}>{c}</option>)}</select><select aria-label="Período do fluxo de caixa" value={period} onChange={e=>setPeriod(e.target.value)} className="border rounded-lg p-2 bg-white"><option value="forecast">Próximos 12 meses</option><option value="history">Últimos 12 meses</option></select><select aria-label="Visão do fluxo de caixa" value={mode} onChange={e=>setMode(e.target.value)} className="border rounded-lg p-2 bg-white"><option value="planned">Contas por vencimento</option><option value="actual">Pagamentos e recebimentos realizados</option></select><span className="text-xs text-slate-500">Valores separados por moeda, sem conversão cambial.</span></div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[[mode==="planned"?"Recebimentos previstos (12m)":"Recebimentos realizados (12m)", totIn, "text-emerald-700", "cf-total-in"], [mode==="planned"?"Pagamentos previstos (12m)":"Pagamentos realizados (12m)", totOut, "text-rose-600", "cf-total-out"],
          ["Saldo (12m)", totIn - totOut, totIn - totOut >= 0 ? "text-[#0F382C]" : "text-rose-600", "cf-balance"],
          ["Saldo do mês", currentBalance ?? 0, (currentBalance ?? 0) >= 0 ? "text-[#0F382C]" : "text-rose-600", "cf-month-balance"]].map(([l, v, c, id]) => (
          <Card key={l} className="bg-white border-[#0F382C]/10" data-testid={id}><CardContent className="p-4">
            <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">{l}</div>
            <div className={`font-display text-xl sm:text-2xl font-bold ${c}`}>{money(v)}</div>
          </CardContent></Card>
        ))}
      </div>
      <Card className="bg-white border-[#0F382C]/10 mb-6"><CardContent className="p-4">
        <div className="text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/60 mb-3">{mode==="planned"?"Contas por vencimento — receber, pagar e saldo previsto":"Movimentos pela data de pagamento e recebimento"} ({currency})</div>
        <div className="h-72" data-testid="cashflow-chart">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0F382C15" />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#0F382C99" }} />
              <YAxis tick={{ fontSize: 11, fill: "#0F382C99" }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => money(v)} contentStyle={{ borderRadius: 8, borderColor: "#0F382C22" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey={inKey} name={mode==="planned"?"A receber":"Recebido"} fill="#0F382C" radius={[4, 4, 0, 0]} />
              <Bar dataKey={outKey} name={mode==="planned"?"A pagar":"Pago"} fill="#D97706" radius={[4, 4, 0, 0]} />
              <Line type="monotone" dataKey={mode==="planned"?"cumulative":"cash_cumulative"} name="Acumulado" stroke="#9F1239" strokeWidth={2} dot={false} />
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
              <Tooltip formatter={(v) => money(v)} contentStyle={{ borderRadius: 8, borderColor: "#0F382C22" }} />
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
