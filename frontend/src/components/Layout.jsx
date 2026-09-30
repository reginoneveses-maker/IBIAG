import { NavLink, Outlet, Link } from "react-router-dom";
import { useLang } from "@/i18n";
import { useAuth } from "@/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { LayoutDashboard, Package, Kanban, Globe2, Mail, CheckSquare, Leaf, ShoppingCart, Boxes, LogOut, ClipboardList, Wallet, Truck, FlaskConical, Calculator, LayoutGrid, Building2, Upload } from "lucide-react";

const Layout = ({ module = "crm" }) => {
  const { lang, setLang, t } = useLang();
  const { user, logout } = useAuth();

  const nav = module === "gestao" ? [
    { to: "/gestao", icon: LayoutDashboard, label: t("nav_g_home"), testId: "nav-g-home", end: true },
    { to: "/gestao/procedimentos", icon: ClipboardList, label: t("nav_g_procedures"), testId: "nav-g-procedures" },
    { to: "/gestao/financeiro", icon: Wallet, label: t("nav_g_finance"), testId: "nav-g-finance" },
    { to: "/gestao/fornecedores", icon: Truck, label: t("nav_g_suppliers"), testId: "nav-g-suppliers" },
    { to: "/gestao/prospeccao", icon: FlaskConical, label: t("nav_g_specs"), testId: "nav-g-specs" },
    { to: "/gestao/precos", icon: Calculator, label: t("nav_g_prices"), testId: "nav-g-prices" },
  ] : [
    { to: "/prospects", icon: LayoutDashboard, label: t("nav_dashboard"), testId: "nav-dashboard", end: true },
    { to: "/prospects/catalog", icon: Package, label: t("nav_catalog"), testId: "nav-catalog" },
    { to: "/prospects/pipeline", icon: Kanban, label: t("nav_pipeline"), testId: "nav-pipeline" },
    { to: "/prospects/trade", icon: Globe2, label: t("nav_trade"), testId: "nav-trade" },
    { to: "/prospects/templates", icon: Mail, label: t("nav_templates"), testId: "nav-templates" },
    { to: "/prospects/tasks", icon: CheckSquare, label: t("nav_tasks"), testId: "nav-tasks" },
    { to: "/prospects/orders", icon: ShoppingCart, label: t("nav_orders"), testId: "nav-orders" },
    { to: "/prospects/inventory", icon: Boxes, label: t("nav_inventory"), testId: "nav-inventory" },
    { to: "/prospects/import", icon: Upload, label: "Importar CRM", testId: "nav-import" },
  ];

  const brand = module === "gestao"
    ? { name: "IBIAG", sub: t("brand_gestao_sub"), Icon: Building2, bg: "bg-[#0F382C]", fg: "text-amber-400" }
    : { name: "Tropical Prospects", sub: t("brand_crm_sub"), Icon: Leaf, bg: "bg-amber-600", fg: "text-white" };

  return (
    <div className="min-h-screen bg-[#F9F6F0] grain-bg">
      <Toaster position="top-right" />
      <header className="sticky top-0 z-40 backdrop-blur-md bg-[#F9F6F0]/85 border-b border-[#0F382C]/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <Link to="/" data-testid="switch-module-button" title={t("switch_module")} className="p-2 rounded-lg hover:bg-[#EFECE6] text-[#0F382C]"><LayoutGrid className="w-5 h-5" /></Link>
            <div className="flex items-center gap-2.5" data-testid="app-logo">
              <div className={`w-9 h-9 rounded-xl ${brand.bg} flex items-center justify-center`}>
                <brand.Icon className={`w-5 h-5 ${brand.fg}`} strokeWidth={2.2} />
              </div>
              <div className="leading-none">
                <div className="font-display font-extrabold text-[#0F382C] text-lg">{brand.name}</div>
                <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 hidden sm:block">{brand.sub}</div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 p-1 rounded-full border border-[#0F382C]/15 bg-white/70" data-testid="language-toggle">
              <button onClick={() => setLang("pt")} data-testid="lang-pt-button" className={`px-3 py-1 text-xs font-semibold rounded-full ${lang === "pt" ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70"}`}>PT</button>
              <button onClick={() => setLang("en")} data-testid="lang-en-button" className={`px-3 py-1 text-xs font-semibold rounded-full ${lang === "en" ? "bg-[#0F382C] text-white" : "text-[#0F382C]/70"}`}>EN</button>
            </div>
            <div className="hidden md:block text-xs text-[#0F382C]/70" data-testid="user-name">{user?.name || user?.email}</div>
            <button onClick={logout} data-testid="logout-button" className="p-2 rounded-lg hover:bg-[#EFECE6] text-[#0F382C]"><LogOut className="w-4 h-4" /></button>
          </div>
        </div>
        <nav className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 flex gap-1 overflow-x-auto scrollbar-thin border-t border-[#0F382C]/5">
          {nav.map(({ to, icon: Icon, label, testId, end }) => (
            <NavLink key={to} to={to} end={end} data-testid={testId}
              className={({ isActive }) => `flex items-center gap-1.5 whitespace-nowrap px-2.5 sm:px-3 py-3 text-sm font-medium border-b-2 transition-all ${isActive ? "border-amber-600 text-[#0F382C]" : "border-transparent text-[#0F382C]/60 hover:text-[#0F382C]"}`}>
              <Icon className="w-4 h-4" />{label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
