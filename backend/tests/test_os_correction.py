"""Testes do módulo de correção de Ordens de Serviço (retitulação e propagação)."""

import json
from pathlib import Path

import pytest
import frontmatter
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings


def _create_simulated_anexo_artifacts(os_slug: str, os_title: str) -> None:
    """Cria pasta de anexo Markdown e diretório de CSVs simulando um anexo persistido."""
    anexo_dir = settings.VAULT_DIR / "03_Anexos" / os_slug
    anexo_dir.mkdir(parents=True, exist_ok=True)
    anexo_nota = anexo_dir / "ANEXO_I_Viagens_Resumo.md"
    anexo_nota.write_text(
        "---\n"
        f"uid: os-{os_slug}-anexo-i\n"
        f"title: ANEXO I — Viagens ({os_title})\n"
        f"os_origem: '[[{os_title}]]'\n"
        "schema_version: 1\n"
        "---\n\n"
        "# ANEXO I — Viagens\n\n"
        f"**OS de Referência:** [[{os_title}]]  \n",
        encoding="utf-8",
    )

    att_dir = settings.DATA_DIR / "attachments" / os_slug
    att_dir.mkdir(parents=True, exist_ok=True)
    (att_dir / "anexo-i.csv").write_text("servico;vista\n1;teste\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_corrigir_titulo_renomeia_artefatos_vinculados():
    """Alterar o título da OS deve renomear arquivo, nota de evento, hub, anexo e CSVs."""
    old_title = "181 - OS 2026.10 - Outubro 1º Estudo"
    new_title = "180 - OS 2026.10 - Outubro 1º Estudo"
    old_slug = "181-os-2026-10-outubro-1o-estudo"
    new_slug = "180-os-2026-10-outubro-1o-estudo"

    payload_data = {
        "title": old_title,
        "tipo_os": "Normal",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/10",
        "processo_rio": "000399.005555/2026-01",
        "inicio_vigencia": "2026-10-01",
        "notas_eventos": [
            {
                "title": "Inclusão da Linha Experimental LECD777",
                "tipo_evento": "Inclusão",
                "objeto_afetado": ["Linhas/Serviços"],
                "linhas_afetadas": ["LECD777"],
                "consorcios": ["Intersul"],
                "descricao": "Criação de serviço experimental LECD777 para validar correção.",
                "justificativa": "Teste automatizado.",
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/os/ingest", data={"payload": json.dumps(payload_data)})
    assert ingest_res.status_code == 201
    old_uid = ingest_res.json()["os_uid"]

    os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{old_title}.md"
    assert os_file.exists()
    nota_file = next(iter((settings.VAULT_DIR / "01_Notas_de_Eventos").glob("NOTA-2026-10-*.md")))
    hub_file = settings.VAULT_DIR / "02_Linhas_e_Servicos" / "Linha LECD777.md"
    assert hub_file.exists()

    _create_simulated_anexo_artifacts(old_slug, old_title)
    anexo_nota = settings.VAULT_DIR / "03_Anexos" / old_slug / "ANEXO_I_Viagens_Resumo.md"
    assert anexo_nota.exists()

    # Corrige o número da OS (179-style) via endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        corr_res = await ac.post(f"/api/os/{old_uid}/correct", json={"title": new_title})
    assert corr_res.status_code == 200
    corr = corr_res.json()
    assert corr["status"] == "success"
    assert corr["new_uid"] == f"os-{new_slug}"
    assert corr["arquivos_renomeados"] >= 1
    assert corr["pastas_renomeadas"] >= 2
    assert corr["arquivos_atualizados"] >= 3

    # Verifica a nota mestra renomeada e com UID atualizado
    new_os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{new_title}.md"
    assert new_os_file.exists()
    assert not os_file.exists()
    with open(new_os_file, "r", encoding="utf-8") as fh:
        post = frontmatter.load(fh)
    assert post.metadata["uid"] == f"os-{new_slug}"
    assert post.metadata["title"] == new_title
    assert f"# {new_title}" in post.content

    # Verifica a nota de evento propagada
    with open(nota_file, "r", encoding="utf-8") as fh:
        ev_post = frontmatter.load(fh)
    assert ev_post.metadata["uid"].startswith(f"evt-{new_slug}-")
    assert new_title in ev_post.metadata["os_origem"]
    assert new_title in ev_post.content

    # Verifica o hub de linha propagado
    with open(hub_file, "r", encoding="utf-8") as fh:
        hub_post = frontmatter.load(fh)
    assert new_title in hub_post.metadata.get("os_origem", "")
    assert new_title in hub_post.content
    assert old_title not in hub_post.content

    # Verifica a pasta de anexos renomeada
    new_anexo_dir = settings.VAULT_DIR / "03_Anexos" / new_slug
    assert new_anexo_dir.is_dir()
    assert not (settings.VAULT_DIR / "03_Anexos" / old_slug).exists()
    renamed_nota = new_anexo_dir / "ANEXO_I_Viagens_Resumo.md"
    assert renamed_nota.exists()
    with open(renamed_nota, "r", encoding="utf-8") as fh:
        anexo_post = frontmatter.load(fh)
    assert anexo_post.metadata["uid"] == f"os-{new_slug}-anexo-i"
    assert new_title in anexo_post.metadata["os_origem"]

    # Verifica diretório de CSVs renomeado
    assert (settings.DATA_DIR / "attachments" / new_slug).is_dir()
    assert not (settings.DATA_DIR / "attachments" / old_slug).exists()

    # Limpeza: exclui a OS corrigida e os artefatos de teste
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_res = await ac.delete(f"/api/os/{corr['new_uid']}")
    assert del_res.status_code == 200
    if hub_file.exists():
        hub_file.unlink()


@pytest.mark.asyncio
async def test_corrigir_campo_escalar_atualiza_frontmatter():
    """Corrigir um campo simples (despacho) deve atualizar apenas o frontmatter."""
    title = "188 - OS 2026.10 - Outubro Teste Escalar"
    payload_data = {
        "title": title,
        "tipo_os": "Normal",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/10",
        "despacho": "Despacho 000999",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/os/ingest", data={"payload": json.dumps(payload_data)})
    assert ingest_res.status_code == 201
    os_uid = ingest_res.json()["os_uid"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        corr_res = await ac.post(f"/api/os/{os_uid}/correct", json={"despacho": "Despacho 111222"})
    assert corr_res.status_code == 200
    corr = corr_res.json()
    assert corr["pastas_renomeadas"] == 0
    assert corr["arquivos_renomeados"] == 0
    assert corr["new_uid"] == os_uid

    os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{title}.md"
    with open(os_file, "r", encoding="utf-8") as fh:
        post = frontmatter.load(fh)
    assert post.metadata["despacho"] == "Despacho 111222"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_res = await ac.delete(f"/api/os/{os_uid}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_corrigir_titulo_invalido_retorna_422():
    """Título inválido para nome de arquivo deve retornar 422 sem tocar no Vault."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        corr_res = await ac.post(
            "/api/os/uid-inexistente/correct",
            json={"title": "180 - OS 2026.10 - Outubro/Novo"},
        )
    assert corr_res.status_code == 422
    assert "caracteres inválidos" in corr_res.json()["detail"]


@pytest.mark.asyncio
async def test_corrigir_titulo_com_mesmo_slug_preserva_anexos():
    """Correção com slug idêntico (ex: '1o'→'1º') não pode apagar pastas de anexos/attachments."""
    old_title = "190 - OS 2026.10 - Outubro 1o Estudo"
    new_title = "190 - OS 2026.10 - Outubro 1º Estudo"
    os_slug = "190-os-2026-10-outubro-1o-estudo"

    payload_data = {
        "title": old_title,
        "tipo_os": "Normal",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/10",
        "inicio_vigencia": "2026-10-01",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/os/ingest", data={"payload": json.dumps(payload_data)})
    assert ingest_res.status_code == 201
    old_uid = ingest_res.json()["os_uid"]
    assert old_uid == f"os-{os_slug}"

    _create_simulated_anexo_artifacts(os_slug, old_title)
    anexo_dir = settings.VAULT_DIR / "03_Anexos" / os_slug
    attach_dir = settings.DATA_DIR / "attachments" / os_slug
    assert anexo_dir.is_dir()
    assert attach_dir.is_dir()

    # '1o' → '1º' mantém o mesmo slug (ambos "190-os-2026-10-outubro-1o-estudo")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        corr_res = await ac.post(f"/api/os/{old_uid}/correct", json={"title": new_title})
    assert corr_res.status_code == 200
    corr = corr_res.json()
    assert corr["pastas_renomeadas"] == 0
    assert corr["new_uid"] == old_uid

    # Pastas e CSVs não podem ser apagados quando o slug não muda
    assert anexo_dir.is_dir()
    assert attach_dir.is_dir()
    assert len(list(attach_dir.glob("*.csv")) or []) >= 1

    # Arquivo da OS deve ser renomeado (texto mudou, slug não)
    new_os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{new_title}.md"
    old_os_file = settings.VAULT_DIR / "00_Ordens_de_Servico" / f"{old_title}.md"
    assert new_os_file.exists()
    assert not old_os_file.exists()

    # Limpeza
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        del_res = await ac.delete(f"/api/os/{old_uid}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_corrigir_os_inexistente_retorna_404():
    """Corrigir uma OS que não existe deve retornar 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        corr_res = await ac.post(
            "/api/os/uid-que-nao-existe/correct",
            json={"despacho": "Despacho 999999"},
        )
    assert corr_res.status_code == 404