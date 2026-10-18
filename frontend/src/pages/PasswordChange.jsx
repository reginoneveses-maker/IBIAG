import React, {useState} from "react";
import {useAuth} from "@/AuthContext";
import {toast} from "sonner";

export default function PasswordChange() {
  const {changePassword} = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    if (next !== confirmation) { toast.error("As novas senhas não coincidem."); return; }
    setBusy(true);
    try {
      await changePassword(current, next);
      toast.success("Senha alterada. Entre novamente com a nova senha.");
    } catch (error) {
      toast.error(error.response?.status === 429 ? "Limite de tentativas atingido. Aguarde antes de repetir." :
        "Não foi possível confirmar a alteração. Confira a senha atual ou entre novamente.");
    } finally { setCurrent(""); setNext(""); setConfirmation(""); setBusy(false); }
  }
  return <section className="max-w-lg space-y-5">
    <h1 className="text-2xl font-bold text-[#0F382C]">Alterar senha</h1>
    <p>A nova senha deve ter pelo menos 8 caracteres e até 72 bytes. Todas as sessões serão encerradas, incluindo esta.</p>
    <form onSubmit={submit} className="space-y-4">
      <label className="block">Senha atual<input className="block border rounded p-2 w-full" type="password" autoComplete="current-password" required maxLength={72} value={current} onChange={e=>setCurrent(e.target.value)}/></label>
      <label className="block">Nova senha<input className="block border rounded p-2 w-full" type="password" autoComplete="new-password" required minLength={8} maxLength={72} value={next} onChange={e=>setNext(e.target.value)}/></label>
      <label className="block">Confirmar nova senha<input className="block border rounded p-2 w-full" type="password" autoComplete="new-password" required minLength={8} maxLength={72} value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label>
      <button className="bg-[#0F382C] text-white rounded p-3" disabled={busy} type="submit">{busy ? "Alterando..." : "Alterar senha e encerrar sessões"}</button>
    </form>
  </section>;
}
