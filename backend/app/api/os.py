"""Endpoints da API para consulta e visualização de notas do cofre Obsidian."""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from slugify import slugify
import frontmatter
from app.core.config import settings
from app.models.os_schema import OSCorrectionPayload
from app.services.rag.indexer import vault_indexer
from app.services.vault.os_correction_service import (
    OSNotFoundException,
    os_correction_service,
)

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
                "processo_rio": meta.get("processo_rio", []),
                "despacho": meta.get("despacho", []),
                "data_publicacao": meta.get("data_publicacao"),
                "inicio_vigencia": meta.get("inicio_vigencia"),
                "fim_vigencia": meta.get("fim_vigencia"),
                "arquivo_gtfs": meta.get("arquivo_gtfs"),
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


@router.post("/{uid}/correct")
async def correct_ordem_de_servico(uid: str, correction: OSCorrectionPayload):
    """Corrige campos de uma OS; alterações de título propagam o renaming para artefatos vinculados."""
    fields = correction.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="Nenhum campo de correção informado.")
    try:
        return os_correction_service.correct_os(uid, fields)
    except OSNotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))


@router.delete("/{uid}")
async def delete_ordem_de_servico(uid: str):
    """Exclui uma OS e seus artefatos vinculados (notas de eventos, anexos e CSVs)."""
    os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
    target_name = None
    os_title = None
    for f in os_dir.glob("*.md"):
        doc = _read_markdown_file(f)
        if doc and doc["metadata"].get("uid") == uid:
            target_name = f.name
            os_title = doc["metadata"].get("title")
            break

    if not target_name or not os_title:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")

    os_slug = slugify(os_title)

    # 1. Exclui notas de eventos vinculadas
    eventos_removidos = 0
    eventos_links = set()
    event_dir = settings.VAULT_DIR / "01_Notas_de_Eventos"
    if event_dir.exists():
        for ev_file in event_dir.glob("*.md"):
            ev_doc = _read_markdown_file(ev_file)
            if ev_doc:
                origem = ev_doc["metadata"].get("os_origem", "")
                if os_title in origem or uid in origem:
                    eventos_links.add(ev_file.stem)
                    ev_file.unlink()
                    eventos_removidos += 1

    anexos_removidos = 0

    # 2. Exclui pasta de anexos Markdown com slug padrão (03_Anexos/<slug>)
    anexos_dir = settings.VAULT_DIR / "03_Anexos" / os_slug
    if anexos_dir.exists():
        shutil.rmtree(anexos_dir)
        anexos_removidos += 1

    # 3. Varre 03_Anexos em busca de pastas cujas notas referenciam esta OS
    #    (cobre slugs fora do padrão, como backups manuais/legados)
    anexos_base = settings.VAULT_DIR / "03_Anexos"
    if anexos_base.exists():
        for sub in list(anexos_base.iterdir()):
            if sub.is_dir():
                for md in sub.glob("*.md"):
                    doc = _read_markdown_file(md)
                    if doc:
                        origem = doc["metadata"].get("os_origem", "")
                        if os_title in origem or uid in origem:
                            shutil.rmtree(sub)
                            anexos_removidos += 1
                            break

    # 4. Exclui arquivos CSV de anexos (data/attachments/<slug> e variantes)
    attachments_base = settings.DATA_DIR / "attachments"
    if attachments_base.exists():
        for att_dir in list(attachments_base.iterdir()):
            if att_dir.is_dir():
                if att_dir.name == os_slug or any(
                    f.name.startswith(f"{os_slug}-") for f in att_dir.glob("*")
                ):
                    shutil.rmtree(att_dir)

    # 5. Exclui a nota mestra da OS
    (os_dir / target_name).unlink()

    # 5.1. Remove referências da OS excluída dos hubs de linha (promove a OS mais recente restante)
    from app.services.vault.line_hub_service import line_hub_service

    hubs_atualizados = line_hub_service.detach_hub_references(os_title, eventos_links)

    # 6. Reindexa o RAG (LanceDB + BM25) após a remoção
    try:
        vault_indexer.index_entire_vault()
    except Exception as e:
        print(f"[AVISO] Falha ao reindexar RAG após exclusão: {e}")

    return {
        "status": "success",
        "message": f"Ordem de Serviço '{os_title}' excluída com sucesso.",
        "os_uid": uid,
        "os_title": os_title,
        "notas_eventos_removidas": eventos_removidos,
        "anexos_removidos": anexos_removidos,
        "hubs_atualizados": hubs_atualizados,
    }
