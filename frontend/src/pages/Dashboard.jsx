import { useEffect, useState } from "react";
import { api, fmtUSD } from "@/lib/api";
import { useLang } from "@/i18n";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Package, DollarSign, TrendingUp, Trophy, XCircle } from "lucide-react";

const Dashboard = () => {
  const { t } = useLang();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/dashboard/stats").then(r => setStats(r.data)).catch(() => {});
  }, []);

  const kpis = [
    { key: "kpi_active_leads", testId: "kpi-active-leads", value: stats?.active_leads ?? 0, icon: Users, tone: "text-blue-600 bg-blue-50" },
    { key: "kpi_pipeline_value", testId: "kpi-pipeline-value", value: fmtUSD(stats?.pipeline_value ?? 0), icon: DollarSign, tone: "text-amber-700 bg-amber-50" },
    { key: "kpi_samples_sent", testId: "kpi-samples-sent", value: stats?.samples_sent ?? 0, icon: Package, tone: "text-purple-700 bg-purple-50" },
    { key: "kpi_conversion", testId: "kpi-conversion", value: `${stats?.conversion_rate ?? 0}%`, icon: TrendingUp, tone: "text-emerald-700 bg-emerald-50" },
  ];

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <div>
        <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-[#0F382C]/60 mb-2">
          Brazil → World
        </div>
        <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F382C] tracking-tight">
          {t("app_name")}
        </h1>
        <p className="text-base sm:text-lg text-[#0F382C]/70 mt-2 max-w-2xl">{t("tagline")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {kpis.map(({ key, testId, value, icon: Icon, tone }) => (
          <Card key={key} data-testid={testId} className="border-[#0F382C]/10 bg-white/90 hover:-translate-y-0.5 transition-transform">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tone}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-4">
                <div className="text-[11px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">{t(key)}</div>
                <div className="mt-1 font-display text-2xl sm:text-3xl font-bold text-[#0F382C]">{value}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-[#0F382C]/10 bg-white/90" data-testid="by-stage-card">
          <CardHeader>
            <CardTitle className="font-display text-[#0F382C]">{t("by_stage")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {["new_lead", "initial_contact", "sample_sent", "negotiation", "closed_won", "closed_lost"].map(s => {
              const count = stats?.by_stage?.[s] || 0;
              const total = Object.values(stats?.by_stage || {}).reduce((a, b) => a + b, 0) || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={s} data-testid={`stage-row-${s}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-[#0F382C]/80">{t(`stage_${s}`)}</span>
                    <span className="font-mono-alt text-[#0F382C]">{count}</span>
                  </div>
                  <div className="h-1.5 bg-[#EFECE6] rounded-full overflow-hidden">
                    <div className="h-full bg-[#0F382C]" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card className="border-[#0F382C]/10 bg-white/90" data-testid="by-industry-card">
          <CardHeader>
            <CardTitle className="font-display text-[#0F382C]">{t("by_industry")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {["beverage", "cosmetics", "food_service", "distributor"].map(i => {
              const count = stats?.by_industry?.[i] || 0;
              const total = Object.values(stats?.by_industry || {}).reduce((a, b) => a + b, 0) || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={i} data-testid={`industry-row-${i}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-[#0F382C]/80">{t(`industry_${i}`)}</span>
                    <span className="font-mono-alt text-[#0F382C]">{count}</span>
                  </div>
                  <div className="h-1.5 bg-[#EFECE6] rounded-full overflow-hidden">
                    <div className="h-full bg-amber-600" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white/80 border border-[#0F382C]/10" data-testid="kpi-total-leads">
          <div className="text-[11px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">{t("kpi_total_leads")}</div>
          <div className="mt-1 font-display text-2xl font-bold text-[#0F382C]">{stats?.total_leads ?? 0}</div>
        </div>
        <div className="p-4 rounded-xl bg-white/80 border border-[#0F382C]/10" data-testid="kpi-won">
          <div className="flex items-center gap-1 text-[11px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60"><Trophy className="w-3 h-3" />{t("kpi_won")}</div>
          <div className="mt-1 font-display text-2xl font-bold text-emerald-700">{stats?.won ?? 0}</div>
        </div>
        <div className="p-4 rounded-xl bg-white/80 border border-[#0F382C]/10" data-testid="kpi-lost">
          <div className="flex items-center gap-1 text-[11px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60"><XCircle className="w-3 h-3" />{t("kpi_lost")}</div>
          <div className="mt-1 font-display text-2xl font-bold text-rose-600">{stats?.lost ?? 0}</div>
        </div>
        <div className="p-4 rounded-xl bg-[#0F382C] border border-[#0F382C]" data-testid="kpi-samples">
          <div className="text-[11px] font-mono-alt uppercase tracking-widest text-amber-300">{t("kpi_samples_sent")}</div>
          <div className="mt-1 font-display text-2xl font-bold text-white">{stats?.samples_sent ?? 0}</div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
