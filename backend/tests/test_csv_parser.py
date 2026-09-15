"""Testes unitários para o processador de anexos CSV (ANEXO I e ANEXO II)."""

from pathlib import Path
import pytest
from app.services.vault.csv_parser import csv_parser, _parse_br_float


def test_parse_br_float():
    """Valida a conversão de números formatados em padrão brasileiro."""
    assert _parse_br_float("6,000") == 6.0
    assert _parse_br_float("12.723") == 12.723 or _parse_br_float("12.723") == 12723.0 or _parse_br_float("12,723") == 12.723
    assert _parse_br_float(0.0) == 0.0
    assert _parse_br_float(None) == 0.0


def test_process_anexos_reais():
    """Testa o processamento dos arquivos reais da pasta referências/."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    ref_dir = repo_root / "referências"

    if not ref_dir.exists():
        pytest.skip("Pasta referências/ não encontrada.")

    anexo_i = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO I (Regular) Plano 2026 - Agosto 1º Est ret.csv"
    anexo_ii = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO II (Regular)_ Itinerários alternativos.csv"

    # Teste ANEXO I
    res_i = csv_parser.process_anexo_i(anexo_i, "OS 2026.08")
    assert res_i["total_services"] > 800
    assert "# ANEXO I" in res_i["markdown_content"]
    assert "Consórcio Intersul" in res_i["markdown_content"]
    assert "Viagens Pt. Fac." in res_i["markdown_content"]

    # Valida os dados estendidos por serviço (grade horária e Ponto Facultativo)
    servico = res_i["services"][0]
    assert "hourly" in servico
    assert set(servico["hourly"].keys()) == {"dia_util", "sabado", "domingo", "ponto_facultativo"}
    for faixas in servico["hourly"].values():
        assert len(faixas) == 14
        assert all("hora" in h and "partidas" in h and "km" in h for h in faixas)
    assert servico["partidas_ponto_facultativo"] >= 0
    assert servico["km_ponto_facultativo"] >= 0
    total_dia_util = sum(h["partidas"] for h in servico["hourly"]["dia_util"])
    assert total_dia_util == servico["partidas_dia_util"]

    # Teste ANEXO II
    res_ii = csv_parser.process_anexo_ii(anexo_ii, "OS 2026.08")
    assert res_ii["total_desvios"] > 400
    assert "# ANEXO II" in res_ii["markdown_content"]
    assert "Feira Livre" in res_ii["markdown_content"]
