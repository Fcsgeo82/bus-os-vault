/** Tipos para o grafo do vault. */

export type NoteCategory = "os" | "evento" | "linha" | "anexo";

export interface VaultNode {
  id: string;
  label: string;
  category: NoteCategory;
}

export interface VaultEdge {
  id: string;
  source: string;
  target: string;
}

export interface VaultGraphData {
  nodes: VaultNode[];
  edges: VaultEdge[];
}
