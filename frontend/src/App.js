import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LangProvider } from "@/i18n";
import { AuthProvider, useAuth } from "@/AuthContext";
import AdminOnly from "@/components/AdminOnly";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Catalog from "@/pages/Catalog";
import Pipeline from "@/pages/Pipeline";
import TradeIntel from "@/pages/TradeIntel";
import Templates from "@/pages/Templates";
import Tasks from "@/pages/Tasks";
import AccountAccess from "@/pages/AccountAccess";
import PasswordChange from "@/pages/PasswordChange";
import Orders from "@/pages/Orders";
import Operations from "@/pages/gestao/Operations";
import PackingLists from "@/pages/gestao/PackingLists";
import CommercialInvoices from "@/pages/gestao/CommercialInvoices";
import Quotations from "@/pages/gestao/Quotations";
import Shipments from "@/pages/gestao/Shipments";
import Samples from "@/pages/gestao/Samples";
import Quality from "@/pages/gestao/Quality";
import Inventory from "@/pages/Inventory";
import ImportCRM from "@/pages/ImportCRM";
import GestaoHome from "@/pages/gestao/GestaoHome";
import Procedimentos from "@/pages/gestao/Procedimentos";
import Financeiro from "@/pages/gestao/Financeiro";
import FornecedoresHub from "@/pages/gestao/FornecedoresHub";
import Specs from "@/pages/gestao/Specs";
import Produtos from "@/pages/gestao/Produtos";
import Precos from "@/pages/gestao/Precos";
import Documentos from "@/pages/gestao/Documentos";

const Protected = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-[#0F382C]">Carregando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <LangProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Protected><Home /></Protected>} />
              <Route path="/gestao" element={<Protected><Layout module="gestao" /></Protected>}>
                <Route path="acessos" element={<AdminOnly><AccountAccess /></AdminOnly>} />
                <Route index element={<AdminOnly><GestaoHome /></AdminOnly>} />
                <Route path="procedimentos" element={<Procedimentos />} />
                <Route path="financeiro" element={<AdminOnly><Financeiro /></AdminOnly>} />
                <Route path="fornecedores" element={<AdminOnly><FornecedoresHub /></AdminOnly>} />
                <Route path="produtos" element={<AdminOnly><Produtos /></AdminOnly>} />
                <Route path="prospeccao" element={<AdminOnly><Specs /></AdminOnly>} />
                <Route path="precos" element={<AdminOnly><Precos /></AdminOnly>} />
                <Route path="documentos" element={<Documentos />} />
                <Route path="operacao" element={<AdminOnly><Operations /></AdminOnly>} />
                <Route path="packing-lists" element={<AdminOnly><PackingLists /></AdminOnly>} />
                <Route path="invoices-comerciais" element={<AdminOnly><CommercialInvoices /></AdminOnly>} />
                <Route path="cotacoes" element={<AdminOnly><Quotations /></AdminOnly>} />
                <Route path="embarques" element={<AdminOnly><Shipments /></AdminOnly>} />
                <Route path="qualidade" element={<AdminOnly><Quality /></AdminOnly>} />
                <Route path="amostras" element={<AdminOnly><Samples /></AdminOnly>} />
                <Route path="pedidos" element={<AdminOnly><Orders /></AdminOnly>} />
                <Route path="estoque" element={<AdminOnly><Inventory /></AdminOnly>} />
              </Route>
              <Route path="/prospects" element={<Protected><Layout module="crm" /></Protected>}>
                <Route path="senha" element={<PasswordChange />} />
                <Route index element={<Dashboard />} />
                <Route path="catalog" element={<Catalog />} />
                <Route path="pipeline" element={<Pipeline />} />
                <Route path="trade" element={<TradeIntel />} />
                <Route path="templates" element={<Templates />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="orders" element={<AdminOnly><Orders /></AdminOnly>} />
                <Route path="inventory" element={<AdminOnly><Inventory /></AdminOnly>} />
                <Route path="import" element={<ImportCRM />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </LangProvider>
      </AuthProvider>
    </div>
  );
}

export default App;
