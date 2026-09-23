"""Chunker hierárquico para notas Markdown do Obsidian com enriquecimento de Frontmatter."""

import re
from pathlib import Path
from typing import List, Dict, Any
import frontmatter
from app.core.config import settings


_TABLE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
_HEADER_RE = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)


def _split_table_rows(body: str) -> List[str]:
    """Divide uma tabela Markdown em linhas, preservando header e separador."""
    lines = body.split("\n")
    header_lines: List[str] = []
    data_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            # Header row ou separator row
            if all(c in "|-: " for c in stripped) and "---" in stripped:
                header_lines.append(line)
            elif not data_lines and not header_lines:
                header_lines.append(line)
            elif not data_lines and header_lines:
                # Second pipe line = separator
                header_lines.append(line)
            else:
                data_lines.append(line)
        else:
            # Non-table line (could be text between tables)
            if data_lines or header_lines:
                # End of table block
                break

    return header_lines, data_lines


def _chunk_table(body: str, max_rows: int, overlap: int, max_chars: int = 1500) -> List[str]:
    """Divide uma tabela Markdown em sub-chunks adaptativos com sobreposição (iterativo)."""
    lines = body.split("\n")

    # Encontra onde a tabela começa e termina
    table_start = -1
    table_end = len(lines)
    pre_table: List[str] = []
    post_table: List[str] = []

    for i, line in enumerate(lines):
        if line.strip().startswith("|") and table_start == -1:
            table_start = i
        elif not line.strip().startswith("|") and table_start != -1:
            table_end = i
            post_table = lines[i:]
            break

    if table_start == -1:
        # Sem tabela, retorna como está
        return [body] if body.strip() else []

    pre_table = lines[:table_start]
    table_lines = lines[table_start:table_end]

    # Separa header (2 primeiras linhas: header + separator) do corpo
    if len(table_lines) <= 2:
        return [body]

    table_header = table_lines[:2]
    data_rows = table_lines[2:]

    # Se a tabela é pequena, retorna como está
    if len(data_rows) <= max_rows:
        return [body]

    # Estratégia adaptativa: calcule número ideal de linhas baseado no tamanho médio
    # usando TODAS as linhas de dados (amostra estável e representativa)
    avg_chars_per_row = sum(len(line) for line in data_rows) / len(data_rows)

    # Overhead fixo repetido em cada sub-chunk (pré-texto, cabeçalho e pós-tabela)
    overhead_chars = len("\n".join(pre_table)) + len("\n".join(table_header))
    if post_table:
        overhead_chars += len("\n".join(post_table))

    available_chars = max_chars - overhead_chars
    adaptive_max_rows = max_rows
    if available_chars > 0 and avg_chars_per_row > 0:
        ideal_rows = int(available_chars / avg_chars_per_row)
        # Limite entre max_rows//2 e max_rows*2 para evitar extremos
        adaptive_max_rows = max(max_rows // 2, min(ideal_rows, max_rows * 2))
    else:
        adaptive_max_rows = 1

    # Divide em sub-chunks com sobreposição (iterativo, sem recursão)
    chunks: List[str] = []
    step = max(adaptive_max_rows - overlap, 1)
    start = 0
    while start < len(data_rows):
        chunk_rows = data_rows[start:start + adaptive_max_rows]
        chunk_lines = pre_table + table_header + chunk_rows
        if post_table:
            chunk_lines.extend(post_table)
        chunks.append("\n".join(chunk_lines))
        start += step

    return chunks if chunks else [body]


def _split_paragraph(body: str, max_chars: int) -> List[str]:
    """Divide texto de parágrafo em blocos de max_chars com sobreposição de frases."""
    if len(body) <= max_chars:
        return [body]

    # Divide por parágrafos (dupla quebra de linha)
    paragraphs = re.split(r"\n\n+", body)
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # Se o parágrafo solo excede o limite, Divide por frases
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}" if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [body]


