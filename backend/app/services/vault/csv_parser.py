"""Parser e sintetizador de dados tabulares (CSV) dos ANEXOS I e II para o Obsidian Vault."""

from pathlib import Path
from typing import Dict, List, Any
import pandas as pd


def _parse_br_float(val: Any) -> float:
    """Converte números formatados no padrão brasileiro (ex: '6,000' ou 6.0) para float."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return 0.0


DAY_TYPE_SUFFIXES = {
    "dia_util": "Dia Útil",
    "sabado": "Sábado",
    "domingo": "Domingo",
    "ponto_facultativo": "Ponto Facultativo",
}


def _build_hourly_columns(df: pd.DataFrame) -> Dict[str, tuple]:
    """Mapeia, para cada tipo de dia, as colunas de partidas/km horárias existentes no CSV."""
    hourly_columns: Dict[str, tuple] = {}
    for key, suffix in DAY_TYPE_SUFFIXES.items():
        p_cols, k_cols = [], []
        for c in df.columns:
            cs = str(c)
            if not cs.endswith(suffix):
                continue
            if "Partidas" in cs:
                p_cols.append((cs.split(" - ")[0].replace("Partidas ", "").strip(), c))
            elif "Quilometragem" in cs:
                k_cols.append((cs.split(" - ")[0].replace("Quilometragem ", "").strip(), c))
        p_cols.sort(key=lambda t: t[0])
        k_cols.sort(key=lambda t: t[0])
        hourly_columns[key] = (p_cols, k_cols)
    return hourly_columns


class CSVAttachmentParser:
    """Processa e sumariza os anexos CSV em formato Markdown legível para RAG."""

    @staticmethod
    def process_anexo_i(csv_path: Path, os_title: str) -> Dict[str, Any]:
        """Lê o ANEXO I (117 colunas de viagens/km) e sintetiza em dados estruturados."""
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # Identifica colunas de partidas/quilometragem por tipo de dia
        partidas_util_cols = [c for c in df.columns if "Partidas" in c and "Dia Útil" in c]
        km_util_cols = [c for c in df.columns if "Quilometragem" in c and "Dia Útil" in c]
        partidas_cols_by_type = {
            key: [c for c in df.columns if "Partidas" in c and c.endswith(suffix)]
            for key, suffix in DAY_TYPE_SUFFIXES.items()
        }
        km_cols_by_type = {
            key: [c for c in df.columns if "Quilometragem" in c and c.endswith(suffix)]
            for key, suffix in DAY_TYPE_SUFFIXES.items()
        }

        pico_manha_cols = [c for c in df.columns if "06h à 09h - Dia Útil" in c and "Partidas" in c]
        pico_noite_cols = [c for c in df.columns if "18h à 21h - Dia Útil" in c and "Partidas" in c]

        hourly_columns = _build_hourly_columns(df)

        services_summary: List[Dict[str, Any]] = []

        for _, row in df.iterrows():
            servico = str(row.get("Serviço", "")).strip()
            vista = str(row.get("Vista", "")).strip()
            consorcio = str(row.get("Consórcio", "")).strip()
            sentido = str(row.get("Sentido", "")).strip()
            extensao = _parse_br_float(row.get("Extensão", 0.0))

            tot_partidas_util = sum(_parse_br_float(row[c]) for c in partidas_util_cols)
            tot_km_util = sum(_parse_br_float(row[c]) for c in km_util_cols)

            partidas_sabado = int(round(sum(_parse_br_float(row[c]) for c in partidas_cols_by_type["sabado"])))
            partidas_domingo = int(round(sum(_parse_br_float(row[c]) for c in partidas_cols_by_type["domingo"])))
            partidas_ptfac = int(round(sum(_parse_br_float(row[c]) for c in partidas_cols_by_type["ponto_facultativo"])))
            km_ptfac = sum(_parse_br_float(row[c]) for c in km_cols_by_type["ponto_facultativo"])

            pico_manha = sum(_parse_br_float(row[c]) for c in pico_manha_cols)
            pico_noite = sum(_parse_br_float(row[c]) for c in pico_noite_cols)

            # Distribuição horária por tipo de dia (14 faixas cada)
            hourly = {
                key: [
                    {
                        "hora": slot,
                        "partidas": int(round(_parse_br_float(row[p]))),
                        "km": round(_parse_br_float(row[k]), 2),
                    }
                    for (slot, p), (_, k) in zip(p_cols, k_cols)
                ]
                for key, (p_cols, k_cols) in hourly_columns.items()
            }

            services_summary.append({
                "servico": servico,
                "vista": vista,
                "consorcio": consorcio,
                "sentido": sentido,
                "extensao_km": round(extensao, 3),
                "partidas_dia_util": int(round(tot_partidas_util)),
                "km_dia_util": round(tot_km_util, 2),
                "partidas_sabado": partidas_sabado,
                "partidas_domingo": partidas_domingo,
                "partidas_ponto_facultativo": partidas_ptfac,
                "km_ponto_facultativo": round(km_ptfac, 2),
                "pico_manha_partidas": int(round(pico_manha)),
                "pico_noite_partidas": int(round(pico_noite)),
                "hourly": hourly,
            })

        # Geração do Markdown sumarizado
        md_lines = [
            f"# ANEXO I — Resumo do Planejamento Operacional de Viagens",
            f"",
            f"**OS de Referência:** [[{os_title}]]  ",
            f"**Total de Serviços/Linhas Analisados:** {len(services_summary)}  ",
            f"",
            f"Este documento sumariza a grade horária e quilometragens das linhas municipais, consolidando os 4 tipos de dia (Dia Útil, Sábado, Domingo e Ponto Facultativo).",
            f"",
        ]

        # Agrupa por Consórcio
        df_summary = pd.DataFrame(services_summary)
        if not df_summary.empty:
            for consorcio, group in df_summary.groupby("consorcio"):
                md_lines.append(f"## Consórcio {consorcio}")
                md_lines.append("")
                md_lines.append(
                    "| Linha | Vista | Sentido | Ext. (km) | Viagens Dia Útil | Km Dia Útil | "
                    "Viagens Sáb | Viagens Dom | Viagens Pt. Fac. | Pico Manhã | Pico Noite |"
                )
                md_lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
                for _, item in group.iterrows():
                    md_lines.append(
                        f"| **{item['servico']}** | {item['vista']} | {item['sentido']} | {item['extensao_km']} | "
                        f"{item['partidas_dia_util']} | {item['km_dia_util']} | {item['partidas_sabado']} | "
                        f"{item['partidas_domingo']} | {item['partidas_ponto_facultativo']} | "
                        f"{item['pico_manha_partidas']} | {item['pico_noite_partidas']} |"
                    )
                md_lines.append("")

                # Resumo em linguagem natural por linha (melhora embedding semântico)
                md_lines.append(f"### Resumo por Linha — Consórcio {consorcio}")
                md_lines.append("")
                for _, item in group.iterrows():
                    sentido_info = f", Sentido: {item['sentido']}" if item['sentido'] and item['sentido'] != "N/A" else ""
                    km_info = f", com {item['km_dia_util']:.2f} km percorridos" if item['km_dia_util'] > 0 else ""
                    viagens_info = f" e {item['partidas_dia_util']} viagens" if item['partidas_dia_util'] > 0 else ""
                    pico_info = ""
                    if item['pico_manha_partidas'] > 0 or item['pico_noite_partidas'] > 0:
                        pico_parts = []
                        if item['pico_manha_partidas'] > 0:
                            pico_parts.append(f"{item['pico_manha_partidas']} partidas no pico da manhã")
                        if item['pico_noite_partidas'] > 0:
                            pico_parts.append(f"{item['pico_noite_partidas']} partidas no pico da noite")
                        pico_info = f". Pico: {', '.join(pico_parts)}"

                    md_lines.append(
                        f"A linha **{item['servico']}** (Vista: {item['vista']}{sentido_info}, "
                        f"Consórcio: {consorcio}) possui extensão de {item['extensao_km']:.3f} km"
                        f"{viagens_info}{km_info} em dia útil{pico_info}."
                    )
                    md_lines.append("")

        return {
            "markdown_content": "\n".join(md_lines),
            "services": services_summary,
            "total_services": len(services_summary),
        }

    @staticmethod
    def process_anexo_ii(csv_path: Path, os_title: str) -> Dict[str, Any]:
        """Lê o ANEXO II (Itinerários Alternativos) e gera tabela categorizada."""
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        desvios: List[Dict[str, Any]] = []

        for _, row in df.iterrows():
            desvios.append({
                "servico": str(row.get("Serviço", "")).strip(),
                "vista": str(row.get("Vista", "")).strip(),
                "consorcio": str(row.get("Consórcio", "")).strip(),
                "sentido": str(row.get("Sentido", "")).strip(),
                "extensao_km": _parse_br_float(row.get("Extensão", 0.0)),
                "evento": str(row.get("Evento", "")).strip(),
                "descricao": str(row.get("Descrição", "")).strip(),
                "ativacao": str(row.get("Ativação", "")).strip(),
            })

        md_lines = [
            f"# ANEXO II — Itinerários Alternativos e Desvios Operacionais",
            f"",
            f"**OS de Referência:** [[{os_title}]]  ",
            f"**Total de Desvios Cadastrados:** {len(desvios)}  ",
            f"",
            f"Tabela de desvios operacionais autorizados para eventos, feiras livres, interdições e dias de lazer.",
            f"",
            f"| Linha | Consórcio | Sentido | Evento | Descrição do Desvio | Extensão (km) | Ativação |",
            f"|---|---|---|---|---|---|---|",
        ]

        for d in desvios:
            md_lines.append(
                f"| **{d['servico']}** | {d['consorcio']} | {d['sentido']} | `{d['evento']}` | "
                f"{d['descricao']} | {d['extensao_km']:.3f} | {d['ativacao']} |"
            )

        return {
            "markdown_content": "\n".join(md_lines),
            "desvios": desvios,
            "total_desvios": len(desvios),
        }


csv_parser = CSVAttachmentParser()
