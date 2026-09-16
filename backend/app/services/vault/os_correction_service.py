"""Serviço de correção de Ordens de Serviço no Vault com propagação de referências."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import frontmatter
from slugify import slugify

from app.core.config import settings
from app.services.vault.vault_writer import validate_os_title_for_filename
from app.services.rag.indexer import vault_indexer


class OSNotFoundException(ValueError):
    """Levantada quando a Ordem de Serviço não é localizada pelo UID informado."""


class OSCorrectionService:
    """Aplica correções de campos e retitulação de OS, propagando referências em todo o Vault."""

    def _find_os_file(self, uid: str) -> Tuple[Optional[Path], Optional[frontmatter.Post]]:
        """Localiza o arquivo da OS pelo UID, retornando caminho e conteúdo parseado."""
        os_dir = settings.VAULT_DIR / "00_Ordens_de_Servico"
        for f in sorted(os_dir.glob("*.md")):
            with open(f, "r", encoding="utf-8") as fh:
                post = frontmatter.load(fh)
            if post.metadata.get("uid") == uid:
                return f, post
        return None, None

    @staticmethod
    def _replace_values(post: frontmatter.Post, old: str, new: str) -> bool:
        """Substitui 'old' por 'new' em metadados (strings e listas) e no conteúdo da nota."""
        if not old or old == new:
            return False
        changed = False
        if post.metadata:
            for key, value in list(post.metadata.items()):
                if isinstance(value, str) and old in value:
                    post.metadata[key] = value.replace(old, new)
                    changed = True
                elif isinstance(value, list):
                    new_items = [
                        item.replace(old, new) if isinstance(item, str) and old in item else item
                        for item in value
                    ]
                    if new_items != value:
                        post.metadata[key] = new_items
                        changed = True
        if post.content and old in post.content:
            post.content = post.content.replace(old, new)
            changed = True
        return changed

    @staticmethod
    def _atomic_write_post(path: Path, post: frontmatter.Post) -> None:
        """Grava frontmatter + conteúdo de forma atômica (arquivo temporário → rename)."""
        temp = path.with_suffix(path.suffix + ".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
        os.replace(temp, path)

    def _update_md_with_rename(
        self,
        path: Path,
        old_title: str,
        new_title: str,
        old_slug: str,
        new_slug: str,
        old_uid: str,
        new_uid: str,
    ) -> bool:
        """Aplica a propagação de retitulação em um arquivo Markdown, retornando se houve mudança."""
        with open(path, "r", encoding="utf-8") as fh:
            post = frontmatter.load(fh)
        changed = self._replace_values(post, old_title, new_title)
        changed |= self._replace_values(post, old_slug, new_slug)
        changed |= self._replace_values(post, old_uid, new_uid)
        if changed:
            self._atomic_write_post(path, post)
        return changed

    def _scan_dir_for_rename(
        self,
        directory: Path,
        old_title: str,
        new_title: str,
        old_slug: str,
        new_slug: str,
        old_uid: str,
        new_uid: str,
    ) -> int:
        """Atualiza todas as notas de um diretório que referenciam a OS retitulada."""
        updated = 0
        if not directory.exists():
            return updated
        for md in sorted(directory.rglob("*.md")):
            if self._update_md_with_rename(md, old_title, new_title, old_slug, new_slug, old_uid, new_uid):
                updated += 1
        return updated

    def correct_os(self, uid: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica correções de campos à OS; se 'title' mudar, propaga o renaming pelos artefatos."""
        new_title = fields.get("title")
        if "title" in fields:
            if not isinstance(new_title, str) or not new_title.strip():
                raise ValueError("O campo 'title' deve ser uma string não vazia.")
            new_title = new_title.strip()
            validate_os_title_for_filename(new_title)

        os_path, post = self._find_os_file(uid)
        if not os_path or not post:
            raise OSNotFoundException(f"Ordem de Serviço com UID '{uid}' não encontrada.")

        old_title = post.metadata.get("title") or os_path.stem
        if new_title == old_title:
            new_title = None

        summary: Dict[str, Any] = {
            "arquivos_atualizados": 0,
            "pastas_renomeadas": 0,
            "arquivos_renomeados": 0,
        }

        if new_title:
            self._apply_title_rename(os_path, post, old_title, new_title, fields, summary)
        else:
            for key, value in fields.items():
                post.metadata[key] = value
            self._atomic_write_post(os_path, post)
            summary["arquivos_atualizados"] += 1

        try:
            vault_indexer.index_entire_vault()
            summary["rag_reindexado"] = True
        except Exception as e:
            print(f"[AVISO] Falha ao reindexar RAG após correção: {e}")
            summary["rag_reindexado"] = False

        final_title = new_title or old_title
        return {
            "status": "success",
            "message": (
                f"Ordem de Serviço atualizada para '{final_title}' com sucesso."
                if new_title
                else f"Campos da Ordem de Serviço '{old_title}' corrigidos com sucesso."
            ),
            "old_title": old_title,
            "new_title": final_title,
            "new_uid": f"os-{slugify(final_title)}",
            **summary,
        }

    def _apply_title_rename(
        self,
        os_path: Path,
        post: frontmatter.Post,
        old_title: str,
        new_title: str,
        fields: Dict[str, Any],
        summary: Dict[str, Any],
    ) -> None:
        """Renomeia a OS e propaga a mudança de título para eventos, anexos, hubs e CSVs."""
        old_uid = post.metadata.get("uid") or ""
        old_slug = slugify(old_title)
        new_slug = slugify(new_title)
        new_uid = f"os-{new_slug}"

        # 1. Atualiza a própria nota mestra da OS e renomeia o arquivo
        for key, value in fields.items():
            if key != "title":
                post.metadata[key] = value
        post.metadata["uid"] = new_uid
        self._replace_values(post, old_title, new_title)
        new_os_path = os_path.with_name(f"{new_title}.md")
        self._atomic_write_post(os_path, post)
        if new_os_path != os_path:
            os.replace(os_path, new_os_path)
            summary["arquivos_renomeados"] += 1
        summary["arquivos_atualizados"] += 1

        # 2. Outras OS que referenciam esta (retifica_os / retificada_por)
        summary["arquivos_atualizados"] += self._scan_dir_for_rename(
            settings.VAULT_DIR / "00_Ordens_de_Servico",
            old_title, new_title, old_slug, new_slug, old_uid, new_uid,
        )

        # 3. Notas de eventos vinculadas
        summary["arquivos_atualizados"] += self._scan_dir_for_rename(
            settings.VAULT_DIR / "01_Notas_de_Eventos",
            old_title, new_title, old_slug, new_slug, old_uid, new_uid,
        )

        # 4. Hubs de linha
        summary["arquivos_atualizados"] += self._scan_dir_for_rename(
            settings.VAULT_DIR / "02_Linhas_e_Servicos",
            old_title, new_title, old_slug, new_slug, old_uid, new_uid,
        )

        # 5. Notas de anexos
        summary["arquivos_atualizados"] += self._scan_dir_for_rename(
            settings.VAULT_DIR / "03_Anexos",
            old_title, new_title, old_slug, new_slug, old_uid, new_uid,
        )

        # 6. Renomeia a pasta padrão de anexos (03_Anexos/<old_slug> → <new_slug>)
        anexos_base = settings.VAULT_DIR / "03_Anexos"
        old_anexo_dir = anexos_base / old_slug
        if old_slug != new_slug and old_anexo_dir.is_dir():
            new_anexo_dir = anexos_base / new_slug
            if new_anexo_dir.exists():
                shutil.rmtree(new_anexo_dir)
            os.replace(str(old_anexo_dir), str(new_anexo_dir))
            summary["pastas_renomeadas"] += 1

        # 7. Renomeia o diretório de CSVs em data/attachments/<old_slug> e seus arquivos internos
        old_attach_dir = settings.DATA_DIR / "attachments" / old_slug
        if old_slug != new_slug and old_attach_dir.is_dir():
            new_attach_dir = settings.DATA_DIR / "attachments" / new_slug
            if new_attach_dir.exists():
                shutil.rmtree(new_attach_dir)
            os.replace(str(old_attach_dir), str(new_attach_dir))
            summary["pastas_renomeadas"] += 1
            for csv_file in list(new_attach_dir.iterdir()):
                if csv_file.name.startswith(f"{old_slug}-"):
                    csv_file.rename(new_attach_dir / csv_file.name.replace(old_slug, new_slug, 1))


os_correction_service = OSCorrectionService()