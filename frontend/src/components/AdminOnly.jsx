import {Link} from "react-router-dom";
import {useAuth} from "@/AuthContext";

export default function AdminOnly({children}) {
  const {user} = useAuth();
  if (user?.role !== "admin") return <section role="alert" className="p-6 space-y-3">
    <h1 className="text-xl font-semibold">Acesso restrito</h1>
    <p>Esta área exige uma conta administrativa.</p>
    <Link to="/prospects" className="underline">Voltar ao CRM</Link>
  </section>;
  return children;
}
