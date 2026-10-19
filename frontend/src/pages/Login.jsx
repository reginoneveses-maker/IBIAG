import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowUpRight, LockKeyhole } from "lucide-react";
import { IbiagLogo } from "@/components/IbiagLogo";
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
    <div className="brand-login" data-testid="login-page">
      <Toaster position="top-right" />
      <aside className="brand-login-story" aria-label="IBIAG Ingredients: origem brasileira, conexões globais">
        <img className="brand-story-photo" src="/brand/ibiag-acai.jpg" alt="" aria-hidden="true" fetchPriority="high" />
        <div className="brand-story-shade" aria-hidden="true" />
        <div className="brand-story-chevron" aria-hidden="true" />
        <IbiagLogo tone="light" className="brand-story-logo" />
        <div className="brand-story-copy">
          <span className="brand-eyebrow brand-eyebrow-light">Origem brasileira. Conexões globais.</span>
          <h1>A riqueza do Brasil.<br />Conectada ao mundo.</h1>
          <p>Ingredientes, pessoas e oportunidades.<br />Uma operação conectada, da origem ao destino.</p>
          <div className="brand-story-signature"><span>IBIAG Ingredients</span><ArrowUpRight aria-hidden="true" size={22}/></div>
        </div>
      </aside>
      <main className="brand-login-panel">
        <div className="brand-login-form">
          <IbiagLogo className="brand-login-logo" />
          <div className="brand-login-heading">
            <span className="brand-eyebrow">ExportHub · Espaço de trabalho</span>
            <h2>Bem-vindo à IBIAG.</h2>
            <p>Entre para acompanhar seus negócios e conectar as próximas oportunidades.</p>
          </div>
          <form onSubmit={submit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input id="login-email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
                     data-testid="login-email-input" placeholder="seu.email@ibiag.com.br" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-password">Senha</Label>
              <Input id="login-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
                     data-testid="login-password-input" required />
            </div>
            <Button type="submit" disabled={busy} data-testid="login-submit-button" className="brand-login-submit">
              {busy ? "Entrando..." : "Entrar"}<ArrowUpRight aria-hidden="true" size={18}/>
            </Button>
          </form>
          <p className="brand-access-note"><LockKeyhole aria-hidden="true" size={14}/>Acesso exclusivo à equipe IBIAG.</p>
        </div>
        <footer className="brand-login-footer"><span>Brazilian ingredients. Global connections.</span><span>IBIAG · ExportHub</span></footer>
      </main>
    </div>
  );
};

export default Login;
