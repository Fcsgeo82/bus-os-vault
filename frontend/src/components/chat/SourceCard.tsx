"use client";

import React, { useState } from "react";
import { FileText, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { RAGSource } from "@/lib/types";

interface SourceCardProps {
  source: RAGSource;
  onOpenNote: (titulo: string) => void;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, onOpenNote }) => {
  const [expanded, setExpanded] = useState(false);

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case "os_mestra":
        return <span className="badge badge-vigente">OS Mestra</span>;
      case "nota_evento":
        return <span className="badge badge-tag">Alteração / Evento</span>;
      case "anexo_operacional":
        return <span className="badge badge-retificada">Anexo Operacional</span>;
      default:
        return <span className="badge badge-tag">{cat}</span>;
    }
  };

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.6)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: "var(--radius-md)",
        padding: "10px 14px",
        marginTop: "8px",
        fontSize: "0.85rem",
        transition: "all 0.2s ease",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          cursor: "pointer",
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, overflow: "hidden" }}>
          <FileText size={15} style={{ color: "var(--accent-cyan)", flexShrink: 0 }} />
          <span
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            [[{source.nota_titulo}]]
          </span>
          {getCategoryBadge(source.categoria)}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              fontSize: "0.75rem",
              color: "var(--accent-cyan)",
              fontWeight: 600,
              background: "rgba(56, 189, 248, 0.1)",
              padding: "2px 6px",
              borderRadius: "4px",
            }}
          >
            {source.score}% ref
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onOpenNote(source.nota_titulo);
            }}
            title="Abrir nota do Vault"
            style={{
              background: "none",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "4px",
              display: "flex",
              alignItems: "center",
            }}
          >
            <ExternalLink size={14} />
          </button>
          {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      {expanded && (
        <div
          style={{
            marginTop: "10px",
            paddingTop: "10px",
            borderTop: "1px solid rgba(255, 255, 255, 0.05)",
            color: "var(--text-secondary)",
            fontSize: "0.8rem",
            lineHeight: 1.5,
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-mono, monospace)",
            maxHeight: "180px",
            overflowY: "auto",
          }}
        >
          {source.trecho}
        </div>
      )}
    </div>
  );
};