class MarkdownVaultChunker:
    """Divide documentos Markdown em seções contextuais preservando metadados."""

    def __init__(
        self,
        max_chars: int | None = None,
        table_rows: int | None = None,
        table_overlap: int | None = None,
    ):
        self.max_chars = max_chars or settings.CHUNK_MAX_CHARS
        self.table_rows = table_rows or settings.CHUNK_TABLE_ROWS
        self.table_overlap = table_overlap or settings.CHUNK_TABLE_OVERLAP

    def chunk_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """Lê um arquivo .md do cofre e gera chunks enriquecidos por cabeçalho."""
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        meta = post.metadata or {}
        content = post.content

        # Identifica categoria - primeiro tenta frontmatter, depois fallback para pasta
        expected_categories = {"os_mestra", "nota_evento", "linha_servico", "anexo_operacional", "outros"}

        # Tenta obter categoria do frontmatter
        categoria_from_meta = meta.get("category")
        if categoria_from_meta and str(categoria_from_meta).strip() in expected_categories:
            categoria = str(categoria_from_meta).strip()
        else:
            # Fallback para detecção por pasta
            relative_str = str(file_path).replace("\\", "/")
            if "00_Ordens_de_Servico" in relative_str:
                categoria = "os_mestra"
            elif "01_Notas_de_Eventos" in relative_str:
                categoria = "nota_evento"
            elif "02_Linhas_e_Servicos" in relative_str:
                categoria = "linha_servico"
            elif "03_Anexos" in relative_str:
                categoria = "anexo_operacional"
            else:
                categoria = "outros"

        is_hub = categoria == "linha_servico"

        # Constrói string contextual dos metadados
        meta_prefix_parts = [
            f"Título: {meta.get('title', file_path.stem)}",
            f"Tipo: {meta.get('type', meta.get('tipo_os', 'geral'))}",
            f"Status Vigência: {meta.get('status_vigencia', 'N/A')}",
        ]
        if meta.get("linhas_afetadas"):
            meta_prefix_parts.append(f"Linhas: {', '.join(meta['linhas_afetadas'])}")
        if meta.get("consorcios"):
            meta_prefix_parts.append(f"Consórcios: {', '.join(meta['consorcios'])}")
        if meta.get("inicio_vigencia"):
            meta_prefix_parts.append(f"Início Vigência: {meta['inicio_vigencia']}")

        meta_context_str = "[Contexto: " + " | ".join(meta_prefix_parts) + "]\n\n"

        # Metadata leve para sub-chunks de tabela (evita inflar cada sub-chunk)
        table_meta_parts = [
            f"Título: {meta.get('title', file_path.stem)}",
        ]
        if meta.get("linhas_afetadas"):
            table_meta_parts.append(f"Linhas: {', '.join(meta['linhas_afetadas'])}")
        table_meta_str = "[Contexto: " + " | ".join(table_meta_parts) + "]\n\n"

        # Divide por cabeçalhos markdown (# ou ##)
        sections = _HEADER_RE.split(content)

        chunks: List[Dict[str, Any]] = []
        doc_uid = str(meta.get("uid", file_path.stem))

        current_header = meta.get("title", file_path.stem)

        idx = 0
        while idx < len(sections):
            text_block = sections[idx].strip()
            idx += 1

            if not text_block:
                continue

            # Se for um cabeçalho, pega ele e o próximo bloco como corpo
            if _HEADER_RE.match(text_block) and idx < len(sections):
                current_header = text_block.lstrip("#").strip()
                body = sections[idx].strip()
                idx += 1
            else:
                body = text_block

            if not body:
                continue

            # Decide se é tabela ou parágrafo e chunka adequadamente
            has_table = bool(_TABLE_ROW_RE.search(body))
            is_oversized = len(body) > self.max_chars

            if has_table and is_oversized:
                sub_bodies = _chunk_table(body, self.table_rows, self.table_overlap)
                # Usa metadata leve para sub-chunks de tabela
                for sub_body in sub_bodies:
                    chunk_text = f"{table_meta_str}### {current_header}\n{sub_body}"
                    chunk_id = f"{doc_uid}_{len(chunks)}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "nota_titulo": meta.get("title", file_path.stem),
                        "secao_titulo": current_header,
                        "arquivo_path": str(file_path),
                        "categoria": categoria,
                        "is_hub": is_hub,
                        "status_vigencia": meta.get("status_vigencia", "Vigente"),
                        "linhas_afetadas": meta.get("linhas_afetadas", []),
                        "consorcios": meta.get("consorcios", []),
                        "ano_mes": meta.get("ano_mes_referencia", meta.get("ano_mes", "")),
                        "texto": chunk_text,
                        "raw_body": sub_body,
                    })
            elif is_oversized:
                sub_bodies = _split_paragraph(body, self.max_chars)
                for sub_body in sub_bodies:
                    chunk_text = f"{meta_context_str}### {current_header}\n{sub_body}"
                    chunk_id = f"{doc_uid}_{len(chunks)}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "nota_titulo": meta.get("title", file_path.stem),
                        "secao_titulo": current_header,
                        "arquivo_path": str(file_path),
                        "categoria": categoria,
                        "is_hub": is_hub,
                        "status_vigencia": meta.get("status_vigencia", "Vigente"),
                        "linhas_afetadas": meta.get("linhas_afetadas", []),
                        "consorcios": meta.get("consorcios", []),
                        "ano_mes": meta.get("ano_mes_referencia", meta.get("ano_mes", "")),
                        "texto": chunk_text,
                        "raw_body": sub_body,
                    })
            else:
                chunk_text = f"{meta_context_str}### {current_header}\n{body}"
                chunk_id = f"{doc_uid}_{len(chunks)}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "nota_titulo": meta.get("title", file_path.stem),
                    "secao_titulo": current_header,
                    "arquivo_path": str(file_path),
                    "categoria": categoria,
                    "is_hub": is_hub,
                    "status_vigencia": meta.get("status_vigencia", "Vigente"),
                    "linhas_afetadas": meta.get("linhas_afetadas", []),
                    "consorcios": meta.get("consorcios", []),
                    "ano_mes": meta.get("ano_mes_referencia", meta.get("ano_mes", "")),
                    "texto": chunk_text,
                    "raw_body": body,
                })

        return chunks


vault_chunker = MarkdownVaultChunker()
