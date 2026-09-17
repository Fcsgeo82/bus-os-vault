"""Testes do serviço de geração e sincronização de Hubs de Linha com dados reais."""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from app.services.vault.vault_writer import VaultWriter
from app.services.vault.csv_parser import csv_parser
from app.services.vault.line_hub_service import line_hub_service
import app.services.vault.line_hub_service as lhs_module

SLOTS = [
    "00h à 01h", "01h à 02h", "02h à 03h", "03h à 04h", "04h à 05h",
    "05h à 06h", "06h à 09h", "09h à 12h", "12h à 15h", "15h à 18h",
    "18h à 21h", "21h à 22h", "22h à 23h", "23h à 24h",
]


def _hourly(partidas: int, km_por_partida: float) -> Dict[str, List[Dict[str, Any]]]:
    """Gera a grade horária sintética dos 4 tipos de dia (14 faixas cada)."""
    return {
        day_key: [
            {"hora": slot, "partidas": partidas, "km": round(partidas * km_por_partida, 2)}
            for slot in SLOTS
        ]
        for day_key in ["dia_util", "sabado", "domingo", "ponto_facultativo"]
    }


def _servico_sintetico(codigo: str, sentido: str, vista: str = "Terminal A - Terminal B") -> Dict[str, Any]:
    """Gera um item de serviço com a mesma estrutura do parser do ANEXO I."""
    return {
        "servico": codigo,
        "vista": vista,
        "consorcio": "Intersul",
        "sentido": sentido,
        "extensao_km": 10.0,
        "partidas_dia_util": 30,
        "km_dia_util": 300.0,
        "partidas_sabado": 20,
        "partidas_domingo": 10,
        "partidas_ponto_facultativo": 15,
        "km_ponto_facultativo": 150.0,
        "pico_manha_partidas": 6,
        "pico_noite_partidas": 4,
        "hourly": _hourly(5, 10.0),
    }


def _desvio_sintetico(codigo: str) -> Dict[str, Any]:
    return {
        "servico": codigo,
        "evento": "[desvio_feira]",
        "descricao": "Feira Livre",
        "extensao_km": 8.865,
        "ativacao": "Automática.",
    }


def _muda_vault(tmp_path, monkeypatch) -> Path:
    """Aponta o serviço de hubs para um vault temporário isolado."""
    vault = tmp_path / "vault"
    monkeypatch.setattr(lhs_module.settings, "VAULT_DIR", vault)
    monkeypatch.setattr(lhs_module, "vault_writer", VaultWriter(vault_path=vault))
    return vault


def test_group_services_consolida_sentidos():
    """Valida o agrupamento de serviços por código de linha."""
    services = [
        _servico_sintetico("006", "Ida"),
        _servico_sintetico("006", "Volta"),
        _servico_sintetico("104", "Circular"),
    ]
    grouped = line_hub_service._group_services(services)
    assert set(grouped.keys()) == {"006", "104"}
    assert set(grouped["006"]["sentidos"].keys()) == {"Ida", "Volta"}
    assert grouped["104"]["sentidos"]["Circular"]["vista"] == "Terminal A - Terminal B"


def test_generate_hub_content_estrutura_real():
    """Valida o conteúdo do hub: seções, grade horária, desvios e links sem extensão."""
    linha_006 = {
        "vista": "Silvestre - Castelo",
        "consorcio": "Intersul",
        "sentidos": {"Ida": _servico_sintetico("006", "Ida", vista="Silvestre - Castelo")},
    }
    eventos = [
        {"title": "Evento Teste", "filename": "NOTA-2026.08-01-AJU-Intersul", "linhas_afetadas": ["006"]},
        {"title": "Evento Teste 2", "filename": "NOTA-2026.08-02-INC-Desvios.md", "linhas_afetadas": ["006"]},
    ]

    meta, content = line_hub_service._generate_hub_content(
        "006",
        linha_006,
        [_desvio_sintetico("006")],
        eventos,
        "174 - OS 2026.08 - Agosto 2º Estudo [ret4]",
        "2026-08-16",
    )

    assert meta["schema_version"] == 2
    assert meta["uid"] == "linha-006"
    assert meta["codigo_linha"] == "006"
    assert meta["vista"] == "Silvestre - Castelo"
    assert meta["os_origem"] == "[[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]"
    assert "tipo/municipal" in meta["tags"]

    assert "## Planejamento Operacional de Viagens" in content
    assert "### Ida" in content
    assert "| Dia Útil | 30 | 300.0 |" in content
    assert "#### Distribuição Horária" in content
    assert "| 06h à 09h | 5 | 50.0 |" in content
    assert "## Itinerários Alternativos e Desvios" in content
    assert "`[desvio_feira]`" in content

    secao_eventos = content.split("## Notas de Eventos Vinculadas")[1]
    assert "[[NOTA-2026.08-01-AJU-Intersul]]" in secao_eventos
    assert "[[NOTA-2026.08-02-INC-Desvios]]" in secao_eventos
    assert ".md]]" not in secao_eventos


