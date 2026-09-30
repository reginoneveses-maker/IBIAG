import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LangProvider } from "@/i18n";
import { AuthProvider, useAuth } from "@/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Catalog from "@/pages/Catalog";
import Pipeline from "@/pages/Pipeline";
import TradeIntel from "@/pages/TradeIntel";
import Templates from "@/pages/Templates";
import Tasks from "@/pages/Tasks";
import Orders from "@/pages/Orders";
import Inventory from "@/pages/Inventory";
import GestaoHome from "@/pages/gestao/GestaoHome";
import Procedimentos from "@/pages/gestao/Procedimentos";
import Financeiro from "@/pages/gestao/Financeiro";
import FornecedoresHub from "@/pages/gestao/FornecedoresHub";
import Specs from "@/pages/gestao/Specs";
import Precos from "@/pages/gestao/Precos";

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
                <Route index element={<GestaoHome />} />
                <Route path="procedimentos" element={<Procedimentos />} />
                <Route path="financeiro" element={<Financeiro />} />
                <Route path="fornecedores" element={<FornecedoresHub />} />
                <Route path="prospeccao" element={<Specs />} />
                <Route path="precos" element={<Precos />} />
              </Route>
              <Route path="/prospects" element={<Protected><Layout module="crm" /></Protected>}>
                <Route index element={<Dashboard />} />
                <Route path="catalog" element={<Catalog />} />
                <Route path="pipeline" element={<Pipeline />} />
                <Route path="trade" element={<TradeIntel />} />
                <Route path="templates" element={<Templates />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="orders" element={<Orders />} />
                <Route path="inventory" element={<Inventory />} />
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
