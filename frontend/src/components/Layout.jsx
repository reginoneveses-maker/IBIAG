import { NavLink, Outlet } from "react-router-dom";
import { useLang } from "@/i18n";
import { LayoutDashboard, Package, Kanban, Globe2, Mail, CheckSquare, Leaf } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";

const Layout = () => {
  const { lang, setLang, t } = useLang();

  const links = [
    { to: "/", icon: LayoutDashboard, label: t("nav_dashboard"), testId: "nav-dashboard" },
    { to: "/catalog", icon: Package, label: t("nav_catalog"), testId: "nav-catalog" },
    { to: "/pipeline", icon: Kanban, label: t("nav_pipeline"), testId: "nav-pipeline" },
    { to: "/trade", icon: Globe2, label: t("nav_trade"), testId: "nav-trade" },
    { to: "/templates", icon: Mail, label: t("nav_templates"), testId: "nav-templates" },
    { to: "/tasks", icon: CheckSquare, label: t("nav_tasks"), testId: "nav-tasks" },
  ];

  return (
    <div className="min-h-screen bg-[#F9F6F0] grain-bg">
      <Toaster position="top-right" />
      <header className="sticky top-0 z-40 backdrop-blur-md bg-[#F9F6F0]/85 border-b border-[#0F382C]/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2.5" data-testid="app-logo">
            <div className="w-9 h-9 rounded-xl bg-[#0F382C] flex items-center justify-center">
              <Leaf className="w-5 h-5 text-amber-400" strokeWidth={2.2} />
            </div>
            <div className="leading-none">
              <div className="font-display font-extrabold text-[#0F382C] text-lg">{t("app_name")}</div>
              <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 hidden sm:block">CRM & Trade Intelligence</div>
            </div>
          </div>

          <div className="flex items-center gap-1 p-1 rounded-full border border-[#0F382C]/15 bg-white/70" data-testid="language-toggle">
            <button
              onClick={() => setLang("pt")}
              data-testid="lang-pt-button"
              className={`px-3 py-1 text-xs font-semibold rounded-full transition-all ${lang === "pt" ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70 hover:text-[#0F382C]"}`}
            >PT</button>
            <button
              onClick={() => setLang("en")}
              data-testid="lang-en-button"
              className={`px-3 py-1 text-xs font-semibold rounded-full transition-all ${lang === "en" ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70 hover:text-[#0F382C]"}`}
            >EN</button>
          </div>
        </div>
        <nav className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 flex gap-1 overflow-x-auto scrollbar-thin border-t border-[#0F382C]/5">
          {links.map(({ to, icon: Icon, label, testId }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              data-testid={testId}
              className={({ isActive }) =>
                `flex items-center gap-2 whitespace-nowrap px-3 sm:px-4 py-3 text-sm font-medium border-b-2 transition-all ${
                  isActive
                    ? "border-amber-600 text-[#0F382C]"
                    : "border-transparent text-[#0F382C]/60 hover:text-[#0F382C] hover:border-[#0F382C]/20"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <Outlet />
      </main>
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-xs font-mono-alt uppercase tracking-widest text-[#0F382C]/40 border-t border-[#0F382C]/10 mt-8">
        Brazil → World · Premium Tropical Ingredients
      </footer>
    </div>
  );
};

export default Layout;
