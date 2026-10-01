import { NavLink, Outlet, Link } from "react-router-dom";
import { useLang } from "@/i18n";
import { useAuth } from "@/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import {
  LayoutDashboard, Package, Kanban, Globe2, Mail, CheckSquare, Leaf, ShoppingCart,
  Boxes, LogOut, ClipboardList, Wallet, Truck, FlaskConical, Calculator, LayoutGrid,
  Building2, Upload, ChevronRight, Home, Users, FileCheck2
} from "lucide-react";

const groups = (module, t) => module === "gestao"
  ? [
      { title: "Visão geral", items: [
        { to: "/gestao", icon: LayoutDashboard, label: "Painel", end: true },
      ]},
      { title: "Operação", items: [
        { to: "/gestao/procedimentos", icon: ClipboardList, label: "Procedimentos" },
        { to: "/gestao/financeiro", icon: Wallet, label: "Financeiro & NF" },
      ]},
      { title: "Fornecedores", items: [
        { to: "/gestao/fornecedores", icon: Truck, label: "Fornecedores", },
      ]},
      { title: "Produtos", items: [
        { to: "/gestao/produtos", icon: Package, label: "Produtos & dossiês" },
        { to: "/gestao/prospeccao", icon: FlaskConical, label: "Specs técnicas" },
        { to: "/gestao/precos", icon: Calculator, label: "Preços & calculadora" },
      ]},
    ]
  : [
      { title: "Visão geral", items: [
        { to: "/prospects", icon: LayoutDashboard, label: "Painel", end: true },
      ]},
      { title: "Produtos", items: [
        { to: "/prospects/catalog", icon: Package, label: "Catálogo" },
        { to: "/prospects/inventory", icon: Boxes, label: "Estoque" },
      ]},
      { title: "Prospecção", items: [
        { to: "/prospects/trade", icon: Globe2, label: "Trade Intelligence" },
        { to: "/prospects/import", icon: Upload, label: "Importar CRM" },
      ]},
      { title: "Vendas & CRM", items: [
        { to: "/prospects/pipeline", icon: Kanban, label: "Pipeline" },
        { to: "/prospects/tasks", icon: CheckSquare, label: "Tarefas" },
        { to: "/prospects/templates", icon: Mail, label: "Templates" },
        { to: "/prospects/orders", icon: ShoppingCart, label: "Pedidos" },
      ]},
    ];

const Layout = ({ module = "crm" }) => {
  const { lang, setLang, t } = useLang();
  const { user, logout } = useAuth();
  const navGroups = groups(module, t);

  const brand = module === "gestao"
    ? { name: "IBIAG", sub: "Gestão da empresa", Icon: Building2, bg: "bg-[#0F382C]", fg: "text-amber-400" }
    : { name: "Tropical Prospects", sub: "Compradores & CRM", Icon: Leaf, bg: "bg-amber-600", fg: "text-white" };

  return (
    <div className="min-h-screen bg-[#F6F7F4]">
      <Toaster position="top-right" />

      <aside className="hidden lg:flex fixed inset-y-0 left-0 z-40 w-64 bg-[#102F27] text-white flex-col">
        <div className="h-20 px-5 flex items-center border-b border-white/10">
          <Link to="/" className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${brand.bg} border border-white/10 flex items-center justify-center`}>
              <brand.Icon className={`w-5 h-5 ${brand.fg}`} />
            </div>
            <div>
              <div className="font-display font-extrabold text-lg leading-none">{brand.name}</div>
              <div className="text-[10px] uppercase tracking-widest text-white/45 mt-1">{brand.sub}</div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-5 space-y-6">
          {navGroups.map((group) => (
            <div key={group.title}>
              <div className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">{group.title}</div>
              <div className="space-y-1">
                {group.items.map(({ to, icon: Icon, label, end }) => (
                  <NavLink key={to} to={to} end={end}
                    className={({ isActive }) => `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${isActive ? "bg-white text-[#102F27] shadow-sm" : "text-white/65 hover:bg-white/8 hover:text-white"}`}>
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="flex-1">{label}</span>
                    <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-50" />
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-white/10 space-y-1">
          <Link to="/" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/60 hover:text-white hover:bg-white/8">
            <LayoutGrid className="w-4 h-4" /> Trocar módulo
          </Link>
          <button onClick={logout} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/60 hover:text-white hover:bg-white/8">
            <LogOut className="w-4 h-4" /> Sair
          </button>
        </div>
      </aside>

      <div className="lg:pl-64 min-h-screen">
        <header className="sticky top-0 z-30 h-16 bg-[#F6F7F4]/90 backdrop-blur-xl border-b border-[#102F27]/10">
          <div className="h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between">
            <div className="flex items-center gap-2 lg:hidden">
              <Link to="/" className="p-2 rounded-lg hover:bg-white text-[#102F27]"><LayoutGrid className="w-5 h-5" /></Link>
              <div className="font-display font-extrabold text-[#102F27]">{brand.name}</div>
            </div>
            <div className="hidden lg:flex items-center gap-2 text-xs text-[#102F27]/45">
              <Home className="w-3.5 h-3.5" />
              <span>{module === "gestao" ? "Gestão" : "Prospecção & CRM"}</span>
            </div>
            <div className="ml-auto flex items-center gap-3">
              <div className="flex items-center gap-1 p-1 rounded-full border border-[#102F27]/10 bg-white">
                <button onClick={() => setLang("pt")} className={`px-2.5 py-1 text-[11px] font-semibold rounded-full ${lang === "pt" ? "bg-[#102F27] text-white" : "text-[#102F27]/55"}`}>PT</button>
                <button onClick={() => setLang("en")} className={`px-2.5 py-1 text-[11px] font-semibold rounded-full ${lang === "en" ? "bg-[#102F27] text-white" : "text-[#102F27]/55"}`}>EN</button>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-[#102F27] text-white flex items-center justify-center text-xs font-bold">{(user?.name || user?.email || "U").slice(0,1).toUpperCase()}</div>
                <span className="text-xs font-medium text-[#102F27]/70 max-w-32 truncate">{user?.name || user?.email}</span>
              </div>
              <button onClick={logout} className="lg:hidden p-2 rounded-lg hover:bg-white text-[#102F27]"><LogOut className="w-4 h-4" /></button>
            </div>
          </div>
        </header>

        <main className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
