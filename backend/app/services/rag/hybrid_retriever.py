"""Mecanismo de recuperação híbrida combinando busca densa vetorial e busca léxica via RRF."""

import re
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.rag_schema import RAGFilters, RAGSource
from app.services.rag.vector_store import vector_store
from app.services.rag.lexical_search import lexical_searcher
from app.services.rag.chunker import _normalize_os


def _query_line_codes(query: str) -> List[str]:
    """Extrai códigos de linha numéricos da query (ex: '104' em 'linha 104')."""
    return re.findall(r"\b(\d{3,4})\b", query)


def _chunk_toca_linha(chunk: Dict[str, Any], codigos: List[str]) -> bool:
    """Verifica se um chunk pertence a uma das linhas consultadas."""
    titulo = str(chunk.get("nota_titulo", ""))
    texto = str(chunk.get("texto", ""))
    for codigo in codigos:
        if codigo in titulo:
            return True
        if f"**{codigo}**" in texto:
            return True
    return False


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
        # Quando há filtro por OS, amplia o pool de candidatos para não perder
        # chunks relevantes da OS selecionada que ficariam fora do top-K global.
        pool = top_k * (5 if filters and filters.os_titulos else 2)

        # 1. Recuperação Densa (LanceDB)
        dense_results = vector_store.search_dense(query, top_k=pool)

        # 2. Recuperação Léxica (BM25)
        lexical_results = lexical_searcher.search(query, top_k=pool)

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

        # 4. Aplica boost específico quando query cita linha(s) numérica(s)
        line_codes = _query_line_codes(query)
        if line_codes:
            for cid in fused_scores:
                chunk = chunk_lookup[cid]
                if _chunk_toca_linha(chunk, line_codes):
                    fused_scores[cid] *= settings.HUB_BOOST

        # 5. Ordena por score RRF
        sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        # 6. Aplica filtros de domínio
        filtered_sources: List[RAGSource] = []
        for cid in sorted_chunk_ids:
            chunk = chunk_lookup[cid]

            # Filtro de vigência
            if filters and filters.apenas_vigentes:
                status = str(chunk.get("status_vigencia", "Vigente")).lower()
                if status in ["revogada", "substituída", "substituida"]:
                    continue

            # Filtro por OS de origem (compara títulos normalizados)
            if filters and filters.os_titulos:
                wanted = {_normalize_os(t) for t in filters.os_titulos}
                if _normalize_os(str(chunk.get("os_titulo", ""))) not in wanted:
                    continue

            # Filtro por ano/mês
            if filters and filters.ano_mes:
                chunk_ano_mes = str(chunk.get("ano_mes", "")).strip()
                if chunk_ano_mes and chunk_ano_mes != filters.ano_mes:
                    continue

            # Truncamento do trecho
            trecho = chunk["texto"]
            if len(trecho) > settings.TRECHO_MAX_CHARS:
                trecho = trecho[:settings.TRECHO_MAX_CHARS] + "..."

            filtered_sources.append(
                RAGSource(
                    chunk_id=cid,
                    nota_titulo=chunk["nota_titulo"],
                    arquivo_path=chunk["arquivo_path"],
                    categoria=chunk["categoria"],
                    score=round(fused_scores[cid] * 100, 2),
                    trecho=trecho,
                    metadata={
                        "status_vigencia": chunk.get("status_vigencia"),
                        "os_titulo": chunk.get("os_titulo", ""),
                        "ano_mes": chunk.get("ano_mes"),
                        "linhas_afetadas": chunk.get("linhas_afetadas", []),
                        "is_hub": chunk.get("is_hub", False),
                    },
                )
            )

            if len(filtered_sources) >= top_k:
                break

        return filtered_sources


hybrid_retriever = HybridRetriever(rrf_k=settings.RRF_K)
