import React, {useEffect, useState} from "react";
import {api} from "@/lib/api";
import {useAuth} from "@/AuthContext";
import {toast} from "sonner";

export default function AccountAccess() {
  const {user} = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    if (user?.role !== "admin") return;
    api.get("/auth/users").then(r => { if (active) setAccounts(r.data); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user?.role]);
  async function change(account) {
    setBusy(true);
    try {
      const r = await api.patch(`/auth/users/${encodeURIComponent(account.id)}/active`, {active: account.active === false});
      setAccounts(rows => rows.map(row => row.id === account.id ? r.data : row));
      setConfirm(null);
      toast.success(r.data.active ? "Conta reativada. É necessário entrar novamente." : "Conta suspensa. Sessões encerradas.");
    } catch { toast.error("Não foi possível alterar o acesso. Tente novamente."); }
    finally { setBusy(false); }
  }
  if (user?.role !== "admin") return <p>Acesso restrito à administração.</p>;
  return <section className="space-y-5 max-w-4xl">
    <h1 className="text-2xl font-bold text-[#0F382C]">Acesso da equipe</h1>
    <p>Suspender bloqueia novos acessos e encerra as sessões da conta. Os dados e responsáveis são preservados. Reativar exige um novo login.</p>
    {loading && <p>Carregando contas...</p>}
    {error && <p role="alert">Não foi possível carregar as contas. Reabra esta página para tentar novamente.</p>}
    <ul className="space-y-3">{accounts.map(account => <li key={account.id} className="bg-white border rounded-xl p-4 space-y-2">
      <div className="font-semibold">{account.name || account.email}</div>
      <div>{account.email} · {account.role === "admin" ? "Administrador" : "Usuário"} · {account.active === false ? "Suspensa" : "Ativa"}</div>
      {account.role === "user" && account.id !== user.id && (confirm === account.id ? <div className="space-x-3">
        <span>{account.active === false ? "Reativar esta conta?" : "Suspender esta conta e encerrar suas sessões?"}</span>
        <button className="underline" disabled={busy} onClick={() => change(account)}>{account.active === false ? "Confirmar reativação" : "Confirmar suspensão"}</button>
        <button disabled={busy} onClick={() => setConfirm(null)}>Cancelar</button>
      </div> : <button className="underline" disabled={busy} onClick={() => setConfirm(account.id)}>{account.active === false ? "Reativar conta" : "Suspender conta"}</button>)}
    </li>)}</ul>
  </section>;
}
