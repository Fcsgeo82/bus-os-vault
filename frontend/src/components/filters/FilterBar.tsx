"use client";

import React, { useRef, useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Filter, Check, RotateCcw, Search, ChevronDown } from "lucide-react";
import { RAGFilters } from "@/lib/types";

export interface LineOption {
  codigo: string;
  vista?: string;
  consorcio?: string;
}

interface FilterOption {
  id: string;
  label: string;
  sublabel?: string;
}

interface MultiSelectPopupProps {
  label: string;
  accentColor: string;
  tintColor: string;
  options: FilterOption[];
  selected: string[];
  onToggle: (id: string) => void;
  placeholder: string;
  emptyText: string;
}

const MultiSelectPopup: React.FC<MultiSelectPopupProps> = ({
  label,
  accentColor,
  tintColor,
  options,
  selected,
  onToggle,
  placeholder,
  emptyText,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        containerRef.current &&
        !containerRef.current.contains(target) &&
        (!dropdownRef.current || !dropdownRef.current.contains(target))
      ) {
        setOpen(false);
        setQuery("");
      }
    };
    const closeOnMove = () => {
      setOpen(false);
      setQuery("");
    };
    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("scroll", closeOnMove, true);
    window.addEventListener("resize", closeOnMove);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", closeOnMove, true);
      window.removeEventListener("resize", closeOnMove);
    };
  }, [open]);

  const toggleOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (open) {
      setOpen(false);
      setQuery("");
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setCoords({ top: rect.bottom + 6, left: rect.left });
    setOpen(true);
  };

  const q = query.trim().toLowerCase();
  const filtered = options.filter(
    (o) => !q || o.label.toLowerCase().includes(q) || (o.sublabel ?? "").toLowerCase().includes(q)
  );

  return (
    <div ref={containerRef}>
      <button
        onClick={toggleOpen}
        style={{
          background: selected.length > 0 ? tintColor : "rgba(255, 255, 255, 0.05)",
          border: `1px solid ${selected.length > 0 ? accentColor : "var(--border-subtle)"}`,
          color: selected.length > 0 ? accentColor : "var(--text-secondary)",
          padding: "6px 12px",
          borderRadius: "var(--radius-sm)",
          fontSize: "0.8rem",
          fontWeight: 600,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          transition: "all 0.2s",
        }}
      >
        <span>{label}</span>
        {selected.length > 0 && (
          <span
            style={{
              background: accentColor,
              color: "#0b0f19",
              borderRadius: "999px",
              padding: "0 7px",
              fontSize: "0.7rem",
              fontWeight: 700,
            }}
          >
            {selected.length}
          </span>
        )}
        <ChevronDown size={13} style={{ opacity: 0.7 }} />
      </button>

      {open &&
        coords &&
        createPortal(
          <div
            id="filter-popup"
            ref={dropdownRef}
            onMouseDown={(e) => e.stopPropagation()}
            style={{
              position: "fixed",
              top: coords.top,
              left: coords.left,
              zIndex: 9999,
              minWidth: "280px",
              maxWidth: "min(360px, calc(100vw - 16px))",
              maxHeight: "min(400px, calc(100vh - 16px))",
              overflowY: "auto",
              background: "rgba(15, 23, 42, 0.97)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              boxShadow: "0 12px 32px rgba(0, 0, 0, 0.5)",
              padding: "10px",
            }}
          >
            <div style={{ position: "relative", marginBottom: "8px" }}>
              <Search
                size={14}
                style={{
                  position: "absolute",
                  left: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                style={{
                  width: "100%",
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  padding: "8px 10px 8px 30px",
                  color: "var(--text-primary)",
                  fontSize: "0.8rem",
                  outline: "none",
                }}
              />
            </div>

            <div
              style={{
                maxHeight: "240px",
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              {filtered.length === 0 && (
                <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", padding: "8px" }}>
                  {emptyText}
                </span>
              )}
              {filtered.map((option) => {
                const isSelected = selected.includes(option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => onToggle(option.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "7px 8px",
                      borderRadius: "6px",
                      background: isSelected ? tintColor : "transparent",
                      border: "none",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    <span
                      style={{
                        width: "16px",
                        height: "16px",
                        borderRadius: "4px",
                        border: `1px solid ${isSelected ? accentColor : "var(--border-subtle)"}`,
                        background: isSelected ? accentColor : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      {isSelected && <Check size={11} color="#0b0f19" />}
                    </span>
                    <span
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        lineHeight: 1.3,
                        fontSize: "0.8rem",
                        color: isSelected ? "var(--text-primary)" : "var(--text-secondary)",
                      }}
                    >
                      <span style={{ fontWeight: isSelected ? 700 : 500 }}>{option.label}</span>
                      {option.sublabel && (
                        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                          {option.sublabel}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};

interface FilterBarProps {
  filters: RAGFilters;
  onChange: (newFilters: RAGFilters) => void;
  availableLines?: LineOption[];
  availableConsorcios?: string[];
}

const DEFAULT_LINES: LineOption[] = [
  { codigo: "006" },
  { codigo: "104" },
  { codigo: "117" },
  { codigo: "169" },
  { codigo: "LECD999" },
];

const DEFAULT_CONSORCIOS = ["Intersul", "Internorte", "Transcarioca", "Santa Cruz"];

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  availableLines = [],
  availableConsorcios = [],
}) => {
  const linesSource = availableLines.length > 0 ? availableLines : DEFAULT_LINES;
  const lineOptions: FilterOption[] = linesSource.map((l) => ({
    id: l.codigo,
    label: l.codigo,
    sublabel: l.vista,
  }));

  const consorciosSource = availableConsorcios.length > 0 ? availableConsorcios : DEFAULT_CONSORCIOS;
  const consorcioOptions: FilterOption[] = consorciosSource.map((c) => ({ id: c, label: c }));

  const toggleLine = (line: string) => {
    const exists = filters.linhas.includes(line);
    const updated = exists ? filters.linhas.filter((l) => l !== line) : [...filters.linhas, line];
    onChange({ ...filters, linhas: updated });
  };

  const toggleConsorcio = (consorcio: string) => {
    const exists = filters.consorcios.includes(consorcio);
    const updated = exists
      ? filters.consorcios.filter((c) => c !== consorcio)
      : [...filters.consorcios, consorcio];
    onChange({ ...filters, consorcios: updated });
  };

  const resetFilters = () => {
    onChange({
      apenas_vigentes: true,
      linhas: [],
      consorcios: [],
    });
  };

  const hasActiveFilters =
    !filters.apenas_vigentes || filters.linhas.length > 0 || filters.consorcios.length > 0;

  const segStyle = (active: boolean): React.CSSProperties => ({
    background: active ? "rgba(16, 185, 129, 0.15)" : "transparent",
    border: "none",
    color: active ? "#34d399" : "var(--text-muted)",
    padding: "6px 12px",
    fontSize: "0.8rem",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    transition: "all 0.2s",
  });

  return (
    <div
      className="glass-panel"
      style={{
        padding: "12px 18px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "14px",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          color: "var(--text-secondary)",
          fontSize: "0.85rem",
          fontWeight: 600,
        }}
      >
        <Filter size={15} style={{ color: "var(--accent-cyan)" }} />
        <span>Filtros RAG:</span>
      </div>

      {/* Vigência (Apenas Vigentes ou Todas) */}
      <div
        style={{
          display: "flex",
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <button
          onClick={() => onChange({ ...filters, apenas_vigentes: true })}
          style={segStyle(filters.apenas_vigentes)}
          title="Restringir a notas e OS com vigência ativa"
        >
          {filters.apenas_vigentes && <Check size={13} />}
          Só Vigentes
        </button>
        <button
          onClick={() => onChange({ ...filters, apenas_vigentes: false })}
          style={segStyle(!filters.apenas_vigentes)}
          title="Consultar todo o acervo, incluindo retificadas/substituídas"
        >
          Todas
        </button>
      </div>

      {/* Popup de Linhas com busca */}
      <MultiSelectPopup
        label="Linhas"
        accentColor="#38bdf8"
        tintColor="rgba(56, 189, 248, 0.16)"
        options={lineOptions}
        selected={filters.linhas}
        onToggle={toggleLine}
        placeholder="Buscar linha..."
        emptyText="Nenhuma linha encontrada."
      />

      {/* Popup de Consórcios com busca */}
      <MultiSelectPopup
        label="Consórcios"
        accentColor="#a78bfa"
        tintColor="rgba(167, 139, 250, 0.16)"
        options={consorcioOptions}
        selected={filters.consorcios}
        onToggle={toggleConsorcio}
        placeholder="Buscar consórcio..."
        emptyText="Nenhum consórcio encontrado."
      />

      {hasActiveFilters && (
        <button
          onClick={resetFilters}
          title="Redefinir filtros"
          style={{
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            fontSize: "0.78rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            marginLeft: "auto",
          }}
        >
          <RotateCcw size={12} />
          Limpar
        </button>
      )}
    </div>
  );
};