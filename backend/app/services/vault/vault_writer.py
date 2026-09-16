"""Módulo para leitura e escrita atômica de arquivos Markdown no Obsidian Vault."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import frontmatter
from app.core.config import settings

_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "CLOCK$"} | {
    f"COM{i}" for i in range(1, 10)
} | {
    f"LPT{i}" for i in range(1, 10)
}


def validate_os_title_for_filename(title: str) -> None:
    """Valida se o título pode ser usado como nome de arquivo no sistema de arquivos (Windows)."""
    invalid = sorted(set(_INVALID_FILENAME_CHARS) & set(title))
    if invalid:
        raise ValueError(
            "O título da OS contém caracteres inválidos para nome de arquivo no Windows: "
            f"{invalid}. Remova caracteres como : / \\ * ? < > | \" do campo 'Título Oficial da OS'."
        )
    if title != title.strip():
        raise ValueError("O título da OS não pode começar ou terminar com espaços.")
    if title.endswith("."):
        raise ValueError("O título da OS não pode terminar com ponto final.")
    stem = title.rsplit(".", 1)[0] if "." in title else title
    if stem.upper() in _RESERVED_NAMES:
        raise ValueError("O título da OS não pode ser um nome reservado do Windows (CON, PRN, AUX, NUL, COM#, LPT#).")


class VaultWriter:
    """Gerenciador do sistema de arquivos do cofre Obsidian."""

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or settings.VAULT_DIR
        self._ensure_folders()

    def _ensure_folders(self) -> None:
        """Garante a existência das subpastas estruturadas do cofre."""
        subfolders = [
            "00_Ordens_de_Servico",
            "01_Notas_de_Eventos",
            "02_Linhas_e_Servicos",
            "03_Anexos",
        ]
        for folder in subfolders:
            (self.vault_path / folder).mkdir(parents=True, exist_ok=True)

    def write_note(
        self,
        subfolder: str,
        filename: str,
        metadata: Dict[str, Any],
        content: str,
        overwrite: bool = True,
    ) -> Path:
        """Escreve um arquivo Markdown estruturado com Frontmatter de forma atômica."""
        target_dir = self.vault_path / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        target_file = target_dir / filename

        if target_file.exists() and not overwrite:
            return target_file

        # Monta a nota com Frontmatter
        post = frontmatter.Post(content=content, **metadata)
        serialized = frontmatter.dumps(post)

        # Escrita atômica usando arquivo temporário
        temp_file = target_dir / f"{filename}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(serialized)

        os.replace(temp_file, target_file)
        return target_file

    def read_note(self, relative_path: str) -> Optional[frontmatter.Post]:
        """Lê um arquivo Markdown do cofre e retorna seu frontmatter e corpo."""
        file_path = self.vault_path / relative_path
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return frontmatter.load(f)

    def list_notes(self, subfolder: str) -> list[Path]:
        """Lista todas as notas de uma subpasta."""
        target_dir = self.vault_path / subfolder
        if not target_dir.exists():
            return []
        return sorted(list(target_dir.glob("*.md")))


vault_writer = VaultWriter()
