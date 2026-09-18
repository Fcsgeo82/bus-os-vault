"use client";

import React, { useState, useEffect } from "react";
import {
  Bus,
  Database,
  RefreshCw,
  FolderGit2,
  Layers,
  CheckCircle,
  MessageSquare,
  FilePlus,
  Trash2,
  Pencil,
  Network,
} from "lucide-react";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { FilterBar, LineOption } from "@/components/filters/FilterBar";
import { NoteViewerModal } from "@/components/vault/NoteViewerModal";
import { DataEntryForm } from "@/components/entry/DataEntryForm";
import { OSCorrectionModal } from "@/components/entry/OSCorrectionModal";
import { LineFilterDropdown } from "@/components/hubs/LineFilterDropdown";
import VaultGraph from "@/components/vault/VaultGraph";
import { Toast, ToastData } from "@/components/ui/Toast";
import { RAGFilters, OSMestra } from "@/lib/types";

const HUB_PREVIEW_LIMIT = 24;

export default function Home() {
  const [activeTab, setActiveTab] = useState<"consulta" | "entrada" | "grafo">("consulta");
  const [filters, setFilters] = useState<RAGFilters>({
    apenas_vigentes: true,
    linhas: [],
    consorcios: [],
  });
  const [selectedNote, setSelectedNote] = useState<string | null>(null);
  const [correctingOs, setCorrectingOs] = useState<OSMestra | null>(null);
  const [osList, setOsList] = useState<OSMestra[]>([]);
  const [availableLines, setAvailableLines] = useState<LineOption[]>([]);
  const [availableConsorcios, setAvailableConsorcios] = useState<string[]>([]);
  const [hubLimitVisible, setHubLimitVisible] = useState(false);
  const [hubFilterLine, setHubFilterLine] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const pushToast = (type: "success" | "error", message: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  };

  const dismissToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleDeleteOs = async (os: OSMestra) => {
    const confirmed = window.confirm(
      `Excluir a Ordem de Serviço "${os.title}"?\n\nIsso removerá também as notas de eventos vinculadas, anexos e arquivos CSV.`
    );
    if (!confirmed) return;

    try {
      const res = await fetch(`/api/os/${os.uid}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        pushToast("success", data.message || `OS "${os.title}" excluída com sucesso.`);
        fetchOsList();
      } else {
        pushToast("error", data.detail || "Erro ao excluir a Ordem de Serviço.");
      }
    } catch (err) {
      console.error("Erro ao excluir OS:", err);
      pushToast("error", "Erro de conexão ao tentar excluir a Ordem de Serviço.");
    }
  };

  const fetchOsList = () => {
    fetch(`/api/os?t=${Date.now()}`)
      .then((res) => res.json())
      .then((data) => setOsList(data))
      .catch((err) => console.error("Erro ao carregar OS:", err));
  };

  useEffect(() => {
    fetchOsList();
    fetch("/api/os/lines/all")
      .then((res) => res.json())
      .then((data: { codigo: string; vista?: string; consorcio?: string }[]) => {
        setAvailableLines(
          data.map((d) => ({ codigo: String(d.codigo), vista: d.vista, consorcio: d.consorcio }))
        );
        const consorcios = Array.from(
          new Set(data.map((d) => String(d.consorcio ?? "")).filter(Boolean))
        ).sort();
        if (consorcios.length > 0) setAvailableConsorcios(consorcios);
      })
      .catch((err) => console.error("Erro ao carregar linhas:", err));
  }, []);

  const handleSyncVault = async () => {
    setSyncing(true);
    setSyncSuccess(false);
    try {
      const res = await fetch("/api/rag/sync", { method: "POST" });
      if (res.ok) {
        setSyncSuccess(true);
        fetchOsList();
        setTimeout(() => setSyncSuccess(false), 3000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSyncing(false);
    }
  };

  const handleEntrySuccess = (newOsTitle: string) => {
    fetchOsList();
    setActiveTab("consulta");
    setSelectedNote(newOsTitle);
  };

  const handleCorrectionSuccess = (message: string) => {
    setCorrectingOs(null);
    fetchOsList();
    pushToast("success", message);
  };

  const filteredHubs =
    hubFilterLine === null
      ? availableLines
      : availableLines.filter((l) => l.codigo === hubFilterLine);

  return (
    <main style={{ maxWidth: "1400px", margin: "0 auto", padding: "24px 20px" }}>
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
          paddingBottom: "18px",
          borderBottom: "1px solid var(--border-subtle)",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              background: "linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))",
              borderRadius: "14px",
              padding: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 20px rgba(56, 189, 248, 0.3)",
            }}
          >
            <Bus size={26} color="#fff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h1 style={{ fontSize: "1.45rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
                Bus OS Vault
              </h1>
              <span className="badge badge-vigente">v0.8.0</span>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
              Sistema de Gestão de Ordens de Serviço & Motor de Busca Híbrido RAG para Obsidian
            </p>
          </div>
        </div>

        {/* Abas de Navegação & Sincronização */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              background: "rgba(11, 15, 25, 0.8)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "4px",
              display: "flex",
              gap: "4px",
            }}
          >
            <button
              onClick={() => setActiveTab("consulta")}
              style={{
                background: activeTab === "consulta" ? "rgba(56, 189, 248, 0.18)" : "transparent",
                border: activeTab === "consulta" ? "1px solid var(--border-glow)" : "1px solid transparent",
                color: activeTab === "consulta" ? "var(--accent-cyan)" : "var(--text-secondary)",
                padding: "8px 14px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s",
              }}
            >
              <MessageSquare size={15} />
              Consulta & RAG
            </button>

            <button
              onClick={() => setActiveTab("entrada")}
              style={{
                background: activeTab === "entrada" ? "rgba(139, 92, 246, 0.18)" : "transparent",
                border: activeTab === "entrada" ? "1px solid rgba(139, 92, 246, 0.4)" : "1px solid transparent",
                color: activeTab === "entrada" ? "#c084fc" : "var(--text-secondary)",
                padding: "8px 14px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s",
              }}
            >
              <FilePlus size={15} />
              Nova Ordem de Serviço
            </button>

            <button
              onClick={() => setActiveTab("grafo")}
              style={{
                background: activeTab === "grafo" ? "rgba(16, 185, 129, 0.18)" : "transparent",
                border: activeTab === "grafo" ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid transparent",
                color: activeTab === "grafo" ? "#34d399" : "var(--text-secondary)",
                padding: "8px 14px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.2s",
              }}
            >
              <Network size={15} />
              Grafo do Cofre
            </button>
          </div>

          <button
            onClick={handleSyncVault}
            disabled={syncing}
            className="btn-secondary"
            title="Reindexar arquivos Markdown no LanceDB e BM25"
          >
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Sincronizando..." : syncSuccess ? "Indexado!" : "Sincronizar"}
            {syncSuccess && <CheckCircle size={14} color="#34d399" />}
          </button>
        </div>
      </header>

      {/* Conteúdo Dinâmico por Aba */}
      {activeTab === "grafo" ? (
        <section>
          <VaultGraph />
        </section>
      ) : activeTab === "entrada" ? (
        <section className="animate-fade-in">
          <DataEntryForm onSuccess={handleEntrySuccess} />
        </section>
      ) : (
        /* Aba de Consulta & Chat RAG */
        <div
          className="animate-fade-in"
          style={{
            display: "grid",
            gridTemplateColumns: "340px 1fr",
            gap: "24px",
            alignItems: "start",
          }}
        >
          {/* Painel Lateral Esquerdo (Acervo & OS) */}
          <aside style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Card de OS Registradas */}
            <div className="glass-panel" style={{ padding: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                <FolderGit2 size={16} style={{ color: "var(--accent-cyan)" }} />
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Ordens de Serviço</h3>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "320px", overflowY: "auto" }}>
                {osList.length === 0 ? (
                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Carregando OS do Vault...</p>
                ) : (
                  osList.map((os) => (
                    <div
                      key={os.uid}
                      onClick={() => setSelectedNote(os.title)}
                      style={{
                        background: "rgba(11, 15, 25, 0.6)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                        padding: "12px",
                        cursor: "pointer",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: "0" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                            {os.title}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setCorrectingOs(os);
                            }}
                            title={`Corrigir ${os.title}`}
                            aria-label={`Corrigir ${os.title}`}
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              padding: "2px",
                              display: "flex",
                              alignItems: "center",
                              borderRadius: "6px",
                              transition: "all 0.2s",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.color = "#fbbf24";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.color = "var(--text-muted)";
                            }}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteOs(os);
                            }}
                            title={`Excluir ${os.title}`}
                            aria-label={`Excluir ${os.title}`}
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              padding: "2px",
                              display: "flex",
                              alignItems: "center",
                              borderRadius: "6px",
                              transition: "all 0.2s",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.color = "#f87171";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.color = "var(--text-muted)";
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                        <span className={`badge ${os.status_vigencia === "Vigente" ? "badge-vigente" : "badge-retificada"}`}>
                          {os.status_vigencia}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "2px" }}>
                        <span>Processo: {os.processo_rio?.length ? os.processo_rio.join(", ") : "N/A"}</span>
                        <span>Vigência: a partir de {os.inicio_vigencia || "N/A"}</span>
                        {os.retifica_os && (
                          <span style={{ color: "#fbbf24" }}>Retifica: {os.retifica_os}</span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Card de Anexos Operacionais */}
            <div className="glass-panel" style={{ padding: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                <Database size={16} style={{ color: "var(--accent-purple)" }} />
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Anexos Operacionais</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.82rem" }}>
                <div
                  onClick={() => setSelectedNote("ANEXO_I_Viagens_Resumo")}
                  style={{
                    background: "rgba(11, 15, 25, 0.6)",
                    padding: "10px 12px",
                    borderRadius: "8px",
                    cursor: "pointer",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>ANEXO I — Viagens & Km</div>
                  <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Grade consolidada do estudo</div>
                </div>

                <div
                  onClick={() => setSelectedNote("ANEXO_II_Itinerarios")}
                  style={{
                    background: "rgba(11, 15, 25, 0.6)",
                    padding: "10px 12px",
                    borderRadius: "8px",
                    cursor: "pointer",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>ANEXO II — Itinerários Alternativos</div>
                  <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Desvios catalogados</div>
                </div>
              </div>
            </div>

            {/* Card de Hubs de Linhas */}
            <div className="glass-panel" style={{ padding: "18px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                <Layers size={16} style={{ color: "var(--accent-emerald)" }} />
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>Hubs de Linhas</h3>
                <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
                  {hubFilterLine !== null
                    ? `(${filteredHubs.length} de ${availableLines.length})`
                    : `(${availableLines.length})`}
                </span>
                <div style={{ marginLeft: "auto" }}>
                  <LineFilterDropdown
                    options={availableLines}
                    selected={hubFilterLine}
                    onChange={setHubFilterLine}
                  />
                </div>
              </div>
              {availableLines.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                  Nenhuma linha catalogada.
                </div>
              ) : filteredHubs.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                  Nenhuma linha corresponde ao filtro selecionado.
                </div>
              ) : (
                <>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {(hubLimitVisible ? filteredHubs : filteredHubs.slice(0, HUB_PREVIEW_LIMIT)).map((l) => (
                      <button
                        key={l.codigo}
                        onClick={() => setSelectedNote(`Linha ${l.codigo}`)}
                        className="btn-secondary"
                        style={{ fontSize: "0.78rem", padding: "4px 10px" }}
                      >
                        {l.codigo}
                      </button>
                    ))}
                  </div>
                  {filteredHubs.length > HUB_PREVIEW_LIMIT && (
                    <button
                      onClick={() => setHubLimitVisible((v) => !v)}
                      style={{
                        marginTop: "10px",
                        fontSize: "0.78rem",
                        color: "var(--accent-emerald)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                    >
                      {hubLimitVisible ? "Mostrar menos" : `Ver todas (${filteredHubs.length})`}
                    </button>
                  )}
                </>
              )}
            </div>
          </aside>

          {/* Painel Central (Filtros + Chat RAG) */}
          <section>
            <FilterBar
              filters={filters}
              onChange={setFilters}
              availableLines={availableLines}
              availableConsorcios={availableConsorcios}
            />
            <ChatContainer filters={filters} onOpenNote={(titulo) => setSelectedNote(titulo)} />
          </section>
        </div>
      )}

      {/* Drawer Lateral de Visualização de Notas */}
      <NoteViewerModal noteIdentifier={selectedNote} onClose={() => setSelectedNote(null)} />

      {/* Modal de Correção de OS */}
      {correctingOs && (
        <OSCorrectionModal os={correctingOs} onClose={() => setCorrectingOs(null)} onSuccess={handleCorrectionSuccess} />
      )}

      {/* Toasts */}
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={dismissToast} />
      ))}
    </main>
  );
}
