import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Leaf } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";

const Login = () => {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      nav("/");
    } catch (err) {
      const d = err.response?.data?.detail;
      toast.error(typeof d === "string" ? d : "Login falhou");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#F9F6F0] grain-bg flex items-center justify-center p-6">
      <Toaster position="top-right" />
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <div className="w-11 h-11 rounded-xl bg-[#0F382C] flex items-center justify-center">
            <Leaf className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <div className="font-display font-extrabold text-[#0F382C] text-xl">AgroBrasil Export</div>
            <div className="text-[10px] font-mono-alt uppercase tracking-widest text-[#0F382C]/60">ERP & CRM</div>
          </div>
        </div>
        <Card className="border-[#0F382C]/10 bg-white">
          <CardContent className="p-8">
            <h1 className="font-display text-2xl font-bold text-[#0F382C] mb-2">Entrar</h1>
            <p className="text-sm text-[#0F382C]/70 mb-6">Acesse o sistema de gestão da sua empresa</p>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <Label>Email</Label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                       data-testid="login-email-input" required />
              </div>
              <div>
                <Label>Senha</Label>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                       data-testid="login-password-input" required />
              </div>
              <Button type="submit" disabled={busy} data-testid="login-submit-button"
                      className="w-full bg-[#0F382C] hover:bg-[#0A2920] text-white">
                {busy ? "Entrando..." : "Entrar"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
