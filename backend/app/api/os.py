"""Endpoints da API para consulta e visualização de notas do cofre Obsidian."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
import frontmatter
from app.core.config import settings

router = APIRouter(prefix="/api/os", tags=["Ordens de Serviço"])


def _read_markdown_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Carrega metadados e conteúdo de um arquivo Markdown."""
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    return {
        "metadata": post.metadata or {},
        "content": post.content,
        "filename": file_path.name,
        "relative_path": str(file_path.relative_to(settings.VAULT_DIR)).replace("\\", "/"),
    }


@router.get("", response_model=List[Dict[str, Any]])
async def list_ordens_de_servico():
    """Lista todas as Ordens de Serviço cadastradas no cofre."""
    os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
    if not os_dir.exists():
        return []

    results = []
    for f in sorted(os_dir.glob("*.md")):
        doc = _read_markdown_file(f)
        if doc:
            meta = doc["metadata"]
            results.append({
                "uid": meta.get("uid", f.stem),
                "title": meta.get("title", f.stem),
                "tipo_os": meta.get("tipo_os", "Normal"),
                "status_vigencia": meta.get("status_vigencia", "Vigente"),
                "ano_mes_referencia": meta.get("ano_mes_referencia", ""),
                "processo_rio": meta.get("processo_rio"),
                "despacho": meta.get("despacho"),
                "data_publicacao": meta.get("data_publicacao"),
                "inicio_vigencia": meta.get("inicio_vigencia"),
                "retifica_os": meta.get("retifica_os"),
                "tags": meta.get("tags", []),
                "filename": doc["filename"],
            })
    return results


@router.get("/{uid}")
async def get_ordem_de_servico(uid: str):
    """Retorna detalhes completos de uma OS e suas notas de evento vinculadas."""
    os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
    target_file = None
    for f in os_dir.glob("*.md"):
        doc = _read_markdown_file(f)
        if doc and doc["metadata"].get("uid") == uid:
            target_file = doc
            break

    if not target_file:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")

    # Busca notas de evento vinculadas a esta OS
    event_dir = settings.VAULT_DIR / "01_Notas_de_Eventos"
    linked_events = []
    os_title = target_file["metadata"].get("title", "")
    for f in event_dir.glob("*.md"):
        ev_doc = _read_markdown_file(f)
        if ev_doc:
            origem = ev_doc["metadata"].get("os_origem", "")
            if os_title in origem or uid in origem:
                linked_events.append({
                    "uid": ev_doc["metadata"].get("uid"),
                    "title": ev_doc["metadata"].get("title"),
                    "tipo_evento": ev_doc["metadata"].get("tipo_evento"),
                    "linhas_afetadas": ev_doc["metadata"].get("linhas_afetadas", []),
                    "filename": ev_doc["filename"],
                })

    target_file["eventos_vinculados"] = linked_events
    return target_file


@router.get("/notes/{uid}")
async def get_note_by_uid(uid: str):
    """Retorna qualquer nota do cofre (evento, linha ou anexo) pelo UID ou nome de arquivo."""
    for f in settings.VAULT_DIR.rglob("*.md"):
        doc = _read_markdown_file(f)
        if doc and (doc["metadata"].get("uid") == uid or f.stem == uid):
            return doc

    raise HTTPException(status_code=404, detail="Nota não encontrada no cofre")


@router.get("/lines/all")
async def list_lines():
    """Lista todos os Hubs de Linhas catalogados."""
    lines_dir = settings.VAULT_DIR / "02_Linhas_e_Servicos"
    if not lines_dir.exists():
        return []

    lines = []
    for f in sorted(lines_dir.glob("*.md")):
        doc = _read_markdown_file(f)
        if doc:
            meta = doc["metadata"]
            lines.append({
                "codigo": meta.get("codigo_linha", f.stem.replace("Linha ", "")),
                "vista": meta.get("vista", ""),
                "consorcio": meta.get("consorcio", ""),
                "filename": doc["filename"],
            })
    return lines