def test_sync_hubs_for_os_atualiza_e_remove_orfaos(tmp_path, monkeypatch):
    """Valida a sincronização: criação, atualização e remoção de hubs órfãos."""
    vault = _muda_vault(tmp_path, monkeypatch)

    # Preparado: hub órfão existente que não pertence à OS
    linhas_dir = vault / "02_Linhas_e_Servicos"
    linhas_dir.mkdir(parents=True, exist_ok=True)
    (linhas_dir / "Linha 999.md").write_text("---\ncodigo_linha: '999'\n---\n", encoding="utf-8")

    services = [
        _servico_sintetico("006", "Ida"),
        _servico_sintetico("006", "Volta"),
        _servico_sintetico("104", "Circular"),
    ]
    desvios = [_desvio_sintetico("006")]
    eventos = [{"title": "Ev", "filename": "NOTA-X.md", "linhas_afetadas": ["006"]}]

    res = line_hub_service.sync_hubs_for_os(
        "OS 174",
        "2026-08-16",
        services,
        desvios,
        eventos,
        remove_orphans=True,
    )
    assert res["total_hubs"] == 2
    assert res["criados"] == 2
    assert res["orfaos_removidos"] == 1
    assert (linhas_dir / "Linha 006.md").exists()
    assert (linhas_dir / "Linha 104.md").exists()
    assert not (linhas_dir / "Linha 999.md").exists()

    conteudo_006 = (linhas_dir / "Linha 006.md").read_text(encoding="utf-8")
    assert "schema_version: 2" in conteudo_006
    assert "[[NOTA-X]]" in conteudo_006 and "NOTA-X.md]]" not in conteudo_006

    # Segunda execução: atualiza os hubs existentes, sem novos órfãos
    res2 = line_hub_service.sync_hubs_for_os(
        "OS 174",
        "2026-08-16",
        services,
        desvios,
        eventos,
        remove_orphans=True,
    )
    assert res2["atualizados"] == 2
    assert res2["criados"] == 0


def test_sync_sem_anexos_nao_apaga_hubs(tmp_path, monkeypatch):
    """Ingestão só com eventos não deve remover hubs (sem manifest completo de linhas)."""
    vault = _muda_vault(tmp_path, monkeypatch)
    linhas_dir = vault / "02_Linhas_e_Servicos"
    linhas_dir.mkdir(parents=True, exist_ok=True)
    (linhas_dir / "Linha 104.md").write_text("# Linha 104 — dados reais\n", encoding="utf-8")

    eventos = [{"title": "Ev", "filename": "NOTA-X.md", "linhas_afetadas": ["104"]}]
    res = line_hub_service.sync_hubs_for_os("OS 999", "2026-09-01", [], [], eventos)
    assert res["criados"] == 0
    assert res["orfaos_removidos"] == 0
    # Hub existente não é sobrescrito por ser apenas citado em evento
    assert (linhas_dir / "Linha 104.md").exists()
    assert "# Linha 104 — dados reais" in (linhas_dir / "Linha 104.md").read_text(encoding="utf-8")


