import {Link} from "react-router-dom";
import {useAuth} from "@/AuthContext";
export const hasCommercialAccess=user=>user?.role==="admin"||(user?.role==="user"&&user?.commercial_profile==="commercial-operator-v1");
export default function CommercialOnly({children}){
 const {user}=useAuth();
 if(!hasCommercialAccess(user))return <section role="alert"><h1>Acesso restrito</h1><p>Esta área exige um perfil comercial autorizado.</p><Link to="/prospects">Voltar ao CRM</Link></section>;
 return children;
}
