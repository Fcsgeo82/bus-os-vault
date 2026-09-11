"""Testes dos endpoints da API FastAPI do Bus OS Vault."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Testa o endpoint de saúde operacional."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["vault_accessible"] is True


@pytest.mark.asyncio
async def test_list_os_endpoint():
    """Testa listagem de OS cadastradas."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/os")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) > 0
    assert "uid" in items[0]


@pytest.mark.asyncio
async def test_rag_search_endpoint():
    """Testa a rota de busca semântica do RAG."""
    payload = {
        "query": "alteração na linha 006",
        "top_k": 3,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/rag/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["results"]) > 0


@pytest.mark.asyncio
async def test_rag_chat_endpoint():
    """Testa o chat RAG com geração de resposta."""
    payload = {
        "query": "Quais desvios existem para a linha 104?",
        "history": [],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/rag/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["sources"]) > 0
