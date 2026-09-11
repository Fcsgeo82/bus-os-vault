"use client";

import React, { useEffect, useState } from "react";
import { X, FileText, Tag, Calendar, Layers } from "lucide-react";
import { VaultNote } from "@/lib/types";

interface NoteViewerModalProps {
  noteIdentifier: string | null;
  onClose: () => void;
}

export const NoteViewerModal: React.FC<NoteViewerModalProps> = ({ noteIdentifier, onClose }) => {
  const [note, setNote] = useState<VaultNote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!noteIdentifier) {
      setNote(null);
      return;
    }

    const cleanId = noteIdentifier.replace(/\[\[|\]\]/g, "").trim();
    setLoading(true);
    setError(null);

    fetch(`/api/os/notes/${encodeURIComponent(cleanId)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Nota não encontrada no cofre.");
        return res.json();
      })
      .then((data) => setNote(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [noteIdentifier]);

  if (!noteIdentifier) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "100%",
        maxWidth: "640px",
        height: "100vh",
        background: "rgba(13, 18, 30, 0.96)",
        backdropFilter: "blur(20px)",
        borderLeft: "1px solid var(--border-subtle)",
        zIndex: 100,
        boxShadow: "-10px 0 35px rgba(0, 0, 0, 0.5)",
        display: "flex",
        flexDirection: "column",
        animation: "fadeIn 0.2s ease-out",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "18px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <FileText size={20} style={{ color: "var(--accent-cyan)" }} />
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-primary)" }}>
              {note?.metadata.title || noteIdentifier.replace(/\[\[|\]\]/g, "")}
            </h3>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              {note?.relative_path || "Carregando caminho..."}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "rgba(255, 255, 255, 0.06)",
            border: "none",
            borderRadius: "50%",
            width: "32px",
            height: "32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-secondary)",
            cursor: "pointer",
          }}
        >
          <X size={18} />
        </button>
      </div>

      {/* Body */}
      <div style={{ padding: "24px", overflowY: "auto", flex: 1 }}>
        {loading && <p style={{ color: "var(--text-secondary)" }}>Carregando nota do Vault...</p>}
        {error && <p style={{ color: "#f87171" }}>{error}</p>}

        {note && (
          <div>
            {/* Frontmatter YAML Card */}
            {note.metadata && Object.keys(note.metadata).length > 0 && (
              <div
                style={{
                  background: "rgba(18, 24, 38, 0.7)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px",
                  marginBottom: "20px",
                  fontSize: "0.82rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "10px", color: "var(--accent-cyan)", fontWeight: 600 }}>
                  <Layers size={14} />
                  <span>Frontmatter YAML</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  {note.metadata.tipo_os && (
                    <div><span style={{ color: "var(--text-muted)" }}>Tipo:</span> <strong>{note.metadata.tipo_os}</strong></div>
                  )}
                  {note.metadata.status_vigencia && (
                    <div><span style={{ color: "var(--text-muted)" }}>Status:</span> <strong>{note.metadata.status_vigencia}</strong></div>
                  )}
                  {note.metadata.inicio_vigencia && (
                    <div><span style={{ color: "var(--text-muted)" }}>Vigência:</span> <strong>{note.metadata.inicio_vigencia}</strong></div>
                  )}
                  {note.metadata.processo_rio && (
                    <div><span style={{ color: "var(--text-muted)" }}>Processo:</span> <strong>{note.metadata.processo_rio}</strong></div>
                  )}
                  {note.metadata.retifica_os && (
                    <div style={{ gridColumn: "span 2" }}>
                      <span style={{ color: "var(--text-muted)" }}>Retifica:</span> <strong style={{ color: "#fbbf24" }}>{note.metadata.retifica_os}</strong>
                    </div>
                  )}
                </div>

                {note.metadata.tags && note.metadata.tags.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "12px" }}>
                    {note.metadata.tags.map((tag: string) => (
                      <span key={tag} className="badge badge-tag">
                        <Tag size={10} />
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Markdown Content Rendered */}
            <div
              style={{
                color: "var(--text-secondary)",
                fontSize: "0.92rem",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
              }}
            >
              {note.content}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
