"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Bot, User, Loader2 } from "lucide-react";
import { ChatMessage, RAGFilters, RAGSource } from "@/lib/types";
import { SourceCard } from "./SourceCard";

interface ChatContainerProps {
  filters: RAGFilters;
  onOpenNote: (titulo: string) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ filters, onOpenNote }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Olá! Sou o assistente do **Bus OS Vault**. Você pode me consultar sobre ordens de serviço, alterações operacionais, viagens planejadas e desvios de itinerários da rede de ônibus.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedQueries = [
    "Quais desvios de itinerário existem para a linha 104?",
    "O que foi alterado na linha 006 pelo segundo estudo?",
    "Quais linhas utilizam o Túnel Santa Bárbara como alternativa?",
    "Qual a vigência e processo da OS 2026.08?",
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: "user",
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!queryText) setInput("");
    setLoading(true);

    try {
      const response = await fetch("/api/rag/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: textToSend.trim(),
          history: messages.slice(-4).map((m) => ({ role: m.role, content: m.content })),
          filters: filters,
        }),
      });

      if (!response.ok) {
        throw new Error("Falha na comunicação com o motor RAG.");
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        id: `ast-${Date.now()}`,
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `⚠️ Não foi possível obter a resposta do RAG: ${err.message || "Erro desconhecido"}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="glass-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "640px",
        overflow: "hidden",
      }}
    >
      {/* Header do Chat */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          background: "rgba(15, 23, 42, 0.4)",
        }}
      >
        <div
          style={{
            background: "linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))",
            borderRadius: "8px",
            width: "32px",
            height: "32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
          }}
        >
          <Sparkles size={18} />
        </div>
        <div>
          <h2 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Consulta Semântica RAG</h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Indexação em LanceDB & BM25 com síntese via Gemini Flash
          </p>
        </div>
      </div>

      {/* Lista de Mensagens */}
      <div style={{ flex: 1, padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
        {messages.map((m) => (
          <div
            key={m.id}
            className="animate-fade-in"
            style={{
              display: "flex",
              gap: "12px",
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: m.role === "user" ? "80%" : "90%",
            }}
          >
            {m.role === "assistant" && (
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  background: "rgba(56, 189, 248, 0.15)",
                  border: "1px solid rgba(56, 189, 248, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent-cyan)",
                  flexShrink: 0,
                  marginTop: "2px",
                }}
              >
                <Bot size={18} />
              </div>
            )}

            <div style={{ flex: 1 }}>
              <div
                style={{
                  background:
                    m.role === "user"
                      ? "linear-gradient(135deg, rgba(37, 99, 235, 0.8), rgba(56, 189, 248, 0.8))"
                      : "rgba(22, 30, 48, 0.8)",
                  border: `1px solid ${m.role === "user" ? "transparent" : "var(--border-subtle)"}`,
                  borderRadius: m.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                  padding: "14px 18px",
                  color: "var(--text-primary)",
                  fontSize: "0.92rem",
                  lineHeight: 1.55,
                  boxShadow: m.role === "user" ? "0 4px 14px rgba(37, 99, 235, 0.25)" : "none",
                }}
              >
                <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>

                {/* Fontes Citadas */}
                {m.sources && m.sources.length > 0 && (
                  <div style={{ marginTop: "14px", paddingTop: "10px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                      Fontes do Vault Consultadas ({m.sources.length}):
                    </span>
                    <div>
                      {m.sources.map((s, idx) => (
                        <SourceCard key={idx} source={s} onOpenNote={onOpenNote} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "var(--text-muted)",
                  marginTop: "4px",
                  display: "block",
                  textAlign: m.role === "user" ? "right" : "left",
                }}
              >
                {m.timestamp}
              </span>
            </div>

            {m.role === "user" && (
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  background: "rgba(255, 255, 255, 0.1)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-primary)",
                  flexShrink: 0,
                  marginTop: "2px",
                }}
              >
                <User size={18} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: "10px", alignItems: "center", color: "var(--accent-cyan)", fontSize: "0.85rem" }}>
            <Loader2 size={18} className="animate-spin" />
            <span>Consultando acervo de OS e formulando resposta...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sugestões de Perguntas */}
      {messages.length <= 2 && (
        <div style={{ padding: "0 20px 12px 20px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {suggestedQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              className="btn-secondary"
              style={{ fontSize: "0.78rem", borderRadius: "20px" }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input de Mensagem */}
      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          gap: "10px",
          background: "rgba(11, 15, 25, 0.5)",
        }}
      >
        <input
          type="text"
          className="input-glass"
          placeholder="Pergunte sobre itinerários, viagens, linhas ou vigências..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={loading}
        />
        <button
          className="btn-primary"
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          style={{ padding: "0 20px" }}
        >
          <Send size={16} />
          Enviar
        </button>
      </div>
    </div>
  );
};
