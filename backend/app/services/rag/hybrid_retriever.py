"""Mecanismo de recuperação híbrida combinando busca densa vetorial e busca léxica via RRF."""

from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.rag_schema import RAGFilters, RAGSource
from app.services.rag.vector_store import vector_store
from app.services.rag.lexical_search import lexical_searcher


class HybridRetriever:
    """Combina busca semântica no LanceDB com busca BM25 via Reciprocal Rank Fusion."""

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        filters: Optional[RAGFilters] = None,
    ) -> List[RAGSource]:
        """Recupera e funde os resultados vetoriais e lexicais."""
        # 1. Recuperação Densa (LanceDB)
        dense_results = vector_store.search_dense(query, top_k=top_k * 2)

        # 2. Recuperação Léxica (BM25)
        lexical_results = lexical_searcher.search(query, top_k=top_k * 2)

        # 3. Reciprocal Rank Fusion (RRF)
        fused_scores: Dict[str, float] = {}
        chunk_lookup: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            chunk_lookup[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank + 1))

        for rank, item in enumerate(lexical_results):
            cid = item["chunk_id"]
            if cid not in chunk_lookup:
                chunk_lookup[cid] = item
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank + 1))

        # 4. Ordena por score RRF
        sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        # 5. Aplica filtros de domínio
        filtered_sources: List[RAGSource] = []
        for cid in sorted_chunk_ids:
            chunk = chunk_lookup[cid]

            # Filtro de vigência
            if filters and filters.apenas_vigentes:
                status = str(chunk.get("status_vigencia", "Vigente")).lower()
                if status in ["revogada", "substituída", "substituida"]:
                    continue

            # Filtro por linhas
            if filters and filters.linhas:
                chunk_linhas = [str(l).lower() for l in chunk.get("linhas_afetadas", [])]
                if not any(fl.lower() in chunk_linhas for fl in filters.linhas):
                    # Se a linha procurada não está no metadata, verifica se o texto cita a linha
                    texto_lower = chunk.get("texto", "").lower()
                    if not any(f"linha {fl.lower()}" in texto_lower or f"**{fl.lower()}**" in texto_lower for fl in filters.linhas):
                        continue

            # Filtro por consórcio
            if filters and filters.consorcios:
                chunk_consorcios = [str(c).lower() for c in chunk.get("consorcios", [])]
                if not any(fc.lower() in chunk_consorcios for fc in filters.consorcios):
                    continue

            filtered_sources.append(
                RAGSource(
                    chunk_id=cid,
                    nota_titulo=chunk["nota_titulo"],
                    arquivo_path=chunk["arquivo_path"],
                    categoria=chunk["categoria"],
                    score=round(fused_scores[cid] * 100, 2),
                    trecho=chunk["texto"],
                    metadata={
                        "status_vigencia": chunk.get("status_vigencia"),
                        "ano_mes": chunk.get("ano_mes"),
                        "linhas_afetadas": chunk.get("linhas_afetadas", []),
                    },
                )
            )

            if len(filtered_sources) >= top_k:
                break

        return filtered_sources


hybrid_retriever = HybridRetriever(rrf_k=settings.RRF_K)
