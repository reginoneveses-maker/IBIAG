import { NavLink, Outlet } from "react-router-dom";
import { useLang } from "@/i18n";
import { useAuth } from "@/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { LayoutDashboard, Package, Kanban, Globe2, Mail, CheckSquare, Leaf, FileText, Receipt, Truck, ShoppingCart, Wallet, FileSignature, Boxes, LogOut } from "lucide-react";

const Layout = () => {
  const { lang, setLang, t } = useLang();
  const { user, logout } = useAuth();

  const groups = [
    { title: t("nav_group_business"), items: [
      { to: "/", icon: LayoutDashboard, label: t("nav_dashboard"), testId: "nav-dashboard", end: true },
      { to: "/documents", icon: FileText, label: t("nav_documents"), testId: "nav-documents" },
      { to: "/invoices", icon: Receipt, label: t("nav_invoices"), testId: "nav-invoices" },
      { to: "/suppliers", icon: Truck, label: t("nav_suppliers"), testId: "nav-suppliers" },
      { to: "/orders", icon: ShoppingCart, label: t("nav_orders"), testId: "nav-orders" },
      { to: "/finance", icon: Wallet, label: t("nav_finance"), testId: "nav-finance" },
      { to: "/inventory", icon: Boxes, label: t("nav_inventory"), testId: "nav-inventory" },
      { to: "/contracts", icon: FileSignature, label: t("nav_contracts"), testId: "nav-contracts" },
    ]},
    { title: t("nav_group_crm"), items: [
      { to: "/catalog", icon: Package, label: t("nav_catalog"), testId: "nav-catalog" },
      { to: "/pipeline", icon: Kanban, label: t("nav_pipeline"), testId: "nav-pipeline" },
      { to: "/trade", icon: Globe2, label: t("nav_trade"), testId: "nav-trade" },
      { to: "/templates", icon: Mail, label: t("nav_templates"), testId: "nav-templates" },
      { to: "/tasks", icon: CheckSquare, label: t("nav_tasks"), testId: "nav-tasks" },
    ]},
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
              <div className="font-display font-extrabold text-[#0F382C] text-lg">AgroBrasil Export</div>
              <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60 hidden sm:block">ERP · CRM · Trade Intelligence</div>
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
        <nav className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 flex gap-4 overflow-x-auto scrollbar-thin border-t border-[#0F382C]/5">
          {groups.map((g, gi) => (
            <div key={gi} className="flex gap-1 items-center">
              <span className="text-[9px] font-mono-alt uppercase tracking-widest text-[#0F382C]/40 pl-1 pr-2 hidden lg:inline">{g.title}</span>
              {g.items.map(({ to, icon: Icon, label, testId, end }) => (
                <NavLink key={to} to={to} end={end} data-testid={testId}
                  className={({ isActive }) => `flex items-center gap-1.5 whitespace-nowrap px-2.5 sm:px-3 py-3 text-sm font-medium border-b-2 transition-all ${isActive ? "border-amber-600 text-[#0F382C]" : "border-transparent text-[#0F382C]/60 hover:text-[#0F382C]"}`}>
                  <Icon className="w-4 h-4" />{label}
                </NavLink>
              ))}
            </div>
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