def test_sync_event_only_atualiza_hub_para_os_mais_recente(tmp_path, monkeypatch):
    """Hub com dados reais da OS antiga, citado só em evento da OS nova, passa a representar
    a OS mais recente preservando a grade operacional e o histórico."""
    vault = _muda_vault(tmp_path, monkeypatch)
    linhas_dir = vault / "02_Linhas_e_Servicos"

    # OS antiga com grade real da linha 006
    res = line_hub_service.sync_hubs_for_os(
        "174 - OS 2026.08 - Agosto 2º Estudo [ret4]",
        "2026-08-16",
        [_servico_sintetico("006", "Ida"), _servico_sintetico("006", "Volta")],
        [],
        [],
    )
    assert res["criados"] == 1
    hub = (linhas_dir / "Linha 006.md").read_text(encoding="utf-8")
    assert "[[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]" in hub

    # OS mais recente toca a linha apenas via nota de evento (sem grade no ANEXO I)
    evento_novo = {
        "title": "Inclusão de itinerários alternativos",
        "filename": "NOTA-2026.09-01-INC-006.md",
        "linhas_afetadas": ["006"],
    }
    res2 = line_hub_service.sync_hubs_for_os(
        "178 - OS 2026.09 - Setembro 1º Estudo",
        "2026-09-03",
        [],
        [],
        [evento_novo],
    )
    assert res2["criados"] == 0
    assert res2["atualizados"] == 1

    hub2 = (linhas_dir / "Linha 006.md").read_text(encoding="utf-8")

    # Proveniência migra para a OS mais recente, mas a grade real é preservada
    assert "os_origem: '[[178 - OS 2026.09 - Setembro 1º Estudo]]'" in hub2
    assert "| Dia Útil | 30 | 300.0 |" in hub2
    assert "Distribuição Horária" in hub2

    # Histórico mantido: as duas OS relacionadas e a nova nota de evento
    secao_os = hub2.split("## Ordens de Serviço Relacionadas")[1]
    secao_os = secao_os.split("## Notas de Eventos Vinculadas")[0]
    assert "[[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]" in secao_os
    assert "[[178 - OS 2026.09 - Setembro 1º Estudo]]" in secao_os
    assert "[[NOTA-2026.09-01-INC-006]]" in hub2
    assert "NOTA-2026.09-01-INC-006.md]]" not in hub2

    # Idempotência: segunda execução com a mesma OS não altera nada
    res3 = line_hub_service.sync_hubs_for_os(
        "178 - OS 2026.09 - Setembro 1º Estudo",
        "2026-09-03",
        [],
        [],
        [evento_novo],
    )
    assert res3["atualizados"] == 0
    assert (linhas_dir / "Linha 006.md").read_text(encoding="utf-8") == hub2


def test_detach_hub_references_apos_exclusao(tmp_path, monkeypatch):
    """Excluir uma OS remove suas referências dos hubs e promove a OS mais recente restante."""
    vault = _muda_vault(tmp_path, monkeypatch)
    linhas_dir = vault / "02_Linhas_e_Servicos"

    # OS antiga com grade real
    line_hub_service.sync_hubs_for_os(
        "174 - OS 2026.08 - Agosto 2º Estudo [ret4]",
        "2026-08-16",
        [_servico_sintetico("006", "Ida"), _servico_sintetico("006", "Volta")],
        [],
        [],
    )

    # OS recente (só via evento) migra a proveniência
    evento_novo = {
        "title": "Inclusão de itinerários alternativos",
        "filename": "NOTA-2026.09-01-INC-006.md",
        "linhas_afetadas": ["006"],
    }
    line_hub_service.sync_hubs_for_os(
        "178 - OS 2026.09 - Setembro 1º Estudo",
        "2026-09-03",
        [],
        [],
        [evento_novo],
    )
    hub = (linhas_dir / "Linha 006.md").read_text(encoding="utf-8")
    assert "os_origem: '[[178 - OS 2026.09 - Setembro 1º Estudo]]'" in hub

    # Exclusão da OS recente: origem volta para a 174 e a nota é removida
    alterados = line_hub_service.detach_hub_references(
        "178 - OS 2026.09 - Setembro 1º Estudo",
        {"NOTA-2026.09-01-INC-006"},
    )
    assert alterados == 1

    hub2 = (linhas_dir / "Linha 006.md").read_text(encoding="utf-8")
    assert "os_origem: '[[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]'" in hub2
    assert "| Dia Útil | 30 | 300.0 |" in hub2  # grade preservada
    assert "[[NOTA-2026.09-01-INC-006]]" not in hub2
    assert "[[178 - OS 2026.09 - Setembro 1º Estudo]]" not in hub2

    # Idempotência: segunda execução não altera nada
    assert line_hub_service.detach_hub_references(
        "178 - OS 2026.09 - Setembro 1º Estudo",
        {"NOTA-2026.09-01-INC-006"},
    ) == 0


