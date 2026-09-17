"""Serviço de geração e sincronização de Hubs de Linha com dados operacionais reais."""

import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

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

        def _hourly_entry(day_key: str, idx: int) -> Dict[str, Any]:
            """Retorna a faixa horária do tipo de dia, ou linha em branco se ausente/conflito de colunas."""
            day_list = hourly.get(day_key) or []
            return day_list[idx] if idx < len(day_list) else {}

        dia_util_entries = hourly.get("dia_util") or []
        for i, slot in enumerate(dia_util_entries):
            sab = _hourly_entry("sabado", i)
            dom = _hourly_entry("domingo", i)
            pf = _hourly_entry("ponto_facultativo", i)
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

    @staticmethod
    def _body_enumera_eventos(body: str, eventos: List[Dict[str, Any]]) -> bool:
        """True se o corpo do hub já enumera todas as notas de evento fornecidas."""
        if not eventos:
            return True
        secao = body.split("## Notas de Eventos Vinculadas", 1)
        secao_ev = secao[1] if len(secao) == 2 else ""
        for ev in eventos:
            link = str(ev.get("filename", "")).replace(".md", "")
            if link and f"[[{link}]]" not in secao_ev:
                return False
        return True

    @staticmethod
    def _data_iso(valor: str) -> str:
        """Normaliza uma data (ISO ou dd/mm/aaaa) para comparação lexicográfica; '0000-00-00' se vazia."""
        bruta = str(valor or "").strip()
        if not bruta:
            return "0000-00-00"
        if bruta.startswith("0000"):
            return bruta
        partes = bruta.split("/")
        if len(partes) == 3 and len(partes[2]) == 4:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return bruta

    @staticmethod
    def _vigencia_da_os(os_title: str) -> str:
        """Retorna a data de início de vigência de uma OS do cofre (vazia se não localizada)."""
        os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
        if not os_dir.exists():
            return ""
        for f in os_dir.glob("*.md"):
            try:
                head = f.read_text(encoding="utf-8-sig").split("---", 2)[1]
                meta = yaml.safe_load(head) or {}
            except (yaml.YAMLError, IndexError):
                continue
            if meta.get("title") == os_title:
                return str(meta.get("inicio_vigencia") or "")
        return ""

    def _merge_event_only_hub(
        self,
        target: Path,
        codigo: str,
        os_title: str,
        vigencia_inicio: Optional[str],
        eventos: List[Dict[str, Any]],
    ) -> bool:
        """Atualiza a proveniência de um hub existente para a OS mais recente que o
        referencia apenas via nota de evento, preservando a grade operacional real.

        Mantém o histórico: novas OS passam a constar em "Ordens de Serviço Relacionadas"
        e novas notas de evento são anexadas. Retorna False quando o hub já representa a
        OS mais recente (sem alterações) ou quando não é um hub válido.
        """
        text = target.read_text(encoding="utf-8-sig")
        parts = text.split("---", 2)
        if len(parts) < 3:
            return False
        try:
            meta: Dict[str, Any] = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return False
        body = parts[2] or ""

        novo_os_link = f"[[{os_title}]]"
        if meta.get("os_origem") == novo_os_link and self._body_enumera_eventos(body, eventos):
            return False

        marker = "## Ordens de Serviço Relacionadas"
        idx = body.find(marker)
        grid_part = body[:idx].rstrip() if idx != -1 else body.rstrip()

        oses_antigas: List[str] = []
        eventos_antigos: List[Dict[str, Any]] = []
        if idx != -1:
            restante = body[idx:]
            fim_os = restante.find("## Notas de Eventos Vinculadas")
            secao_os = restante[:fim_os] if fim_os != -1 else restante
            # Greedy por linha: preserva ']]' internos (ex: títulos com '[ret4]]]')
            oses_antigas = re.findall(r"- \[\[(.+)\]\]", secao_os)
            secao_ev = restante[fim_os:] if fim_os != -1 else ""
            eventos_antigos = [
                {"link": link, "title": titulo.strip()}
                for link, titulo in re.findall(r"- \[\[([^\]]+)\]\]:\s*(.*)", secao_ev)
            ]

        # Merge de ordens de serviço relacionadas (histórico + OS mais recente)
        ordens: List[str] = list(dict.fromkeys(oses_antigas + [os_title]))

        # Merge de notas de eventos por link, preservando o histórico
        eventos_por_link: Dict[str, str] = {
            ev["link"]: ev["title"] for ev in eventos_antigos
        }
        for ev in eventos:
            link = str(ev.get("filename", "")).replace(".md", "")
            if link:
                eventos_por_link[link] = str(ev.get("title", ""))
        eventos_merged = [
            {"link": link, "title": title} for link, title in eventos_por_link.items()
        ]

        meta = dict(meta)
        meta["os_origem"] = novo_os_link
        meta["data_atualizacao"] = date.today().isoformat()
        if vigencia_inicio:
            # Nunca regressa a vigência: o hub mantém a data mais recente entre atual e nova
            atual = str(meta.get("vigencia_inicio") or "")
            if self._data_iso(atual) >= self._data_iso(vigencia_inicio):
                pass
            else:
                meta["vigencia_inicio"] = vigencia_inicio

        corpo = grid_part.strip() + "\n\n## Ordens de Serviço Relacionadas\n"
        corpo += "\n".join(f"- [[{os}]]" for os in ordens) + "\n\n"
        corpo += "## Notas de Eventos Vinculadas\n"
        if eventos_merged:
            corpo += "\n".join(f"- [[{ev['link']}]]: {ev['title']}" for ev in eventos_merged)
        else:
            corpo += "Nenhuma nota de evento referenciada para esta linha na OS vigente."
        corpo += "\n"

        vault_writer.write_note("02_Linhas_e_Servicos", f"Linha {codigo}", meta, corpo)
        return True

    def detach_hub_references(self, os_title: str, event_links: Set[str]) -> int:
        """Remove referências a uma OS excluída dos hubs de linha e promove a próxima
        OS mais recente para `os_origem`, preservando a grade operacional.

        Retorna o número de hubs alterados.
        """
        target_link = f"[[{os_title}]]"
        hub_dir = settings.VAULT_DIR / "02_Linhas_e_Servicos"
        if not hub_dir.exists():
            return 0

        alterados = 0
        for hub_file in hub_dir.glob("*.md"):
            text = hub_file.read_text(encoding="utf-8-sig")
            parts = text.split("---", 2)
            if len(parts) < 3:
                continue
            try:
                meta: Dict[str, Any] = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                continue
            body = parts[2] or ""
            if target_link not in meta.get("os_origem", "") and target_link not in body:
                continue

            marker = "## Ordens de Serviço Relacionadas"
            idx = body.find(marker)
            grid_part = body[:idx].rstrip() if idx != -1 else body.rstrip()

            oses_antigas: List[str] = []
            eventos_por_link: Dict[str, str] = {}
            if idx != -1:
                restante = body[idx:]
                fim_os = restante.find("## Notas de Eventos Vinculadas")
                secao_os = restante[:fim_os] if fim_os != -1 else restante
                oses_antigas = re.findall(r"- \[\[(.+)\]\]", secao_os)
                secao_ev = restante[fim_os:] if fim_os != -1 else ""
                eventos_por_link = {
                    link: titulo.strip()
                    for link, titulo in re.findall(r"- \[\[([^\]]+)\]\]:\s*(.*)", secao_ev)
                }

            ordens = [os for os in oses_antigas if os != os_title]
            for link in list(eventos_por_link):
                if link in event_links:
                    del eventos_por_link[link]
            if ordens == oses_antigas and not (set(event_links) & set(eventos_por_link.keys())):
                continue

            # Sem nenhuma OS restante, o hub é órfão: remove o arquivo
            if not ordens:
                hub_file.unlink()
                alterados += 1
                continue

            novo_origem = ordens[0]
            meta = dict(meta)
            meta["os_origem"] = f"[[{novo_origem}]]"
            meta["data_atualizacao"] = date.today().isoformat()
            vigencia_restante = self._vigencia_da_os(novo_origem)
            if vigencia_restante:
                meta["vigencia_inicio"] = vigencia_restante

            corpo = grid_part.strip() + "\n\n## Ordens de Serviço Relacionadas\n"
            corpo += "\n".join(f"- [[{os}]]" for os in ordens) + "\n\n"
            corpo += "## Notas de Eventos Vinculadas\n"
            if eventos_por_link:
                corpo += "\n".join(
                    f"- [[{link}]]: {title}" for link, title in eventos_por_link.items()
                )
            else:
                corpo += "Nenhuma nota de evento referenciada para esta linha na OS vigente."
            corpo += "\n"

            codigo = hub_file.stem[len("Linha "):] if hub_file.stem.startswith("Linha ") else hub_file.stem
            vault_writer.write_note("02_Linhas_e_Servicos", f"Linha {codigo}", meta, corpo)
            alterados += 1
        return alterados

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
        # cria hub mínimo, ou — quando o hub já existe — atualiza a proveniência
        # para a OS mais recente preservando os dados operacionais reais.
        event_only_codes = sorted(set(eventos_by_line.keys()) - set(lines_data.keys()))
        for codigo in event_only_codes:
            target = settings.VAULT_DIR / "02_Linhas_e_Servicos" / f"Linha {codigo}.md"
            if not target.exists():
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
                continue
            if self._merge_event_only_hub(
                target,
                codigo,
                os_title,
                vigencia_inicio,
                eventos_by_line.get(codigo, []),
            ):
                atualizados += 1

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