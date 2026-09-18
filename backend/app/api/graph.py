"""Endpoint para estrutura de grafo do vault."""

from typing import List, Dict, Any
from fastapi import APIRouter
from app.services.vault.vault_reader import list_all_notes

router = APIRouter(prefix="/api/vault", tags=["Vault"])


@router.get("/graph", response_model=List[Dict[str, Any]])
async def get_vault_graph():
    """Retorna a estrutura completa do grafo — todas as notas com UIDs, títulos, categorias e wikilinks."""
    return list_all_notes()
