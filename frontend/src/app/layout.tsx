import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bus OS Vault — Inteligência de Transporte & RAG",
  description: "Painel de consulta semântica e gestão de Ordens de Serviço da rede de ônibus municipal via Obsidian Vault e RAG híbrido.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="bg-mesh" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
