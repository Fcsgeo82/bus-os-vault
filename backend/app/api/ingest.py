"""Endpoint de ingestão e publicação atômica de Ordens de Serviço e Anexos no Vault."""

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from slugify import slugify
import frontmatter

from app.core.config import settings
from app.models.os_schema import OSIngestPayload, OSIngestResponse
from app.services.vault.vault_writer import vault_writer
from app.services.vault.csv_parser import csv_parser
from app.services.vault.line_hub_service import line_hub_service
from app.services.rag.indexer import vault_indexer

router = APIRouter(prefix="/api/os", tags=["Ingestão de Dados"])


@router.post("/ingest", response_model=OSIngestResponse, status_code=201)
async def ingest_ordem_de_servico(
    payload: str = Form(..., description="String JSON serializada de OSIngestPayload"),
    anexo_i: Optional[UploadFile] = File(None, description="Arquivo CSV do ANEXO I (Viagens)"),
    anexo_ii: Optional[UploadFile] = File(None, description="Arquivo CSV do ANEXO II (Itinerários)"),
):
    """Realiza a ingestão atômica de uma nova OS com notas de eventos e processamento de planilhas CSV."""
    # 1. Validação do payload JSON
    try:
        raw_json = json.loads(payload)
        data = OSIngestPayload.model_validate(raw_json)
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Payload de dados inválido: {str(err)}",
        )

    os_slug = slugify(data.title)
    os_uid = f"os-{os_slug}"

    attachments_dir = settings.DATA_DIR / "attachments" / os_slug
    attachments_dir.mkdir(parents=True, exist_ok=True)

    total_servicos = 0
    total_desvios = 0
    anexo_i_link = None
    anexo_ii_link = None
    parsed_i = None
    parsed_ii = None

    # 2. Processamento do ANEXO I (Viagens CSV)
    if anexo_i and anexo_i.filename:
        anexo_i_path = attachments_dir / f"{os_slug}-anexo-i.csv"
        content = await anexo_i.read()
        with open(anexo_i_path, "wb") as f:
            f.write(content)

        try:
            parsed_i = csv_parser.process_anexo_i(anexo_i_path, data.title)
            total_servicos = parsed_i["total_services"]
            vault_writer.write_note(
                subfolder=f"03_Anexos/{os_slug}",
                filename="ANEXO_I_Viagens_Resumo",
                metadata={
                    "uid": f"{os_uid}-anexo-i",
                    "title": f"ANEXO I — Viagens ({data.title})",
                    "type": "anexo_operacional",
                    "os_origem": f"[[{data.title}]]",
                    "total_servicos": total_servicos,
                    "schema_version": 1,
                },
                content=parsed_i["markdown_content"],
            )
            anexo_i_link = "[[ANEXO_I_Viagens_Resumo]]"
        except Exception as e:
            print(f"[AVISO] Falha ao parsear ANEXO I: {e}")

    # 3. Processamento do ANEXO II (Itinerários CSV)
    if anexo_ii and anexo_ii.filename:
        anexo_ii_path = attachments_dir / f"{os_slug}-anexo-ii.csv"
        content = await anexo_ii.read()
        with open(anexo_ii_path, "wb") as f:
            f.write(content)

        try:
            parsed_ii = csv_parser.process_anexo_ii(anexo_ii_path, data.title)
            total_desvios = parsed_ii["total_desvios"]
            vault_writer.write_note(
                subfolder=f"03_Anexos/{os_slug}",
                filename="ANEXO_II_Itinerarios",
                metadata={
                    "uid": f"{os_uid}-anexo-ii",
                    "title": f"ANEXO II — Itinerários Alternativos ({data.title})",
                    "type": "anexo_operacional",
                    "os_origem": f"[[{data.title}]]",
                    "total_desvios": total_desvios,
                    "schema_version": 1,
                },
                content=parsed_ii["markdown_content"],
            )
            anexo_ii_link = "[[ANEXO_II_Itinerarios]]"
        except Exception as e:
            print(f"[AVISO] Falha ao parsear ANEXO II: {e}")

    # 4. Gravação das Notas de Eventos associadas
    eventos_links = []
    eventos_hub_meta = []
    for idx, ev in enumerate(data.notas_eventos, 1):
        ev_slug = slugify(f"{idx:02d}-{ev.title[:30]}")
        ev_uid = f"evt-{os_slug}-{ev_slug}"
        ev_filename = f"NOTA-{data.ano_mes_referencia.replace('/', '-')}-{ev_slug}"

        ev_meta = {
            "uid": ev_uid,
            "title": ev.title,
            "type": "nota_evento",
            "os_origem": f"[[{data.title}]]",
            "tipo_evento": ev.tipo_evento.value,
            "objeto_afetado": ev.objeto_afetado,
            "linhas_afetadas": ev.linhas_afetadas,
            "consorcios": [c.value for c in ev.consorcios],
            "vigencia_inicio": ev.vigencia_inicio.isoformat() if ev.vigencia_inicio else None,
            "vigencia_fim": ev.vigencia_fim.isoformat() if ev.vigencia_fim else None,
            "tags": [
                f"evento/{slugify(ev.tipo_evento.value)}",
                *[f"linha/{slugify(l)}" for l in ev.linhas_afetadas],
                *[f"consorcio/{slugify(c.value)}" for c in ev.consorcios],
            ],
            "schema_version": 1,
        }

        linhas_links_str = ", ".join([f"[[Linha {l}]]" for l in ev.linhas_afetadas])
        ev_content = f"""# {ev.title}

**OS de Origem:** [[{data.title}]]  
**Tipo de Evento:** {ev.tipo_evento.value}  
**Linhas Afetadas:** {linhas_links_str or 'Geral'}  
**Início da Vigência:** {ev.vigencia_inicio or data.inicio_vigencia or 'Não especificado'}  

## Descrição da Alteração
{ev.descricao}

## Justificativa Operacional
{ev.justificativa or 'Sem justificativa adicional informada.'}
"""
        vault_writer.write_note("01_Notas_de_Eventos", ev_filename, ev_meta, ev_content)
        eventos_links.append(f"- [[{ev_filename}]]: {ev.title}")
        eventos_hub_meta.append({
            "title": ev.title,
            "filename": ev_filename,
            "linhas_afetadas": ev.linhas_afetadas,
        })

    # 5. Sincroniza Hubs de Linha com dados reais dos anexos e eventos
    hub_sync = line_hub_service.sync_hubs_for_os(
        os_title=data.title,
        vigencia_inicio=data.inicio_vigencia.isoformat() if data.inicio_vigencia else None,
        anexo_i_services=(parsed_i or {}).get("services", []) if parsed_i else [],
        anexo_ii_desvios=(parsed_ii or {}).get("desvios", []) if parsed_ii else [],
        eventos=eventos_hub_meta,
    )
    print(f"[INFO] Hubs de linha sincronizados: {hub_sync}")

    # 6. Se esta OS retifica outra, atualiza a OS anterior
    if data.retifica_os:
        clean_retifica = data.retifica_os.replace("[[", "").replace("]]", "").strip()
        os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
        for existing_file in os_dir.glob("*.md"):
            with open(existing_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            if post.metadata.get("title") == clean_retifica or existing_file.stem == clean_retifica:
                post.metadata["status_vigencia"] = "Substituída"
                post.metadata["retificada_por"] = f"[[{data.title}]]"
                serialized = frontmatter.dumps(post)
                with open(existing_file, "w", encoding="utf-8") as f:
                    f.write(serialized)
                break

    # 7. Grava a nova OS Mestra
    os_meta = {
        "uid": os_uid,
        "title": data.title,
        "tipo_os": data.tipo_os.value,
        "status_vigencia": data.status_vigencia.value,
        "ano_mes_referencia": data.ano_mes_referencia,
        "processo_rio": data.processo_rio,
        "despacho": data.despacho,
        "data_publicacao": data.data_publicacao.isoformat() if data.data_publicacao else None,
        "inicio_vigencia": data.inicio_vigencia.isoformat() if data.inicio_vigencia else None,
        "fim_vigencia": data.fim_vigencia.isoformat() if data.fim_vigencia else None,
        "arquivo_gtfs": data.arquivo_gtfs,
        "retifica_os": data.retifica_os,
        "substitui_os": data.substitui_os,
        "retificada_por": None,
        "tags": [
            f"os/{slugify(data.tipo_os.value)}",
            f"ano/{data.ano_mes_referencia.split('/')[0]}",
            f"status/{slugify(data.status_vigencia.value)}",
        ],
        "schema_version": 1,
    }

    eventos_secao = "\n".join(eventos_links) if eventos_links else "Nenhuma nota de evento cadastrada."
    anexos_secao_parts = []
    if anexo_i_link:
        anexos_secao_parts.append(f"- {anexo_i_link}: Grade de partidas e quilometragens ({total_servicos} serviços).")
    if anexo_ii_link:
        anexos_secao_parts.append(f"- {anexo_ii_link}: Itinerários alternativos e desvios ({total_desvios} desvios).")
    anexos_secao = "\n".join(anexos_secao_parts) if anexos_secao_parts else "Nenhum anexo importado."

    content_os = f"""# {data.title}

**Tipo:** {data.tipo_os.value}  
**Status:** {data.status_vigencia.value}  
**Ano/Mês de Referência:** {data.ano_mes_referencia}  
**Início da Vigência:** {data.inicio_vigencia or 'Sem data definida'}  
**Processo Administrativo:** {data.processo_rio or 'N/A'}  
**Despacho:** {data.despacho or 'N/A'}  
{f"**Retifica:** {data.retifica_os}" if data.retifica_os else ""}

---

## Notas de Alterações Operacionais
{eventos_secao}

---

## Anexos Operacionais
{anexos_secao}
"""
    vault_writer.write_note("00_Ordens_de_Servico", data.title, os_meta, content_os)

    # 8. Sincroniza o RAG automaticamente
    try:
        vault_indexer.index_entire_vault()
    except Exception as e:
        print(f"[AVISO] Falha ao reindexar RAG após ingestão: {e}")

    return OSIngestResponse(
        status="success",
        message=f"Ordem de Serviço '{data.title}' cadastrada com sucesso e indexada no RAG!",
        os_uid=os_uid,
        os_title=data.title,
        total_notas_criadas=len(data.notas_eventos),
        total_servicos_anexo_i=total_servicos,
        total_desvios_anexo_ii=total_desvios,
    )
