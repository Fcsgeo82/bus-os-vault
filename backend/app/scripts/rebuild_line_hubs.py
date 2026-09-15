"""Script de rebuild dos Hubs de Linha com dados reais a partir das referências/ da OS 174."""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ajusta sys.path para permitir imports de app
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import frontmatter
from app.core.config import settings
from app.services.vault.vault_writer import vault_writer
from app.services.vault.csv_parser import csv_parser
from app.services.vault.line_hub_service import line_hub_service
from app.services.rag.indexer import vault_indexer

OS_TITLE = "174 - OS 2026.08 - Agosto 2º Estudo [ret4]"
OS_UID = "os-2026-08-estudo-2-ret-4"
VIGENCIA_INICIO = "2026-08-16"


def load_eventos_vinculados(os_title: str) -> List[Dict[str, Any]]:
    """Carrega título, arquivo e linhas afetadas das notas de evento vinculadas à OS."""
    eventos: List[Dict[str, Any]] = []
    event_dir = settings.VAULT_DIR / "01_Notas_de_Eventos"
    if not event_dir.exists():
        return eventos

    for f in event_dir.glob("*.md"):
        with open(f, "r", encoding="utf-8") as fh:
            post = frontmatter.load(fh)
        origem = str(post.metadata.get("os_origem", ""))
        if os_title in origem:
            eventos.append({
                "title": post.metadata.get("title", f.stem),
                "filename": f.name,
                "linhas_afetadas": post.metadata.get("linhas_afetadas", []),
            })
    return eventos


def run_rebuild() -> None:
    """Executa a regeneração de todos os hubs de linha da OS 174 com dados reais."""
    print("[INFO] Rebuild de Hubs de Linha iniciado...")

    repo_root = settings.BASE_DIR.parent
    ref_dir = repo_root / "referências"

    if not ref_dir.exists():
        print(f"[ERRO] Pasta referências não encontrada em {ref_dir}")
        sys.exit(1)

    anexo_i_csv = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO I (Regular) Plano 2026 - Agosto 1º Est ret.csv"
    anexo_ii_csv = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO II (Regular)_ Itinerários alternativos.csv"

    print("[INFO] Processando ANEXO I (grade horária e quilometragens)...")
    parsed_i = csv_parser.process_anexo_i(anexo_i_csv, OS_TITLE)
    print(f"[OK] {parsed_i['total_services']} serviços carregados.")

    print("[INFO] Processando ANEXO II (itinerários alternativos)...")
    parsed_ii = csv_parser.process_anexo_ii(anexo_ii_csv, OS_TITLE)
    print(f"[OK] {parsed_ii['total_desvios']} desvios carregados.")

    print("[INFO] Regenerando notas de resumo dos ANEXOS I e II...")
    vault_writer.write_note(
        subfolder="03_Anexos/OS_2026.08_Estudo2_ret4",
        filename="ANEXO_I_Viagens_Resumo",
        metadata={
            "uid": f"{OS_UID}-anexo-i",
            "title": f"ANEXO I — Viagens e Km ({OS_TITLE})",
            "type": "anexo_operacional",
            "os_origem": f"[[{OS_TITLE}]]",
            "total_servicos": parsed_i["total_services"],
            "schema_version": 1,
        },
        content=parsed_i["markdown_content"],
    )
    vault_writer.write_note(
        subfolder="03_Anexos/OS_2026.08_Estudo2_ret4",
        filename="ANEXO_II_Itinerarios",
        metadata={
            "uid": f"{OS_UID}-anexo-ii",
            "title": f"ANEXO II — Itinerários Alternativos ({OS_TITLE})",
            "type": "anexo_operacional",
            "os_origem": f"[[{OS_TITLE}]]",
            "total_desvios": parsed_ii["total_desvios"],
            "schema_version": 1,
        },
        content=parsed_ii["markdown_content"],
    )
    print("[OK] ANEXOS regenerados.")

    eventos = load_eventos_vinculados(OS_TITLE)
    print(f"[INFO] {len(eventos)} notas de eventos vinculadas.")

    resultado = line_hub_service.sync_hubs_for_os(
        os_title=OS_TITLE,
        vigencia_inicio=VIGENCIA_INICIO,
        anexo_i_services=parsed_i["services"],
        anexo_ii_desvios=parsed_ii["desvios"],
        eventos=eventos,
        remove_orphans=True,
    )
    print(f"[OK] Hubs sincronizados: {resultado}")

    print("[INFO] Reindexando o RAG (LanceDB + BM25)...")
    try:
        vault_indexer.index_entire_vault()
        print("[OK] RAG reindexado.")
    except Exception as e:
        print(f"[AVISO] Falha ao reindexar RAG: {e}")

    print("[OK] Rebuild de Hubs de Linha concluído.")


if __name__ == "__main__":
    run_rebuild()