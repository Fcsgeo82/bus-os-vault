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
  availableOs?: OSOption[];
}

export interface OSOption {
  uid: string;
  title: string;
  status_vigencia?: string;
}

const DEFAULT_OS: OSOption[] = [
  { uid: "os-179-os-2026-09-setembro-1o-estudo-ret", title: "179 - OS 2026.09 - Setembro 1º Estudo ret" },
  { uid: "os-178-os-2026-09-setembro-1o-estudo", title: "178 - OS 2026.09 - Setembro 1º Estudo" },
  { uid: "os-2026-08-estudo-2-ret-4", title: "174 - OS 2026.08 - Agosto 2º Estudo [ret4]" },
];

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  availableOs = [],
}) => {
  const osSource = availableOs.length > 0 ? availableOs : DEFAULT_OS;
  const osOptions: FilterOption[] = osSource.map((o) => ({
    id: o.title,
    label: o.title,
    sublabel: o.status_vigencia,
  }));

  const toggleOs = (title: string) => {
    const exists = filters.os_titulos.includes(title);
    const updated = exists
      ? filters.os_titulos.filter((t) => t !== title)
      : [...filters.os_titulos, title];
    onChange({ ...filters, os_titulos: updated });
  };

  const resetFilters = () => {
    onChange({
      apenas_vigentes: true,
      os_titulos: [],
    });
  };

  const hasActiveFilters = !filters.apenas_vigentes || filters.os_titulos.length > 0;

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

      {/* Popup de OS com busca */}
      <MultiSelectPopup
        label="OS"
        accentColor="#38bdf8"
        tintColor="rgba(56, 189, 248, 0.16)"
        options={osOptions}
        selected={filters.os_titulos}
        onToggle={toggleOs}
        placeholder="Buscar OS..."
        emptyText="Nenhuma OS encontrada."
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