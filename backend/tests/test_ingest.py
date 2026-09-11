"""Testes unitários e de integração para o endpoint de ingestão de OS."""

import json
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_ingest_nova_os_e_sincronizacao_rag():
    """Testa o cadastro de uma nova OS com notas de eventos e validação da busca no RAG."""
    payload_data = {
        "title": "180 - OS 2026.10 - Outubro 1º Estudo",
        "tipo_os": "Normal",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/10",
        "processo_rio": "000399.009999/2026-01",
        "despacho": "Despacho 998877",
        "inicio_vigencia": "2026-10-01",
        "notas_eventos": [
            {
                "title": "Inclusão da Linha Experimental LECD999",
                "tipo_evento": "Inclusão",
                "objeto_afetado": ["Linhas/Serviços", "Planejamento de Viagens"],
                "linhas_afetadas": ["LECD999"],
                "consorcios": ["Intersul"],
                "descricao": "Criação de serviço experimental LECD999 para ligação rápida entre terminais.",
                "justificativa": "Estudo de viabilidade de nova rota expressa.",
            }
        ],
    }

    form_data = {
        "payload": json.dumps(payload_data),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/os/ingest", data=form_data)

    assert response.status_code == 201
    res_json = response.json()
    assert res_json["status"] == "success"
    assert res_json["total_notas_criadas"] == 1
    assert "180 - OS 2026.10" in res_json["os_title"]

    # Verifica se a nota da OS foi criada no Vault
    os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{payload_data['title']}.md"
    assert os_file.exists()

    # Verifica se a busca no RAG encontra a nova linha criada
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        search_res = await ac.post("/api/rag/search", json={"query": "LECD999", "top_k": 3})

    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] > 0
    assert any("LECD999" in r["trecho"] or "LECD999" in r["nota_titulo"] for r in search_data["results"])