def test_generate_hub_content_hourly_sabado_ausente_nao_estoura(tmp_path, monkeypatch):
    """CSV sem colunas horárias de Sábado não deve estourar IndexError no hub (issue #ingest-500)."""
    hora_util = [
        {"hora": slot, "partidas": 5, "km": 50.0}
        for slot in SLOTS
    ]
    servico_sem_sabado = _servico_sintetico("006", "Ida")
    servico_sem_sabado["hourly"] = {
        "dia_util": hora_util,
        "sabado": [],
        "domingo": [{} for _ in SLOTS],
        "ponto_facultativo": [{} for _ in SLOTS],
    }
    linha = {
        "vista": "Terminal A - Terminal B",
        "consorcio": "Intersul",
        "sentidos": {"Ida": servico_sem_sabado},
    }

    meta, content = line_hub_service._generate_hub_content(
        "006",
        linha,
        [],
        [],
        "OS 180",
        "2026-10-01",
    )

    assert "#### Distribuição Horária" in content
    assert "| 00h à 01h | 5 | 50.0 |" in content
    assert content.count("| 00h à 01h ") == 1


def test_sync_hubs_for_os_nao_estoura_com_anexo_tipo_dia_incompleto(tmp_path, monkeypatch):
    """Ingestão com ANEXO I de colunas incompletas continua salvando a OS (hub não aborta)."""
    vault = _muda_vault(tmp_path, monkeypatch)

    service = _servico_sintetico("006", "Ida")
    service["hourly"] = {
        "dia_util": [{"hora": slot, "partidas": 5, "km": 50.0} for slot in SLOTS],
        "sabado": [],
        "domingo": [],
        "ponto_facultativo": [],
    }

    res = line_hub_service.sync_hubs_for_os(
        "OS 180",
        "2026-10-01",
        [service],
        [],
        [],
    )
    assert res["criados"] == 1
    hub = (vault / "02_Linhas_e_Servicos" / "Linha 006.md").read_text(encoding="utf-8")
    assert "Distribuição Horária" in hub


def test_sync_hubs_os_174_dados_reais(tmp_path, monkeypatch):
    """Gera hubs para todas as 435 linhas da OS 174 a partir dos CSVs reais de referência."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    ref_dir = repo_root / "referências"
    if not ref_dir.exists():
        pytest.skip("Pasta referências/ não encontrada.")

    anexo_i = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO I (Regular) Plano 2026 - Agosto 1º Est ret.csv"
    anexo_ii = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO II (Regular)_ Itinerários alternativos.csv"

    vault = _muda_vault(tmp_path, monkeypatch)

    parsed_i = csv_parser.process_anexo_i(anexo_i, "OS 174")
    parsed_ii = csv_parser.process_anexo_ii(anexo_ii, "OS 174")

    res = line_hub_service.sync_hubs_for_os(
        "174 - OS 2026.08 - Agosto 2º Estudo [ret4]",
        "2026-08-16",
        parsed_i["services"],
        parsed_ii["desvios"],
        [],
        remove_orphans=True,
    )
    assert res["total_hubs"] == 435
    assert res["criados"] == 435

    hubs = list((vault / "02_Linhas_e_Servicos").glob("*.md"))
    assert len(hubs) == 435

    conteudo_006 = (vault / "02_Linhas_e_Servicos" / "Linha 006.md").read_text(encoding="utf-8")
    assert "Silvestre - Castelo" in conteudo_006
    assert "Distribuição Horária" in conteudo_006
    assert "Partidas Pto. Fac." in conteudo_006

    conteudo_104 = (vault / "02_Linhas_e_Servicos" / "Linha 104.md").read_text(encoding="utf-8")
    assert "Itinerários Alternativos e Desvios" in conteudo_104