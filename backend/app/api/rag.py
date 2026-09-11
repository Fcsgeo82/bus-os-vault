"""Endpoints da API para busca semântica híbrida e chat RAG."""

from fastapi import APIRouter, HTTPException
from app.models.rag_schema import (
    ChatQuery,
    ChatResponse,
    SearchQuery,
    SearchResponse,
)
from app.services.rag.hybrid_retriever import hybrid_retriever
from app.services.rag.generator import rag_generator
from app.services.rag.indexer import vault_indexer

router = APIRouter(prefix="/api/rag", tags=["RAG & Busca Inteligente"])


@router.post("/chat", response_model=ChatResponse)
async def chat_rag(payload: ChatQuery):
    """Realiza pergunta em linguagem natural sobre o acervo de Ordens de Serviço."""
    try:
        # 1. Recuperação Híbrida (LanceDB + BM25 com RRF)
        sources = hybrid_retriever.retrieve(
            query=payload.query,
            top_k=8,
            filters=payload.filters,
        )

        # 2. Geração com Gemini Flash (ou síntese local se sem chave)
        response = rag_generator.generate_response(
            query=payload.query,
            sources=sources,
            history=payload.history,
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar consulta RAG: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_vault(payload: SearchQuery):
    """Busca direta por trechos e notas relevantes sem invocação do LLM."""
    try:
        sources = hybrid_retriever.retrieve(
            query=payload.query,
            top_k=payload.top_k,
            filters=payload.filters,
        )
        return SearchResponse(total=len(sources), results=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca híbrida: {str(e)}")


@router.post("/sync")
async def sync_vault_index():
    """Força a sincronização e reindexação de todas as notas do cofre no LanceDB e BM25."""
    try:
        result = vault_indexer.index_entire_vault()
        return {
            "status": "success",
            "message": "Cofre reindexado com sucesso!",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar cofre: {str(e)}")
