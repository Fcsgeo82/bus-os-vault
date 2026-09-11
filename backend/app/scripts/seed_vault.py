"""Script de inicialização e seed do Vault com os arquivos reais da pasta referências/."""

import sys
from pathlib import Path

# Ajusta sys.path para permitir imports de app
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings
from app.services.vault.vault_writer import vault_writer
from app.services.vault.csv_parser import csv_parser


def run_seed():
    """Executa a ingestão dos dados de referência para o cofre Obsidian."""
    print("[INFO] Iniciando Seed do Obsidian Vault...")

    repo_root = settings.BASE_DIR.parent
    ref_dir = repo_root / "referências"

    if not ref_dir.exists():
        print(f"[ERRO] Pasta referências não encontrada em {ref_dir}")
        return

    anexo_i_csv = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO I (Regular) Plano 2026 - Agosto 1º Est ret.csv"
    anexo_ii_csv = ref_dir / "174 - OS 2026.08 - agosto 2º Estudo ret 4 - ANEXO II (Regular)_ Itinerários alternativos.csv"

    os_title = "174 - OS 2026.08 - Agosto 2º Estudo [ret4]"
    os_uid = "os-2026-08-estudo-2-ret-4"

    # 1. Processa e grava os Anexos
    print("[INFO] Processando ANEXO I (Grade de viagens e quilometragens)...")
    anexo_i_result = csv_parser.process_anexo_i(anexo_i_csv, os_title)
    vault_writer.write_note(
        subfolder="03_Anexos/OS_2026.08_Estudo2_ret4",
        filename="ANEXO_I_Viagens_Resumo",
        metadata={
            "uid": f"{os_uid}-anexo-i",
            "title": f"ANEXO I — Viagens e Km ({os_title})",
            "type": "anexo_operacional",
            "os_origem": f"[[{os_title}]]",
            "total_servicos": anexo_i_result["total_services"],
            "schema_version": 1,
        },
        content=anexo_i_result["markdown_content"],
    )
    print(f"[OK] ANEXO I gravado com {anexo_i_result['total_services']} servicos sumarizados.")

    print("[INFO] Processando ANEXO II (Itinerarios alternativos e desvios)...")
    anexo_ii_result = csv_parser.process_anexo_ii(anexo_ii_csv, os_title)
    vault_writer.write_note(
        subfolder="03_Anexos/OS_2026.08_Estudo2_ret4",
        filename="ANEXO_II_Itinerarios",
        metadata={
            "uid": f"{os_uid}-anexo-ii",
            "title": f"ANEXO II — Itinerarios Alternativos ({os_title})",
            "type": "anexo_operacional",
            "os_origem": f"[[{os_title}]]",
            "total_desvios": anexo_ii_result["total_desvios"],
            "schema_version": 1,
        },
        content=anexo_ii_result["markdown_content"],
    )
    print(f"[OK] ANEXO II gravado com {anexo_ii_result['total_desvios']} desvios operacionais.")

    # 2. Grava Notas de Evento da OS
    print("[INFO] Criando Notas de Eventos associadas...")

    evento_1 = {
        "uid": "evt-2026-08-001",
        "title": "Ajuste na quilometragem e partidas das linhas da Zona Sul",
        "type": "nota_evento",
        "os_origem": f"[[{os_title}]]",
        "tipo_evento": "Ajuste",
        "objeto_afetado": ["Planejamento de Viagens", "Quilometragem"],
        "linhas_afetadas": ["006", "007", "010", "014", "100", "104", "107"],
        "consorcios": ["Intersul"],
        "vigencia_inicio": "2026-08-16",
        "vigencia_fim": None,
        "tags": ["evento/ajuste", "consorcio/intersul", "tipo/viagens"],
        "schema_version": 1,
    }
    content_evt_1 = """# Ajuste no Planejamento Operacional das Linhas Intersul

**OS de Origem:** [[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]  
**Início da Vigência:** 16/08/2026  
**Consórcio:** Intersul  
**Linhas Afetadas:** [[Linha 006]], [[Linha 007]], [[Linha 010]], [[Linha 014]], [[Linha 100]], [[Linha 104]], [[Linha 107]]  

## Descrição da Alteração
Ajuste nas grades horárias de viagens em dias úteis e sábados, além da atualização da quilometragem apurada com base nos novos estudos de tráfego.

## Referências Operacionais
- Ver grade completa de viagens em: [[ANEXO_I_Viagens_Resumo#Consórcio Intersul]]
"""
    vault_writer.write_note("01_Notas_de_Eventos", "NOTA-2026.08-01-AJU-Intersul", evento_1, content_evt_1)

    evento_2 = {
        "uid": "evt-2026-08-002",
        "title": "Inclusão de desvios operacionais por fechamento do Túnel Santa Bárbara e Feiras",
        "type": "nota_evento",
        "os_origem": f"[[{os_title}]]",
        "tipo_evento": "Inclusão",
        "objeto_afetado": ["Itinerários", "Linhas/Serviços"],
        "linhas_afetadas": ["104", "117", "165", "167", "169"],
        "consorcios": ["Intersul"],
        "vigencia_inicio": "2026-08-16",
        "vigencia_fim": None,
        "tags": ["evento/inclusao", "desvio/tunel", "desvio/feira"],
        "schema_version": 1,
    }
    content_evt_2 = """# Inclusão de Itinerários Alternativos nos Túneis e Feiras Livres

**OS de Origem:** [[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]  
**Início da Vigência:** 16/08/2026  
**Linhas:** [[Linha 104]], [[Linha 117]], [[Linha 165]], [[Linha 167]], [[Linha 169]]  

## Descrição do Evento
Autorização de itinerários alternativos de ativação automática nos seguintes cenários:
- Fechamento noturno ou para manutenção do Túnel Santa Bárbara (linhas 117 e 165).
- Desvios em decorrência de feiras livres dominicais (linha 104 na Rua Carlos Sampaio).
- Interdições na região do Aterro do Flamengo para área de lazer (linhas 100 e 169).

## Referências Operacionais
- Tabela detalhada de desvios em: [[ANEXO_II_Itinerarios]]
"""
    vault_writer.write_note("01_Notas_de_Eventos", "NOTA-2026.08-02-INC-Desvios", evento_2, content_evt_2)

    # 3. Grava a OS Mestra
    print("[INFO] Gravando OS Mestra...")
    os_meta = {
        "uid": os_uid,
        "title": os_title,
        "tipo_os": "Retificada",
        "status_vigencia": "Vigente",
        "ano_mes_referencia": "2026/8",
        "processo_rio": "000399.001631/2025-86",
        "despacho": "Despacho 0446149",
        "data_publicacao": "2026-08-14",
        "inicio_vigencia": "2026-08-16",
        "fim_vigencia": None,
        "arquivo_gtfs": "174_gtfs_ago-26_2E-ret4.zip",
        "retifica_os": "[[173 - OS 2026.08 - Agosto 2º Estudo [ret3]]]",
        "substitui_os": None,
        "retificada_por": None,
        "tags": ["os/retificada", "ano/2026", "mes/08", "status/vigente"],
        "schema_version": 1,
    }
    content_os = f"""# {os_title}

**Tipo:** Retificada  
**Status:** Vigente  
**Início da Vigência:** 16/08/2026  
**Processo Administrativo:** 000399.001631/2025-86  
**Retifica:** [[173 - OS 2026.08 - Agosto 2º Estudo [ret3]]]  

---

## Notas de Alterações Operacionais
- [[NOTA-2026.08-01-AJU-Intersul]]: Ajuste na quilometragem e partidas das linhas da Zona Sul.
- [[NOTA-2026.08-02-INC-Desvios]]: Inclusão de desvios operacionais por fechamento de túneis e feiras livres.

---

## Anexos Operacionais
- [[ANEXO_I_Viagens_Resumo]]: Grade operacional consolidada com {anexo_i_result['total_services']} serviços.
- [[ANEXO_II_Itinerarios]]: Tabela de itinerários alternativos com {anexo_ii_result['total_desvios']} desvios cadastrados.
"""
    vault_writer.write_note("00_Ordens_de_Servico", "174 - OS 2026.08 - Agosto 2º Estudo [ret4]", os_meta, content_os)

    # 4. Grava Hubs de Linhas (MOC)
    print("[INFO] Criando Hubs de Linhas (MOC)...")
    linhas_exemplo = [
        ("006", "Silvestre - Castelo", "Intersul"),
        ("104", "São Conrado - Terminal Gentileza", "Intersul"),
        ("117", "Central - Cosme Velho", "Intersul"),
        ("169", "Terminal Gentileza - General Osório", "Intersul"),
    ]

    for codigo, vista, consorcio in linhas_exemplo:
        linha_meta = {
            "uid": f"linha-{codigo}",
            "codigo_linha": codigo,
            "vista": vista,
            "consorcio": consorcio,
            "type": "linha_servico",
            "schema_version": 1,
        }
        linha_content = f"""# Linha {codigo} — {vista}

**Consórcio:** {consorcio}  
**Código do Serviço:** {codigo}  

---

## Ordens de Serviço Relacionadas
- [[{os_title}]] (Vigente a partir de 16/08/2026)

## Eventos e Alterações Cadastradas
- [[NOTA-2026.08-01-AJU-Intersul]]
- [[NOTA-2026.08-02-INC-Desvios]]

## Desvios e Itinerários Alternativos
Consulte os desvios autorizados desta linha em: [[ANEXO_II_Itinerarios#{codigo}]]
"""
        vault_writer.write_note("02_Linhas_e_Servicos", f"Linha {codigo}", linha_meta, linha_content)

    print("[OK] Seed do Vault concluído com sucesso!")


if __name__ == "__main__":
    run_seed()
