"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { Network, Filter } from "lucide-react";
import type { VaultNode, VaultEdge, VaultGraphData, NoteCategory } from "@/types/vault-graph";
import { buildGraphData } from "@/lib/build-vault-graph";

const CATEGORY_META: Record<NoteCategory, { color: string; label: string }> = {
  os: { color: "#38bdf8", label: "OS" },
  evento: { color: "#f59e0b", label: "Evento" },
  linha: { color: "#10b981", label: "Linha" },
  anexo: { color: "#8b5cf6", label: "Anexo" },
};

function GraphCanvasLazy({ data, selected }: { data: VaultGraphData; selected: Set<string> }) {
  const { GraphCanvas } = require("reagraph");

  const nodes = data.nodes
    .filter((n) => selected.has(n.category))
    .map((n) => ({
      id: n.id,
      label: n.label,
      fill: CATEGORY_META[n.category].color,
      size: n.category === "os" ? 10 : 6,
    }));

  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges = data.edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e) => ({ id: e.id, source: e.source, target: e.target }));

  return (
    <GraphCanvas
      nodes={nodes}
      edges={edges}
      layoutType="forceDirected2d"
      labelType="auto"
      edgeArrowPosition="end"
      defaultNodeSize={7}
      style={{ width: "100%", height: "100%", background: "transparent" }}
    />
  );
}

export default function VaultGraph() {
  const [graphData, setGraphData] = useState<VaultGraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Set<NoteCategory>>(
    new Set(["os", "evento", "linha", "anexo"])
  );

  useEffect(() => {
    fetch("/api/vault/graph")
      .then((res) => {
        if (!res.ok) throw new Error("Falha ao carregar dados do grafo.");
        return res.json();
      })
      .then((data) => setGraphData(buildGraphData(data)))
      .catch((err) => setError(err instanceof Error ? err.message : "Erro desconhecido."))
      .finally(() => setLoading(false));
  }, []);

  const toggleCategory = useCallback((cat: NoteCategory) => {
    setFilter((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  if (loading) {
    return (
      <div style={styles.centered}>
        <Network size={32} color="var(--accent-cyan)" className="animate-spin" style={{ animationDuration: "3s" }} />
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Carregando grafo do cofre...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.centered}>
        <p style={{ color: "#f87171", fontSize: "0.85rem" }}>{error}</p>
      </div>
    );
  }

  const nodeCount = graphData?.nodes.length ?? 0;
  const edgeCount = graphData?.edges.length ?? 0;

  return (
    <div className="animate-fade-in" style={styles.container}>
      {/* Barra de filtros + estatísticas */}
      <div style={styles.toolbar}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Filter size={14} color="var(--text-muted)" />
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Filtrar:</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {(Object.entries(CATEGORY_META) as [NoteCategory, { color: string; label: string }][]).map(
            ([cat, meta]) => (
              <button
                key={cat}
                onClick={() => toggleCategory(cat)}
                style={{
                  ...styles.filterBtn,
                  opacity: filter.has(cat) ? 1 : 0.35,
                  borderColor: filter.has(cat) ? meta.color : "var(--border-subtle)",
                  color: filter.has(cat) ? meta.color : "var(--text-muted)",
                  background: filter.has(cat) ? `${meta.color}18` : "transparent",
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: meta.color,
                    display: "inline-block",
                  }}
                />
                {meta.label}
              </button>
            )
          )}
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: "12px", fontSize: "0.72rem", color: "var(--text-muted)" }}>
          <span>{nodeCount} nós</span>
          <span>{edgeCount} arestas</span>
        </div>
      </div>

      {/* Canvas do grafo */}
      <div style={styles.canvasWrap}>
        {graphData && (
          <Suspense
            fallback={
              <div style={styles.centered}>
                <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>Renderizando WebGL...</p>
              </div>
            }
          >
            <GraphCanvasLazy data={graphData} selected={filter} />
          </Suspense>
        )}
      </div>

      {/* Legenda */}
      <div style={styles.legend}>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Legenda:</span>
        {Object.entries(CATEGORY_META).map(([cat, meta]) => (
          <div key={cat} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: meta.color }} />
            <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{meta.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "calc(100vh - 160px)",
    minHeight: "500px",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 18px",
    background: "var(--bg-card)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "var(--radius-md) var(--radius-md) 0 0",
    flexWrap: "wrap",
  },
  filterBtn: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
    padding: "5px 10px",
    border: "1px solid var(--border-subtle)",
    borderRadius: "8px",
    fontSize: "0.78rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  canvasWrap: {
    flex: 1,
    background: "rgba(10, 13, 20, 0.6)",
    border: "1px solid var(--border-subtle)",
    borderTop: "none",
    borderRadius: "0 0 var(--radius-md) var(--radius-md)",
    overflow: "hidden",
    position: "relative",
  },
  centered: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "12px",
    padding: "80px 20px",
  },
  legend: {
    display: "flex",
    alignItems: "center",
    gap: "14px",
    padding: "10px 18px",
    marginTop: "10px",
  },
};
