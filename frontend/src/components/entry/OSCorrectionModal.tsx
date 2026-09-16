"use client";

import React, { useEffect, useState } from "react";
import { X, Save, CheckCircle, AlertCircle } from "lucide-react";
import { OSMestra } from "@/lib/types";

interface OSCorrectionModalProps {
  os: OSMestra;
  onClose: () => void;
  onSuccess: (message: string) => void;
}

const TIPO_OS_OPTIONS = ["Normal", "Retificada", "Temporária"];
const STATUS_OPTIONS = ["Vigente", "Revogada", "Substituída", "Sem Vigência"];

export const OSCorrectionModal: React.FC<OSCorrectionModalProps> = ({ os, onClose, onSuccess }) => {
  const [title, setTitle] = useState(os.title);
  const [tipoOs, setTipoOs] = useState(os.tipo_os || "Normal");
  const [statusVigencia, setStatusVigencia] = useState(os.status_vigencia || "Vigente");
  const [processoRio, setProcessoRio] = useState(os.processo_rio || "");
  const [despacho, setDespacho] = useState(os.despacho || "");
  const [dataPublicacao, setDataPublicacao] = useState(os.data_publicacao || "");
  const [inicioVigencia, setInicioVigencia] = useState(os.inicio_vigencia || "");
  const [fimVigencia, setFimVigencia] = useState(os.fim_vigencia || "");
  const [arquivoGtfs, setArquivoGtfs] = useState(os.arquivo_gtfs || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const buildPayload = () => {
    const payload: Record<string, string | null> = {
      title: title.trim() || null,
      tipo_os: tipoOs,
      status_vigencia: statusVigencia,
      processo_rio: processoRio.trim() || null,
      despacho: despacho.trim() || null,
      data_publicacao: dataPublicacao || null,
      inicio_vigencia: inicioVigencia || null,
      fim_vigencia: fimVigencia || null,
      arquivo_gtfs: arquivoGtfs.trim() || null,
    };
    return payload;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("O título da Ordem de Serviço não pode ficar vazio.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/os/${os.uid}/correct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload()),
      });

      const raw = await res.text();
      let data: any = null;
      try {
        data = raw ? JSON.parse(raw) : null;
      } catch {
        data = null;
      }

      if (!res.ok) {
        const detail = data?.detail || (raw ? `Erro ${res.status}: ${raw.slice(0, 300)}` : `Erro ${res.status} ao corrigir a OS.`);
        setError(detail);
        return;
      }

      onSuccess(data?.message || `Ordem de Serviço corrigida para "${title.trim()}" com sucesso.`);
    } catch (err: any) {
      setError(err.message || "Falha de conexão ao tentar corrigir a Ordem de Serviço.");
    } finally {
      setSubmitting(false);
    }
  };

  const fieldLabel: React.CSSProperties = {
    display: "block",
    fontSize: "0.78rem",
    color: "var(--text-secondary)",
    marginBottom: "5px",
    fontWeight: 600,
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(4, 6, 12, 0.7)",
        backdropFilter: "blur(6px)",
        zIndex: 90,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "680px",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "rgba(15, 20, 34, 0.98)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg, 16px)",
          boxShadow: "0 25px 60px rgba(0, 0, 0, 0.55)",
          animation: "fadeIn 0.2s ease-out",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700 }}>Corrigir Ordem de Serviço</h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Alterações de título propagam renomeações para eventos, hubs, anexos e CSVs.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Fechar"
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "22px", display: "flex", flexDirection: "column", gap: "16px" }}>
          {error && (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "10px",
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.35)",
                color: "#f87171",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label style={fieldLabel}>Título Oficial da OS *</label>
            <input
              type="text"
              className="input-glass"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={fieldLabel}>Tipo de OS</label>
              <select
                className="input-glass"
                value={tipoOs}
                onChange={(e) => setTipoOs(e.target.value)}
                style={{ background: "#111827", cursor: "pointer", width: "100%" }}
              >
                {TIPO_OS_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={fieldLabel}>Status de Vigência</label>
              <select
                className="input-glass"
                value={statusVigencia}
                onChange={(e) => setStatusVigencia(e.target.value)}
                style={{ background: "#111827", cursor: "pointer", width: "100%" }}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={fieldLabel}>Processo Administrativo (Processo.Rio)</label>
              <input
                type="text"
                className="input-glass"
                placeholder="000399.001631/2026-86"
                value={processoRio}
                onChange={(e) => setProcessoRio(e.target.value)}
              />
            </div>
            <div>
              <label style={fieldLabel}>Despacho Autorizativo</label>
              <input
                type="text"
                className="input-glass"
                placeholder="Despacho 0446149"
                value={despacho}
                onChange={(e) => setDespacho(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
            <div>
              <label style={fieldLabel}>Data de Publicação (D.O.)</label>
              <input
                type="date"
                className="input-glass"
                value={dataPublicacao}
                onChange={(e) => setDataPublicacao(e.target.value)}
              />
            </div>
            <div>
              <label style={fieldLabel}>Início da Vigência</label>
              <input
                type="date"
                className="input-glass"
                value={inicioVigencia}
                onChange={(e) => setInicioVigencia(e.target.value)}
              />
            </div>
            <div>
              <label style={fieldLabel}>Fim da Vigência</label>
              <input
                type="date"
                className="input-glass"
                value={fimVigencia}
                onChange={(e) => setFimVigencia(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label style={fieldLabel}>Arquivo GTFS Associado</label>
            <input
              type="text"
              className="input-glass"
              placeholder="0157_gtfs_set-26_1E.zip"
              value={arquivoGtfs}
              onChange={(e) => setArquivoGtfs(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "8px" }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: "10px 18px" }}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={submitting} style={{ padding: "10px 22px" }}>
              <Save size={16} />
              {submitting ? "Corrigindo & Sincronizando RAG..." : "Salvar Correção"}
            </button>
          </div>

          {title.trim() && title.trim() !== os.title && (
            <div
              style={{
                fontSize: "0.78rem",
                color: "#fbbf24",
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.2)",
                borderRadius: "8px",
                padding: "10px 12px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle size={14} />
              <span>
                O título mudará de "{os.title}" para "{title.trim()}"; eventos, hubs, anexos e CSVs vinculados serão
                renomeados automaticamente.
              </span>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};