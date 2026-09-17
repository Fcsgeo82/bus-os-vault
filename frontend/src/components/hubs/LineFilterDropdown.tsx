"use client";

import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Search, Check, X } from "lucide-react";
import { LineOption } from "@/components/filters/FilterBar";

interface LineFilterDropdownProps {
  options: LineOption[];
  selected: string | null;
  onChange: (codigo: string | null) => void;
}

export const LineFilterDropdown: React.FC<LineFilterDropdownProps> = ({
  options,
  selected,
  onChange,
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
    (o) => !q || o.codigo.toLowerCase().includes(q) || (o.vista ?? "").toLowerCase().includes(q)
  );

  const select = (codigo: string | null) => {
    onChange(codigo);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <button
          onClick={toggleOpen}
          title="Filtrar hubs por linha"
          style={{
            background: selected ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.05)",
            border: `1px solid ${selected ? "var(--accent-emerald)" : "var(--border-subtle)"}`,
            color: selected ? "var(--accent-emerald)" : "var(--text-secondary)",
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.78rem",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            transition: "all 0.2s",
          }}
        >
          <span>{selected ? `${selected}` : "Filtrar linha"}</span>
          <ChevronDown size={12} style={{ opacity: 0.7 }} />
        </button>
        {selected && (
          <button
            onClick={() => select(null)}
            title="Mostrar todas as linhas"
            aria-label="Limpar filtro de linha"
            style={{
              background: "none",
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
            <X size={14} />
          </button>
        )}
      </div>

      {open &&
        coords &&
        createPortal(
          <div
            ref={dropdownRef}
            onMouseDown={(e) => e.stopPropagation()}
            style={{
              position: "fixed",
              top: coords.top,
              left: coords.left,
              zIndex: 10000,
              width: "300px",
              maxWidth: "calc(100vw - 48px)",
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
              placeholder="Buscar linha..."
              style={{
                width: "100%",
                background: "rgba(255, 255, 255, 0.06)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                padding: "7px 10px 7px 30px",
                color: "var(--text-primary)",
                fontSize: "0.8rem",
                outline: "none",
              }}
            />
          </div>

          <div
            style={{
              maxHeight: "220px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "2px",
            }}
          >
            {filtered.length === 0 && (
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", padding: "8px" }}>
                Nenhuma linha encontrada.
              </span>
            )}
            {filtered.map((option) => {
              const isSelected = option.codigo === selected;
              return (
                <button
                  key={option.codigo}
                  onClick={() => select(option.codigo)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "6px 8px",
                    borderRadius: "6px",
                    background: isSelected ? "rgba(16, 185, 129, 0.12)" : "transparent",
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
                      border: `1px solid ${isSelected ? "var(--accent-emerald)" : "var(--border-subtle)"}`,
                      background: isSelected ? "var(--accent-emerald)" : "transparent",
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
                    <span style={{ fontWeight: isSelected ? 700 : 500 }}>{option.codigo}</span>
                    {option.vista && (
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                        {option.vista}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => select(null)}
            style={{
              marginTop: "8px",
              width: "100%",
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              padding: "6px",
              color: "var(--text-secondary)",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Mostrar todas as linhas
          </button>
          </div>,
          document.body,
        )}
    </div>
  );
};