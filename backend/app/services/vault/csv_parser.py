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


class CSVAttachmentParser:
    """Processa e sumariza os anexos CSV em formato Markdown legível para RAG."""

    @staticmethod
    def process_anexo_i(csv_path: Path, os_title: str) -> Dict[str, Any]:
        """Lê o ANEXO I (117 colunas de viagens/km) e sintetiza em dados estruturados."""
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # Identifica colunas de partidas
        partidas_util_cols = [c for c in df.columns if "Partidas" in c and "Dia Útil" in c]
        km_util_cols = [c for c in df.columns if "Quilometragem" in c and "Dia Útil" in c]
        partidas_sab_cols = [c for c in df.columns if "Partidas" in c and "Sábado" in c]
        partidas_dom_cols = [c for c in df.columns if "Partidas" in c and "Domingo" in c]

        pico_manha_cols = [c for c in df.columns if "06h à 09h - Dia Útil" in c and "Partidas" in c]
        pico_noite_cols = [c for c in df.columns if "18h à 21h - Dia Útil" in c and "Partidas" in c]

        services_summary: List[Dict[str, Any]] = []

        for _, row in df.iterrows():
            servico = str(row.get("Serviço", "")).strip()
            vista = str(row.get("Vista", "")).strip()
            consorcio = str(row.get("Consórcio", "")).strip()
            sentido = str(row.get("Sentido", "")).strip()
            extensao = _parse_br_float(row.get("Extensão", 0.0))

            tot_partidas_util = sum(_parse_br_float(row[c]) for c in partidas_util_cols)
            tot_km_util = sum(_parse_br_float(row[c]) for c in km_util_cols)
            tot_partidas_sab = sum(_parse_br_float(row[c]) for c in partidas_sab_cols)
            tot_partidas_dom = sum(_parse_br_float(row[c]) for c in partidas_dom_cols)

            pico_manha = sum(_parse_br_float(row[c]) for c in pico_manha_cols)
            pico_noite = sum(_parse_br_float(row[c]) for c in pico_noite_cols)

            services_summary.append({
                "servico": servico,
                "vista": vista,
                "consorcio": consorcio,
                "sentido": sentido,
                "extensao_km": round(extensao, 3),
                "partidas_dia_util": int(round(tot_partidas_util)),
                "km_dia_util": round(tot_km_util, 2),
                "partidas_sabado": int(round(tot_partidas_sab)),
                "partidas_domingo": int(round(tot_partidas_dom)),
                "pico_manha_partidas": int(round(pico_manha)),
                "pico_noite_partidas": int(round(pico_noite)),
            })

        # Geração do Markdown sumarizado
        md_lines = [
            f"# ANEXO I — Resumo do Planejamento Operacional de Viagens",
            f"",
            f"**OS de Referência:** [[{os_title}]]  ",
            f"**Total de Serviços/Linhas Analisados:** {len(services_summary)}  ",
            f"",
            f"Este documento sumariza a grade horária e quilometragens das linhas municipais, consolidando os 4 tipos de dia.",
            f"",
        ]

        # Agrupa por Consórcio
        df_summary = pd.DataFrame(services_summary)
        if not df_summary.empty:
            for consorcio, group in df_summary.groupby("consorcio"):
                md_lines.append(f"## Consórcio {consorcio}")
                md_lines.append("")
                md_lines.append("| Linha | Vista | Sentido | Ext. (km) | Viagens Dia Útil | Km Dia Útil | Viagens Sáb | Viagens Dom | Pico Manhã | Pico Noite |")
                md_lines.append("|---|---|---|---|---|---|---|---|---|---|")
                for _, item in group.iterrows():
                    md_lines.append(
                        f"| **{item['servico']}** | {item['vista']} | {item['sentido']} | {item['extensao_km']} | "
                        f"{item['partidas_dia_util']} | {item['km_dia_util']} | {item['partidas_sabado']} | "
                        f"{item['partidas_domingo']} | {item['pico_manha_partidas']} | {item['pico_noite_partidas']} |"
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
