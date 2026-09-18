/** Transforma dados crus da API /api/vault/graph em VaultGraphData para reagraph. */

import type { VaultNode, VaultEdge, VaultGraphData, NoteCategory } from "@/types/vault-graph";

interface RawNote {
  uid: string;
  title: string;
  category: string;
  wikilinks: string[];
}

export function buildGraphData(notes: RawNote[]): VaultGraphData {
  const uidSet = new Set(notes.map((n) => n.uid));

  const nodes: VaultNode[] = notes.map((n) => ({
    id: n.uid,
    label: n.title,
    category: (n.category as NoteCategory) ?? "evento",
  }));

  const edgeSet = new Set<string>();
  const edges: VaultEdge[] = [];

  for (const note of notes) {
    for (const target of note.wikilinks) {
      if (!uidSet.has(target)) continue;
      const key = `${note.uid}::${target}`;
      if (edgeSet.has(key)) continue;
      edgeSet.add(key);
      edges.push({ id: key, source: note.uid, target });
    }
  }

  return { nodes, edges };
}
