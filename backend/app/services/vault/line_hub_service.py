"""Serviço de geração e sincronização de Hubs de Linha com dados operacionais reais."""

from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from slugify import slugify

from app.core.config import settings
from app.services.vault.vault_writer import vault_writer

DAY_TYPE_LABELS = {
    "dia_util": "Dia Útil",
    "sabado": "Sábado",
    "domingo": "Domingo",
    "ponto_facultativo": "Ponto Facultativo",
}

_SENTIDO_ORDER = {"Ida": 0, "Volta": 1, "Circular": 2}


class LineHubService:
    """Constrói e sincroniza hubs de linha (02_Linhas_e_Servicos) a partir da OS e anexos."""

    def _group_services(self, services: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Agrupa os serviços do ANEXO I por código de linha, consolidando os sentidos."""
        lines: Dict[str, Dict[str, Any]] = {}
        for s in services:
            codigo = str(s["servico"]).strip()
            entry = lines.setdefault(
                codigo,
                {"vista": s["vista"], "consorcio": s["consorcio"], "sentidos": {}},
            )
            entry["sentidos"][s["sentido"]] = s
        return lines

    def _group_desvios(self, desvios: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa os desvios do ANEXO II por código de linha."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for d in desvios:
            grouped.setdefault(str(d["servico"]).strip(), []).append(d)
        return grouped

    def _group_eventos(self, eventos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa notas de evento (title, filename, linhas_afetadas) por código de linha."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for ev in eventos:
            for codigo in ev.get("linhas_afetadas") or []:
                grouped.setdefault(str(codigo).strip(), []).append(ev)
        return grouped

    @staticmethod
    def _sum_km(hourly: Dict[str, List[Dict[str, Any]]], day_key: str) -> float:
        """Soma as quilometragens horárias de um tipo de dia."""
        return round(sum(float(h.get("km") or 0) for h in hourly.get(day_key, [])), 2)

    def _render_sentido(self, sentido: str, s: Dict[str, Any]) -> List[str]:
        """Renderiza as seções de resumo e distribuição horária de um sentido."""
        lines: List[str] = []
        lines.append(f"### {sentido}")
        lines.append("")
        lines.append(f"**Extensão:** {s['extensao_km']} km  ")
        lines.append("")
        kms = {
            "dia_util": s["km_dia_util"],
            "sabado": self._sum_km(s["hourly"], "sabado"),
            "domingo": self._sum_km(s["hourly"], "domingo"),
            "ponto_facultativo": s["km_ponto_facultativo"],
        }
        lines.append("| Tipo de Dia | Viagens | Km |")
        lines.append("|---|---|---|")
        lines.append(f"| Dia Útil | {s['partidas_dia_util']} | {kms['dia_util']} |")
        lines.append(f"| Sábado | {s['partidas_sabado']} | {kms['sabado']} |")
        lines.append(f"| Domingo | {s['partidas_domingo']} | {kms['domingo']} |")
        lines.append(
            f"| Ponto Facultativo | {s['partidas_ponto_facultativo']} | {kms['ponto_facultativo']} |"
        )
        lines.append("| Pico Manhã (06h-09h) | {pico} | — |".format(pico=s["pico_manha_partidas"]))
        lines.append("| Pico Noite (18h-21h) | {pico} | — |".format(pico=s["pico_noite_partidas"]))
        lines.append("")
        lines.append("#### Distribuição Horária")
        lines.append("")
        lines.append(
            "| Faixa Horária | Partidas Dia Útil | Km Dia Útil | Partidas Sábado | Km Sábado | "
            "Partidas Domingo | Km Domingo | Partidas Pto. Fac. | Km Pto. Fac. |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        hourly = s["hourly"]
        for i, slot in enumerate(hourly.get("dia_util", [])):
            sab = hourly.get("sabado", [{} for _ in range(len(hourly["dia_util"]))])[i]
            dom = hourly.get("domingo", [{} for _ in range(len(hourly["dia_util"]))])[i]
            pf = hourly.get("ponto_facultativo", [{} for _ in range(len(hourly["dia_util"]))])[i]
            lines.append(
                f"| {slot['hora']} | {slot['partidas']} | {slot['km']} | "
                f"{sab.get('partidas', 0)} | {sab.get('km', 0)} | "
                f"{dom.get('partidas', 0)} | {dom.get('km', 0)} | "
                f"{pf.get('partidas', 0)} | {pf.get('km', 0)} |"
            )
        lines.append("")
        return lines

    def _generate_hub_content(
        self,
        codigo: str,
        line_data: Dict[str, Any],
        desvios: List[Dict[str, Any]],
        eventos: List[Dict[str, Any]],
        os_title: str,
        vigencia_inicio: Optional[str],
    ) -> Tuple[Dict[str, Any], str]:
        """Monta o frontmatter e o corpo Markdown de um hub de linha."""
        vista = str(line_data.get("vista") or "")
        consorcio = str(line_data.get("consorcio") or "")
        sentidos = line_data.get("sentidos") or {}
        vigencia = vigencia_inicio or "Sem data definida"

        meta: Dict[str, Any] = {
            "uid": f"linha-{slugify(codigo)}",
            "codigo_linha": codigo,
            "vista": vista,
            "consorcio": consorcio,
            "type": "linha_servico",
            "os_origem": f"[[{os_title}]]",
            "vigencia_inicio": vigencia,
            "data_atualizacao": date.today().isoformat(),
            "tags": [
                f"linha/{slugify(codigo)}",
                f"consorcio/{slugify(consorcio)}",
                "tipo/municipal",
            ],
            "schema_version": 2,
        }

        corpo: List[str] = []
        titulo = f"# Linha {codigo} — {vista}" if vista else f"# Linha {codigo}"
        corpo.append(titulo)
        corpo.append("")
        corpo.append(f"**Código do Serviço:** {codigo}  ")
        if consorcio:
            corpo.append(f"**Consórcio:** {consorcio}  ")
        corpo.append(f"**OS de Origem:** [[{os_title}]]  ")
        corpo.append(f"**Vigência:** {vigencia}  ")
        corpo.append("")
        corpo.append("---")
        corpo.append("")

        if sentidos:
            corpo.append("## Planejamento Operacional de Viagens")
            corpo.append("")
            ordered = sorted(sentidos.items(), key=lambda kv: _SENTIDO_ORDER.get(kv[0], 9))
            for sentido, s in ordered:
                corpo.extend(self._render_sentido(sentido, s))

        if desvios:
            corpo.append("---")
            corpo.append("")
            corpo.append("## Itinerários Alternativos e Desvios")
            corpo.append("")
            corpo.append("| Evento | Descrição | Extensão (km) | Ativação |")
            corpo.append("|---|---|---|---|")
            for d in desvios:
                corpo.append(
                    f"| `{d['evento']}` | {d['descricao']} | {d['extensao_km']} | {d['ativacao']} |"
                )
            corpo.append("")

        corpo.append("---")
        corpo.append("")
        corpo.append("## Ordens de Serviço Relacionadas")
        corpo.append(f"- [[{os_title}]]")
        corpo.append("")
        corpo.append("## Notas de Eventos Vinculadas")
        if eventos:
            for ev in eventos:
                ev_link = str(ev.get("filename", "")).replace(".md", "")
                corpo.append(f"- [[{ev_link}]]: {ev.get('title', '')}")
        else:
            corpo.append("Nenhuma nota de evento referenciada para esta linha na OS vigente.")
        corpo.append("")

        return meta, "\n".join(corpo).rstrip() + "\n"

    def sync_hubs_for_os(
        self,
        os_title: str,
        vigencia_inicio: Optional[str],
        anexo_i_services: List[Dict[str, Any]],
        anexo_ii_desvios: List[Dict[str, Any]],
        eventos: List[Dict[str, Any]],
        remove_orphans: bool = False,
    ) -> Dict[str, Any]:
        """Gera/atualiza hubs para todas as linhas da OS.

        `remove_orphans=True` remove hubs cujos códigos não constam nas linhas de origem
        da OS (operação de rebuild do cofre inteiro; desativado em ingestões rotineiras).
        """
        lines_data = self._group_services(anexo_i_services)
        desvios_by_line = self._group_desvios(anexo_ii_desvios)
        eventos_by_line = self._group_eventos(eventos)

        current_codes: Set[str] = set(lines_data.keys()) | set(eventos_by_line.keys())

        criados = 0
        atualizados = 0
        for codigo, data in lines_data.items():
            meta, content = self._generate_hub_content(
                codigo,
                data,
                desvios_by_line.get(codigo, []),
                eventos_by_line.get(codigo, []),
                os_title,
                vigencia_inicio,
            )
            target = settings.VAULT_DIR / "02_Linhas_e_Servicos" / f"Linha {codigo}.md"
            existe = target.exists()
            vault_writer.write_note("02_Linhas_e_Servicos", f"Linha {codigo}", meta, content)
            if existe:
                atualizados += 1
            else:
                criados += 1

        # Linhas citadas apenas em notas de evento (sem grade no ANEXO I):
        # cria hub mínimo apenas se ainda não existir (não sobrescreve hubs com dados reais)
        event_only_codes = sorted(set(eventos_by_line.keys()) - set(lines_data.keys()))
        for codigo in event_only_codes:
            target = settings.VAULT_DIR / "02_Linhas_e_Servicos" / f"Linha {codigo}.md"
            if target.exists():
                continue
            meta, content = self._generate_hub_content(
                codigo,
                {"vista": "", "consorcio": "", "sentidos": {}},
                [],
                eventos_by_line.get(codigo, []),
                os_title,
                vigencia_inicio,
            )
            vault_writer.write_note("02_Linhas_e_Servicos", f"Linha {codigo}", meta, content)
            criados += 1

        orfaos_removidos = 0
        if remove_orphans:
            lines_dir = settings.VAULT_DIR / "02_Linhas_e_Servicos"
            if lines_dir.exists():
                for f in lines_dir.glob("*.md"):
                    codigo = f.stem[len("Linha "):] if f.stem.startswith("Linha ") else f.stem
                    if codigo not in current_codes:
                        f.unlink()
                        orfaos_removidos += 1

        return {
            "total_hubs": len(current_codes),
            "criados": criados,
            "atualizados": atualizados,
            "orfaos_removidos": orfaos_removidos,
        }


line_hub_service = LineHubService()