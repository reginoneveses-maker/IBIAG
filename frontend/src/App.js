import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LangProvider } from "@/i18n";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Catalog from "@/pages/Catalog";
import Pipeline from "@/pages/Pipeline";
import TradeIntel from "@/pages/TradeIntel";
import Templates from "@/pages/Templates";
import Tasks from "@/pages/Tasks";

function App() {
  return (
    <div className="App">
      <LangProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="catalog" element={<Catalog />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="trade" element={<TradeIntel />} />
              <Route path="templates" element={<Templates />} />
              <Route path="tasks" element={<Tasks />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </LangProvider>
    </div>
  );
}

export default App;
