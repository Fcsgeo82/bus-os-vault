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
        self.table = self._get_or_create_table()

    def _get_or_create_table(self):
        """Inicializa ou obtém a tabela vetorial com schema Arrow."""
        tables = self.db.table_names() if hasattr(self.db, "table_names") else []
        if self.TABLE_NAME in tables:
            return self.db.open_table(self.TABLE_NAME)

        schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), settings.EMBEDDING_DIMENSION)),
            pa.field("chunk_id", pa.string()),
            pa.field("nota_titulo", pa.string()),
            pa.field("secao_titulo", pa.string()),
            pa.field("arquivo_path", pa.string()),
            pa.field("categoria", pa.string()),
            pa.field("status_vigencia", pa.string()),
            pa.field("ano_mes", pa.string()),
            pa.field("linhas_afetadas", pa.string()),  # JSON list
            pa.field("consorcios", pa.string()),       # JSON list
            pa.field("texto", pa.string()),
        ])

        return self.db.create_table(self.TABLE_NAME, schema=schema, mode="create")

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
                "secao_titulo": c["secao_titulo"],
                "arquivo_path": c["arquivo_path"],
                "categoria": c["categoria"],
                "status_vigencia": c.get("status_vigencia", "Vigente"),
                "ano_mes": str(c.get("ano_mes", "")),
                "linhas_afetadas": json.dumps(c.get("linhas_afetadas", [])),
                "consorcios": json.dumps(c.get("consorcios", [])),
                "texto": c["texto"],
            })

        # Sobrescreve tabela com novos dados (ou adiciona)
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
        if self.table.count_rows() == 0:
            return []

        query_vec = embedding_provider.embed_text(query)
        search = self.table.search(query_vec).limit(top_k)

        if status_vigencia:
            search = search.where(f"status_vigencia = '{status_vigencia}'")

        results = search.to_list()
        formatted = []
        for r in results:
            formatted.append({
                "chunk_id": r["chunk_id"],
                "nota_titulo": r["nota_titulo"],
                "secao_titulo": r["secao_titulo"],
                "arquivo_path": r["arquivo_path"],
                "categoria": r["categoria"],
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
