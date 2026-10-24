import type { Metadata } from "next";
import "./globals.css";
import RuntimeStatus from '@/components/exporthub/RuntimeStatus';
import {chatGPTSignInPath} from './chatgpt-auth';

export const metadata: Metadata = {
  title: "IBIAG | ExportHub",
  description: "Sistema interno IBIAG para acompanhamento de operações de comércio exterior.",
  icons: {
    icon: "/brand/ibiag-logo.png",
    shortcut: "/brand/ibiag-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased"><RuntimeStatus signInPath={chatGPTSignInPath('/')}/><noscript>Ative o JavaScript no navegador para cadastrar e editar registros. <a href="/produtos">Consultar produtos</a></noscript>{children}</body>
    </html>
  );
}
