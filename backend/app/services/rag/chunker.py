"""Chunker hierárquico para notas Markdown do Obsidian com enriquecimento de Frontmatter."""

import re
from pathlib import Path
from typing import List, Dict, Any
import frontmatter


class MarkdownVaultChunker:
    """Divide documentos Markdown em seções contextuais preservando metadados."""

    @staticmethod
    def chunk_document(file_path: Path) -> List[Dict[str, Any]]:
        """Lê um arquivo .md do cofre e gera chunks enriquecidos por cabeçalho."""
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        meta = post.metadata or {}
        content = post.content

        # Identifica categoria pela pasta
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

        # Divide por cabeçalhos markdown (# ou ##)
        header_regex = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
        sections = header_regex.split(content)

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
            if header_regex.match(text_block) and idx < len(sections):
                current_header = text_block.lstrip("#").strip()
                body = sections[idx].strip()
                idx += 1
            else:
                body = text_block

            if not body:
                continue

            # Constrói o texto do chunk com o cabeçalho e os metadados injetados
            chunk_text = f"{meta_context_str}### {current_header}\n{body}"

            chunk_id = f"{doc_uid}_{len(chunks)}"

            chunks.append({
                "chunk_id": chunk_id,
                "nota_titulo": meta.get("title", file_path.stem),
                "secao_titulo": current_header,
                "arquivo_path": str(file_path),
                "categoria": categoria,
                "status_vigencia": meta.get("status_vigencia", "Vigente"),
                "linhas_afetadas": meta.get("linhas_afetadas", []),
                "consorcios": meta.get("consorcios", []),
                "ano_mes": meta.get("ano_mes_referencia", meta.get("ano_mes", "")),
                "texto": chunk_text,
                "raw_body": body,
            })

        return chunks


vault_chunker = MarkdownVaultChunker()
