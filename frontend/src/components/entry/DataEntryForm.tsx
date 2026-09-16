"use client";

import React, { useState, useEffect } from "react";
import { Plus, Trash2, Upload, CheckCircle, AlertCircle, FileSpreadsheet, Send, FileText, ChevronRight } from "lucide-react";
import { OSMestra } from "@/lib/types";

interface EventoForm {
  title: string;
  tipo_evento: "Inclusão" | "Remoção" | "Ajuste" | "Correção/Retificação";
  objeto_afetado: string[];
  linhas_afetadas: string;
  consorcios: string[];
  vigencia_inicio: string;
  vigencia_fim: string;
  descricao: string;
  justificativa: string;
}

interface DataEntryFormProps {
  onSuccess: (osTitle: string) => void;
}

export const DataEntryForm: React.FC<DataEntryFormProps> = ({ onSuccess }) => {
  // Dados Mestre da OS
  const [title, setTitle] = useState("");
  const [tipoOs, setTipoOs] = useState<"Normal" | "Retificada" | "Temporária">("Normal");
  const [statusVigencia, setStatusVigencia] = useState<"Vigente" | "Sem Vigência">("Vigente");
  const [anoMes, setAnoMes] = useState("2026/10");
  const [processoRio, setProcessoRio] = useState("");
  const [despacho, setDespacho] = useState("");
  const [dataPublicacao, setDataPublicacao] = useState("");
  const [inicioVigencia, setInicioVigencia] = useState("");
  const [fimVigencia, setFimVigencia] = useState("");
  const [semFimVigencia, setSemFimVigencia] = useState(true);
  const [arquivoGtfs, setArquivoGtfs] = useState("");
  const [retificaOs, setRetificaOs] = useState("");

  // Arquivos CSV
  const [anexoIFile, setAnexoIFile] = useState<File | null>(null);
  const [anexoIIFile, setAnexoIIFile] = useState<File | null>(null);

  // Lista de Notas de Evento
  const [eventos, setEventos] = useState<EventoForm[]>([
    {
      title: "",
      tipo_evento: "Inclusão",
      objeto_afetado: ["Linhas/Serviços"],
      linhas_afetadas: "",
      consorcios: ["Intersul"],
      vigencia_inicio: "",
      vigencia_fim: "",
      descricao: "",
      justificativa: "",
    },
  ]);

  // Lista de OS existentes para vincular retificação
  const [existingOs, setExistingOs] = useState<OSMestra[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    fetch("/api/os")
      .then((res) => res.json())
      .then((data) => setExistingOs(data))
      .catch(() => {});
  }, []);

  const handleAddEvento = () => {
    setEventos((prev) => [
      ...prev,
      {
        title: "",
        tipo_evento: "Ajuste",
        objeto_afetado: ["Planejamento de Viagens"],
        linhas_afetadas: "",
        consorcios: ["Intersul"],
        vigencia_inicio: inicioVigencia,
        vigencia_fim: "",
        descricao: "",
        justificativa: "",
      },
    ]);
  };

  const handleRemoveEvento = (index: number) => {
    setEventos((prev) => prev.filter((_, i) => i !== index));
  };

  const handleEventoChange = (index: number, field: keyof EventoForm, value: any) => {
    setEventos((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const toggleConsorcioInEvento = (index: number, consorcio: string) => {
    setEventos((prev) => {
      const copy = [...prev];
      const curr = copy[index].consorcios;
      copy[index].consorcios = curr.includes(consorcio)
        ? curr.filter((c) => c !== consorcio)
        : [...curr, consorcio];
      return copy;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setStatusMsg({ type: "error", text: "Preencha o título oficial da Ordem de Serviço." });
      return;
    }

    setSubmitting(true);
    setStatusMsg(null);

    try {
      const formattedEventos = eventos
        .filter((ev) => ev.title.trim().length > 0)
        .map((ev) => ({
          title: ev.title.trim(),
          tipo_evento: ev.tipo_evento,
          objeto_afetado: ev.objeto_afetado,
          linhas_afetadas: ev.linhas_afetadas
            .split(/[,;\s]+/)
            .map((s) => s.trim())
            .filter(Boolean),
          consorcios: ev.consorcios,
          vigencia_inicio: ev.vigencia_inicio || inicioVigencia || null,
          vigencia_fim: ev.vigencia_fim || null,
          descricao: ev.descricao || `Alteração referente a ${ev.title}`,
          justificativa: ev.justificativa || null,
        }));

      const payloadData = {
        title: title.trim(),
        tipo_os: tipoOs,
        status_vigencia: statusVigencia,
        ano_mes_referencia: anoMes.trim(),
        processo_rio: processoRio.trim() || null,
        despacho: despacho.trim() || null,
        data_publicacao: dataPublicacao || null,
        inicio_vigencia: inicioVigencia || null,
        fim_vigencia: semFimVigencia ? null : fimVigencia || null,
        arquivo_gtfs: arquivoGtfs.trim() || null,
        retifica_os: retificaOs ? `[[${retificaOs}]]` : null,
        notas_eventos: formattedEventos,
      };

      const formData = new FormData();
      formData.append("payload", JSON.stringify(payloadData));

      if (anexoIFile) {
        formData.append("anexo_i", anexoIFile);
      }
      if (anexoIIFile) {
        formData.append("anexo_ii", anexoIIFile);
      }

      const res = await fetch("/api/os/ingest", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const raw = await res.text();
        let detail = `Erro ${res.status} ao processar ingestão${res.statusText ? ` (${res.statusText})` : ""}.`;
        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            detail = parsed.detail || detail;
          } catch {
            detail = `${detail} ${raw.slice(0, 300)}`;
          }
        }
        throw new Error(detail);
      }

      const successText = await res.text();
      let message = "Ordem de Serviço salva com sucesso.";
      if (successText) {
        try {
          const parsed = JSON.parse(successText);
          message = parsed.message || message;
        } catch {
          // Corpo não-JSON: mantém a mensagem padrão de sucesso.
        }
      }
      setStatusMsg({ type: "success", text: message });
      setTimeout(() => {
        onSuccess(title.trim());
      }, 1500);
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Falha na submissão." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {statusMsg && (
        <div
          className="animate-fade-in"
          style={{
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            background: statusMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            border: `1px solid ${statusMsg.type === "success" ? "rgba(16, 185, 129, 0.4)" : "rgba(239, 68, 68, 0.4)"}`,
            color: statusMsg.type === "success" ? "#34d399" : "#f87171",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "0.9rem",
          }}
        >
          {statusMsg.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* 1. Metadados Mestre da OS */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
          <FileText size={20} style={{ color: "var(--accent-cyan)" }} />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>1. Identificação Oficial da Ordem de Serviço</h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "16px", marginBottom: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Título Oficial da OS *
            </label>
            <input
              type="text"
              className="input-glass"
              placeholder="Ex: 175 - OS 2026.09 - Setembro 1º Estudo"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Ano / Mês de Ref. *
            </label>
            <input
              type="text"
              className="input-glass"
              placeholder="2026/09"
              value={anoMes}
              onChange={(e) => setAnoMes(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Tipo de OS
            </label>
            <select
              className="input-glass"
              value={tipoOs}
              onChange={(e: any) => setTipoOs(e.target.value)}
              style={{ background: "#111827", cursor: "pointer" }}
            >
              <option value="Normal">Normal</option>
              <option value="Retificada">Retificada</option>
              <option value="Temporária">Temporária</option>
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", marginBottom: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Processo Administrativo (Processo.Rio)
            </label>
            <input
              type="text"
              className="input-glass"
              placeholder="000399.001631/2026-86"
              value={processoRio}
              onChange={(e) => setProcessoRio(e.target.value)}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Despacho Autorizativo
            </label>
            <input
              type="text"
              className="input-glass"
              placeholder="Despacho 0446149"
              value={despacho}
              onChange={(e) => setDespacho(e.target.value)}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Arquivo GTFS Associado
            </label>
            <input
              type="text"
              className="input-glass"
              placeholder="175_gtfs_set-26_1E.zip"
              value={arquivoGtfs}
              onChange={(e) => setArquivoGtfs(e.target.value)}
            />
          </div>
        </div>

        {/* Datas de Vigência */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", marginBottom: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Data de Publicação (D.O.)
            </label>
            <input
              type="date"
              className="input-glass"
              value={dataPublicacao}
              onChange={(e) => setDataPublicacao(e.target.value)}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600 }}>
              Início da Vigência
            </label>
            <input
              type="date"
              className="input-glass"
              value={inicioVigencia}
              onChange={(e) => setInicioVigencia(e.target.value)}
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ fontSize: "0.82rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                Fim da Vigência
              </label>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}>
                <input
                  type="checkbox"
                  checked={semFimVigencia}
                  onChange={(e) => setSemFimVigencia(e.target.checked)}
                />
                Sem vigência final
              </label>
            </div>
            <input
              type="date"
              className="input-glass"
              value={fimVigencia}
              onChange={(e) => setFimVigencia(e.target.value)}
              disabled={semFimVigencia}
              style={{ opacity: semFimVigencia ? 0.4 : 1 }}
            />
          </div>
        </div>

        {/* Rastreabilidade de Retificação */}
        {tipoOs === "Retificada" && (
          <div style={{ marginTop: "12px", padding: "12px", background: "rgba(245, 158, 11, 0.08)", borderRadius: "8px", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
            <label style={{ display: "block", fontSize: "0.82rem", color: "#fbbf24", marginBottom: "6px", fontWeight: 600 }}>
              Qual Ordem de Serviço anterior esta versão retifica?
            </label>
            <select
              className="input-glass"
              value={retificaOs}
              onChange={(e) => setRetificaOs(e.target.value)}
              style={{ background: "#111827", cursor: "pointer" }}
            >
              <option value="">Selecione a OS a ser retificada...</option>
              {existingOs.map((os) => (
                <option key={os.uid} value={os.title}>
                  {os.title} ({os.status_vigencia})
                </option>
              ))}
            </select>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
              Ao selecionar, a OS anterior será automaticamente marcada como "Substituída" e vinculada na cadeia histórica.
            </p>
          </div>
        )}
      </div>

      {/* 2. Upload de Anexos CSV */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" }}>
          <FileSpreadsheet size={20} style={{ color: "var(--accent-purple)" }} />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>2. Importação de Planilhas Operacionais (CSV)</h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          {/* ANEXO I Dropzone */}
          <div
            style={{
              border: `2px dashed ${anexoIFile ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
              borderRadius: "var(--radius-md)",
              padding: "20px",
              textAlign: "center",
              background: anexoIFile ? "rgba(56, 189, 248, 0.06)" : "rgba(11, 15, 25, 0.4)",
              transition: "all 0.2s ease",
            }}
          >
            <Upload size={24} style={{ color: "var(--accent-cyan)", margin: "0 auto 8px auto" }} />
            <h4 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>
              ANEXO I — Grade de Viagens (.csv)
            </h4>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "12px" }}>
              Matriz horária de partidas e quilometragens (117 colunas)
            </p>
            <input
              type="file"
              accept=".csv"
              id="upload-anexo-i"
              style={{ display: "none" }}
              onChange={(e) => e.target.files?.[0] && setAnexoIFile(e.target.files[0])}
            />
            <label htmlFor="upload-anexo-i" className="btn-secondary" style={{ cursor: "pointer", display: "inline-flex" }}>
              {anexoIFile ? `Alterar (${anexoIFile.name})` : "Selecionar CSV"}
            </label>
          </div>

          {/* ANEXO II Dropzone */}
          <div
            style={{
              border: `2px dashed ${anexoIIFile ? "var(--accent-purple)" : "var(--border-subtle)"}`,
              borderRadius: "var(--radius-md)",
              padding: "20px",
              textAlign: "center",
              background: anexoIIFile ? "rgba(139, 92, 246, 0.06)" : "rgba(11, 15, 25, 0.4)",
              transition: "all 0.2s ease",
            }}
          >
            <Upload size={24} style={{ color: "var(--accent-purple)", margin: "0 auto 8px auto" }} />
            <h4 style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-primary)" }}>
              ANEXO II — Itinerários Alternativos (.csv)
            </h4>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "12px" }}>
              Tabela de desvios operacionais para feiras, túneis e lazer
            </p>
            <input
              type="file"
              accept=".csv"
              id="upload-anexo-ii"
              style={{ display: "none" }}
              onChange={(e) => e.target.files?.[0] && setAnexoIIFile(e.target.files[0])}
            />
            <label htmlFor="upload-anexo-ii" className="btn-secondary" style={{ cursor: "pointer", display: "inline-flex" }}>
              {anexoIIFile ? `Alterar (${anexoIIFile.name})` : "Selecionar CSV"}
            </label>
          </div>
        </div>
      </div>

      {/* 3. Lista Dinâmica de Notas de Eventos */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>3. Notas de Alterações Operacionais (Eventos)</h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              Descreva cada alteração pontual (Inclusão, Remoção, Ajuste ou Retificação)
            </p>
          </div>
          <button type="button" onClick={handleAddEvento} className="btn-secondary">
            <Plus size={15} />
            Adicionar Alteração
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {eventos.map((ev, idx) => (
            <div
              key={idx}
              className="animate-fade-in"
              style={{
                background: "rgba(11, 15, 25, 0.6)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "18px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
                  Alteração #{idx + 1}
                </span>
                {eventos.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveEvento(idx)}
                    style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.78rem" }}
                  >
                    <Trash2 size={14} />
                    Remover
                  </button>
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Título Resumido da Alteração *
                  </label>
                  <input
                    type="text"
                    className="input-glass"
                    placeholder="Ex: Inclusão do planejamento de viagens da linha LECD131"
                    value={ev.title}
                    onChange={(e) => handleEventoChange(idx, "title", e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Tipo de Evento
                  </label>
                  <select
                    className="input-glass"
                    value={ev.tipo_evento}
                    onChange={(e: any) => handleEventoChange(idx, "tipo_evento", e.target.value)}
                    style={{ background: "#111827", cursor: "pointer" }}
                  >
                    <option value="Inclusão">Inclusão</option>
                    <option value="Remoção">Remoção</option>
                    <option value="Ajuste">Ajuste</option>
                    <option value="Correção/Retificação">Correção/Retificação</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Linhas / Serviços Afetados (separados por vírgula)
                  </label>
                  <input
                    type="text"
                    className="input-glass"
                    placeholder="Ex: 104, 117, LECD131"
                    value={ev.linhas_afetadas}
                    onChange={(e) => handleEventoChange(idx, "linhas_afetadas", e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Consórcios
                  </label>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {["Intersul", "Internorte", "Transcarioca", "Santa Cruz"].map((consorcio) => {
                      const sel = ev.consorcios.includes(consorcio);
                      return (
                        <button
                          type="button"
                          key={consorcio}
                          onClick={() => toggleConsorcioInEvento(idx, consorcio)}
                          style={{
                            background: sel ? "rgba(56, 189, 248, 0.2)" : "rgba(255, 255, 255, 0.04)",
                            border: `1px solid ${sel ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                            color: sel ? "var(--accent-cyan)" : "var(--text-secondary)",
                            padding: "4px 8px",
                            borderRadius: "6px",
                            fontSize: "0.75rem",
                            cursor: "pointer",
                          }}
                        >
                          {consorcio}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Descrição Completa da Modificação *
                </label>
                <textarea
                  className="input-glass"
                  rows={3}
                  placeholder="Detalhe o que foi modificado, motivos de atendimento, trechos e alterações de viagens..."
                  value={ev.descricao}
                  onChange={(e) => handleEventoChange(idx, "descricao", e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Justificativa Operacional (Opcional)
                </label>
                <input
                  type="text"
                  className="input-glass"
                  placeholder="Ex: Em virtude de obras viárias no corredor..."
                  value={ev.justificativa}
                  onChange={(e) => handleEventoChange(idx, "justificativa", e.target.value)}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Botão de Envio */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "8px" }}>
        <button
          type="submit"
          className="btn-primary"
          disabled={submitting}
          style={{ padding: "14px 28px", fontSize: "1rem" }}
        >
          <Send size={18} />
          {submitting ? "Gravando no Vault & Sincronizando RAG..." : "Publicar Ordem de Serviço"}
        </button>
      </div>
    </form>
  );
};
