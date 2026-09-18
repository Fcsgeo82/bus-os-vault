"""Módulo para leitura e consulta de notas do Obsidian Vault."""

import re
from pathlib import Path
from typing import Any
import frontmatter
from app.core.config import settings


_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _category_from_folder(folder_name: str) -> str:
    """Mapeia nome da subpasta para categoria do grafo."""
    mapping = {
        "00_Ordens_de_Servico": "os",
        "01_Notas_de_Eventos": "evento",
        "02_Linhas_e_Servicos": "linha",
        "03_Anexos": "anexo",
    }
    return mapping.get(folder_name, "evento")


def _extract_wikilinks(content: str, title_to_uid: dict[str, str]) -> list[str]:
    """Extrai wikilinks [[...]] do conteúdo e resolve por título → UID."""
    links: list[str] = []
    seen: set[str] = set()
    for match in _WIKILINK_RE.finditer(content):
        raw = match.group(1).strip()
        uid = title_to_uid.get(raw, raw)
        if uid not in seen:
            seen.add(uid)
            links.append(uid)
    return links


def _extract_frontmatter_wikilinks(
    metadata: dict[str, Any], title_to_uid: dict[str, str]
) -> list[str]:
    """Extrai wikilinks de campos do frontmatter que contêm referências [[...]]."""
    link_fields = {"retifica_os", "retificada_por", "substitui_os", "os_origem"}
    links: list[str] = []
    seen: set[str] = set()
    for key, value in metadata.items():
        if key not in link_fields:
            continue
        if not isinstance(value, str):
            continue
        for match in _WIKILINK_RE.finditer(value):
            raw = match.group(1).strip()
            uid = title_to_uid.get(raw, raw)
            if uid not in seen:
                seen.add(uid)
                links.append(uid)
    return links


def list_all_notes() -> list[dict[str, Any]]:
    """
    Varre todas as pastas do vault e retorna uma lista de notas
    com uid, title, category e wikilinks extraídos do conteúdo.

    Etapas:
    1. Lê todos os arquivos .md e extrai uid/title do frontmatter
    2. Monta índice título → UID para resolução de wikilinks
    3. Para cada nota, extrai wikilinks do frontmatter e do corpo
    """
    vault = settings.VAULT_DIR
    if not vault.exists():
        return []

    folders = [
        "00_Ordens_de_Servico",
        "01_Notas_de_Eventos",
        "02_Linhas_e_Servicos",
        "03_Anexos",
    ]

    # Passo 1: Ler todas as notas e extrair metadados
    raw_notes: list[dict[str, Any]] = []
    title_to_uid: dict[str, str] = {}

    for folder in folders:
        folder_path = vault / folder
        if not folder_path.exists():
            continue
        category = _category_from_folder(folder)
        for md_file in sorted(folder_path.rglob("*.md")):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    doc = frontmatter.load(f)
            except Exception:
                continue
            meta = doc.metadata or {}
            uid = meta.get("uid", md_file.stem)
            title = meta.get("title", md_file.stem)
            title_to_uid[title] = uid
            raw_notes.append({
                "uid": uid,
                "title": title,
                "category": category,
                "content": doc.content or "",
                "metadata": meta,
            })

    # Passo 2: Extrair wikilinks resolvidos
    notes: list[dict[str, Any]] = []
    for note in raw_notes:
        wm_links = _extract_frontmatter_wikilinks(note["metadata"], title_to_uid)
        body_links = _extract_wikilinks(note["content"], title_to_uid)
        all_links = wm_links + [l for l in body_links if l not in wm_links]
        notes.append({
            "uid": note["uid"],
            "title": note["title"],
            "category": note["category"],
            "wikilinks": all_links,
        })

    return notes
