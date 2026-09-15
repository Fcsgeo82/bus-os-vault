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
    os_uid = res_json["os_uid"]

    # Verifica se a nota da OS foi criada no Vault
    os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{payload_data['title']}.md"
    assert os_file.exists()

    # Verifica se o hub da linha do evento foi criado (linha só citada em evento)
    linha_file = settings.VAULT_DIR / "02_Linhas_e_Servicos" / "Linha LECD999.md"
    assert linha_file.exists()

    # Verifica se a busca no RAG encontra a nova linha criada
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        search_res = await ac.post("/api/rag/search", json={"query": "LECD999", "top_k": 3})

    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] > 0
    assert any("LECD999" in r["trecho"] or "LECD999" in r["nota_titulo"] for r in search_data["results"])

    # Limpeza: remove a OS criada e o hub de linha gerado para não poluir o cofre real
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_res = await ac.delete(f"/api/os/{os_uid}")
    assert del_res.status_code == 200
    if linha_file.exists():
        linha_file.unlink()


@pytest.mark.asyncio
async def test_excluir_os_e_artefatos_vinculados():
    """Testa a exclusão em cascata de uma OS: notas de eventos, anexos e CSVs."""
    # 1. Cria uma OS temporária com notas de eventos
    payload_data = {
        "title": "999 - OS 2026.09 - Estudo de Exclusão",
        "tipo_os": "Normal",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/09",
        "processo_rio": "000399.000000/2026-01",
        "inicio_vigencia": "2026-09-01",
        "notas_eventos": [
            {
                "title": "Ajuste operacional direcionado para exclusão",
                "tipo_evento": "Ajuste",
                "objeto_afetado": ["Linhas/Serviços"],
                "linhas_afetadas": ["104"],
                "consorcios": ["Intersul"],
                "descricao": "Evento criado para validar a exclusão em cascata.",
                "justificativa": "Teste automatizado.",
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/os/ingest", data={"payload": json.dumps(payload_data)})

    assert ingest_res.status_code == 201
    os_uid = ingest_res.json()["os_uid"]

    # 2. Confirma que os artefatos existem no Vault
    os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{payload_data['title']}.md"
    assert os_file.exists()
    event_files = list((settings.VAULT_DIR / "01_Notas_de_Eventos").glob("NOTA-2026-09-*.md"))
    assert any(f.exists() for f in event_files)

    # 3. Exclui a OS
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_res = await ac.delete(f"/api/os/{os_uid}")

    assert del_res.status_code == 200
    data = del_res.json()
    assert data["status"] == "success"
    assert data["notas_eventos_removidas"] >= 1

    # 4. Verifica que a OS mestra e os eventos foram removidos
    assert not os_file.exists()
    assert not any(f.exists() for f in event_files)

    # 5. Verifica 404 ao tentar consultar novamente
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        get_res = await ac.get(f"/api/os/{os_uid}")
        assert get_res.status_code == 404

    # 6. Verifica que a busca RAG não retorna mais a OS excluída
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        search_res = await ac.post(
            "/api/rag/search",
            json={"query": "999 Estudo Exclusão", "top_k": 8},
        )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert not any(
        "999 - OS" in r["trecho"] or "999 - OS" in r["nota_titulo"]
        for r in search_data["results"]
    )
