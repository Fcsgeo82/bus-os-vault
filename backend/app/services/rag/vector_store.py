"""Armazenamento vetorial embedded com LanceDB para o acervo de OS."""

import json
from typing import List, Dict, Any, Optional
import lancedb
import pyarrow as pa
from app.core.config import settings
from app.services.rag.embeddings import embedding_provider


class LanceDBStore:
    """Interface de persistência e consulta vetorial do LanceDB."""

    TABLE_NAME = "vault_chunks"

    def __init__(self):
        self.db = lancedb.connect(str(settings.LANCEDB_DIR))
        self.table = None  # Será criada/obtida no primeiro index_chunks ou search

    def _ensure_table(self):
        """Obtém a tabela existente ou retorna None (será criada no index_chunks)."""
        if self.table is not None:
            return self.table
        tables = self.db.list_tables() if hasattr(self.db, "list_tables") else []
        if self.TABLE_NAME in tables:
            self.table = self.db.open_table(self.TABLE_NAME)
            return self.table
        return None

    def index_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Calcula embeddings e indexa chunks na tabela."""
        if not chunks:
            return 0

        # Gera embeddings em lote
        texts = [c["texto"] for c in chunks]
        vectors = embedding_provider.embed_batch(texts)

        records = []
        for c, vec in zip(chunks, vectors):
            records.append({
                "vector": vec,
                "chunk_id": c["chunk_id"],
                "nota_titulo": c["nota_titulo"],
                "os_titulo": c.get("os_titulo", ""),
                "secao_titulo": c["secao_titulo"],
                "arquivo_path": c["arquivo_path"],
                "categoria": c["categoria"],
                "is_hub": c.get("is_hub", False),
                "status_vigencia": c.get("status_vigencia", "Vigente"),
                "ano_mes": str(c.get("ano_mes", "")),
                "linhas_afetadas": json.dumps(c.get("linhas_afetadas", [])),
                "consorcios": json.dumps(c.get("consorcios", [])),
                "texto": c["texto"],
            })

        # Sempre sobrescreve com schema atualizado
        self.table = self.db.create_table(
            self.TABLE_NAME,
            data=records,
            mode="overwrite",
        )
        return len(records)

    def search_dense(
        self,
        query: str,
        top_k: int = 10,
        status_vigencia: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Realiza busca vetorial por similaridade de cosseno."""
        table = self._ensure_table()
        if table is None or table.count_rows() == 0:
            return []

        query_vec = embedding_provider.embed_text(query)
        search = table.search(query_vec).limit(top_k)

        if status_vigencia:
            search = search.where(f"status_vigencia = '{status_vigencia}'")

        results = search.to_list()
        formatted = []
        for r in results:
            formatted.append({
                "chunk_id": r["chunk_id"],
                "nota_titulo": r["nota_titulo"],
                "os_titulo": r.get("os_titulo", ""),
                "secao_titulo": r["secao_titulo"],
                "arquivo_path": r["arquivo_path"],
                "categoria": r["categoria"],
                "is_hub": bool(r.get("is_hub", False)),
                "status_vigencia": r["status_vigencia"],
                "ano_mes": r["ano_mes"],
                "linhas_afetadas": json.loads(r["linhas_afetadas"]),
                "consorcios": json.loads(r["consorcios"]),
                "texto": r["texto"],
                "distance": r.get("_distance", 0.0),
                "score": round(1.0 / (1.0 + float(r.get("_distance", 1.0))), 4),
            })
        return formatted


vector_store = LanceDBStore()
