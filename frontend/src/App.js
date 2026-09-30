import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LangProvider } from "@/i18n";
import { AuthProvider, useAuth } from "@/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Catalog from "@/pages/Catalog";
import Pipeline from "@/pages/Pipeline";
import TradeIntel from "@/pages/TradeIntel";
import Templates from "@/pages/Templates";
import Tasks from "@/pages/Tasks";
import Documents from "@/pages/Documents";
import Invoices from "@/pages/Invoices";
import Suppliers from "@/pages/Suppliers";
import Orders from "@/pages/Orders";
import Finance from "@/pages/Finance";
import Contracts from "@/pages/Contracts";
import Inventory from "@/pages/Inventory";

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
              <Route path="/" element={<Protected><Layout /></Protected>}>
                <Route index element={<Dashboard />} />
                <Route path="catalog" element={<Catalog />} />
                <Route path="pipeline" element={<Pipeline />} />
                <Route path="trade" element={<TradeIntel />} />
                <Route path="templates" element={<Templates />} />
                <Route path="tasks" element={<Tasks />} />
                <Route path="documents" element={<Documents />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="suppliers" element={<Suppliers />} />
                <Route path="orders" element={<Orders />} />
                <Route path="finance" element={<Finance />} />
                <Route path="contracts" element={<Contracts />} />
                <Route path="inventory" element={<Inventory />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </LangProvider>
      </AuthProvider>
    </div>
  );
}

export default App;
