import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/AuthContext";
import { useAuth } from "@/AuthContext";
import { useLang } from "@/i18n";
import { Toaster } from "@/components/ui/sonner";
import { Building2, Leaf, ArrowRight, LogOut, AlertTriangle } from "lucide-react";
import { IbiagLogo } from "@/components/IbiagLogo";

export default function Home() {
  const { user, logout } = useAuth();
  const { lang, setLang, t } = useLang();
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/gestao/stats").then(r => setStats(r.data)).catch(() => {}); }, []);
  const alerts = (stats?.certs_expiring?.length || 0) + (stats?.certs_expired?.length || 0) + (stats?.contracts_expiring || 0);

  return (
    <div className="min-h-screen bg-[#F9F6F0] grain-bg" data-testid="home-page">
      <Toaster position="top-right" />
      <header className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <IbiagLogo className="w-40 h-auto" />
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 p-1 rounded-full border border-[#104496]/15 bg-white/70" data-testid="language-toggle">
            <button onClick={() => setLang("pt")} data-testid="lang-pt-button" className={`px-3 py-1 text-xs font-semibold rounded-full ${lang === "pt" ? "bg-[#104496] text-white" : "text-[#104496]/70"}`}>PT</button>
            <button onClick={() => setLang("en")} data-testid="lang-en-button" className={`px-3 py-1 text-xs font-semibold rounded-full ${lang === "en" ? "bg-[#104496] text-white" : "text-[#104496]/70"}`}>EN</button>
          </div>
          <span className="hidden sm:block text-xs text-[#104496]/70" data-testid="user-name">{user?.name || user?.email}</span>
          <button onClick={logout} data-testid="logout-button" className="p-2 rounded-lg hover:bg-[#EFECE6] text-[#104496]"><LogOut className="w-4 h-4" /></button>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 pt-10 pb-20">
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-[#104496] tracking-tight max-w-3xl">{t("home_title")}</h1>
        <p className="text-base md:text-lg text-[#104496]/70 mt-4 max-w-2xl">{t("home_subtitle")}</p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-12">
          <Link to="/gestao" data-testid="module-gestao" className="group relative overflow-hidden rounded-3xl bg-[#104496] text-white p-8 sm:p-10 min-h-[300px] flex flex-col justify-between hover:-translate-y-1 transition-transform">
            <div className="absolute -right-12 -top-12 w-56 h-56 rounded-full bg-[#CAD51B]/15 blur-2xl" />
            <div>
              <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center"><Building2 className="w-6 h-6 text-[#CAD51B]" /></div>
              <div className="mt-6 text-xs font-mono-alt uppercase tracking-[0.25em] text-[#CAD51B]/90">01 · {t("module_gestao_kicker")}</div>
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold mt-2">{t("module_gestao_title")}</h2>
              <p className="text-sm sm:text-base text-white/70 mt-3 max-w-md">{t("module_gestao_desc")}</p>
            </div>
            <div className="flex items-center justify-between mt-8">
              {alerts > 0 ? (
                <span data-testid="home-alerts-badge" className="inline-flex items-center gap-1.5 text-xs font-semibold bg-[#CAD51B] text-[#104496] px-3 py-1.5 rounded-full"><AlertTriangle className="w-3.5 h-3.5" />{alerts} {t("home_alerts")}</span>
              ) : <span className="text-xs text-white/50">{stats ? t("home_no_alerts") : ""}</span>}
              <span className="inline-flex items-center gap-2 text-sm font-semibold group-hover:gap-3 transition-all">{t("open")} <ArrowRight className="w-4 h-4" /></span>
            </div>
          </Link>

          <Link to="/prospects" data-testid="module-prospects" className="group relative overflow-hidden rounded-3xl bg-white border border-[#104496]/10 p-8 sm:p-10 min-h-[300px] flex flex-col justify-between hover:-translate-y-1 hover:border-[#104496]/40 transition-all">
            <div className="absolute -right-12 -bottom-12 w-56 h-56 rounded-full bg-[#104496]/5 blur-2xl" />
            <div>
              <div className="w-12 h-12 rounded-2xl bg-[#104496] flex items-center justify-center"><Leaf className="w-6 h-6 text-white" /></div>
              <div className="mt-6 text-xs font-mono-alt uppercase tracking-[0.25em] text-[#104496]">02 · {t("module_crm_kicker")}</div>
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold mt-2 text-[#104496]">Tropical Prospects</h2>
              <p className="text-sm sm:text-base text-[#104496]/70 mt-3 max-w-md">{t("module_crm_desc")}</p>
            </div>
            <div className="flex items-center justify-end mt-8 text-[#104496]">
              <span className="inline-flex items-center gap-2 text-sm font-semibold group-hover:gap-3 transition-all">{t("open")} <ArrowRight className="w-4 h-4" /></span>
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}
