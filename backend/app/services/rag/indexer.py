"""Serviço de indexação do cofre no LanceDB e BM25."""

from pathlib import Path
from typing import List, Dict, Any
from app.core.config import settings
from app.services.rag.chunker import vault_chunker
from app.services.rag.vector_store import vector_store
from app.services.rag.lexical_search import lexical_searcher


class VaultIndexer:
    """Coordena a varredura do cofre e indexação no LanceDB e BM25."""

    @staticmethod
    def index_entire_vault(vault_dir: Path | None = None) -> Dict[str, Any]:
        """Varre todas as notas Markdown do cofre e sincroniza os índices."""
        target_dir = vault_dir or settings.VAULT_DIR
        all_chunks: List[Dict[str, Any]] = []
        falhas: List[str] = []

        md_files = list(target_dir.rglob("*.md"))
        for f in md_files:
            try:
                chunks = vault_chunker.chunk_document(f)
                all_chunks.extend(chunks)
            except Exception as e:
                falhas.append(f"{f}: {e}")
                print(f"[AVISO] Falha ao processar chunks de {f.name}: {e}")

        if not all_chunks:
            raise RuntimeError(
                "Nenhum chunk gerado durante a indexação. Verifique o chunker e o cofre."
            )

        # 1. Indexa no LanceDB
        total_vectors = vector_store.index_chunks(all_chunks)

        # 2. Constrói o índice BM25 em memória
        lexical_searcher.build_index(all_chunks)

        return {
            "total_files": len(md_files),
            "total_chunks": len(all_chunks),
            "total_vectors_indexed": total_vectors,
            "falhas": falhas,
        }


vault_indexer = VaultIndexer()
