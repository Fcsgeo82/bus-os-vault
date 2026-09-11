"""Script CLI para indexação e sincronização manual do acervo."""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.rag.indexer import vault_indexer


def run_indexing():
    print("[INFO] Iniciando indexação do Obsidian Vault no LanceDB e BM25...")
    result = vault_indexer.index_entire_vault()
    print(f"[OK] Arquivos processados: {result['total_files']}")
    print(f"[OK] Chunks gerados: {result['total_chunks']}")
    print(f"[OK] Vetores salvos no LanceDB: {result['total_vectors_indexed']}")
    print("[OK] Indexação concluída com sucesso!")


if __name__ == "__main__":
    run_indexing()
