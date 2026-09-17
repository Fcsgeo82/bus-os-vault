"""Migração automática: converte `processo_rio`/`despacho` de string para lista nas OSs legadas.

Idempotente e seguro de rodar a cada startup. As OSs cadastradas antes da v0.7.0
não possuíam mais de um processo/despacho, portanto a conversão é de string → lista
de 1 elemento (ou lista vazia quando o campo era nulo).
"""

import os
from pathlib import Path
from typing import List

import frontmatter

from app.core.config import settings


def migrate_processos_despachos(vault_dir: Path | None = None) -> List[str]:
    """Converte campos legados em listas. Retorna os nomes dos arquivos migrados."""
    os_dir = (vault_dir or settings.VAULT_DIR) / "00_Ordens_de_Servico"
    if not os_dir.exists():
        return []

    migrated: List[str] = []
    for md_file in sorted(os_dir.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as fh:
            post = frontmatter.load(fh)

        changed = False
        for field in ("processo_rio", "despacho"):
            value = post.metadata.get(field)
            if isinstance(value, list):
                continue
            cleaned = str(value).strip() if value not in (None, "") else ""
            post.metadata[field] = [cleaned] if cleaned else []
            changed = True

        if changed:
            temp = md_file.with_suffix(md_file.suffix + ".tmp")
            with open(temp, "w", encoding="utf-8") as fh:
                fh.write(frontmatter.dumps(post))
            os.replace(temp, md_file)
            migrated.append(md_file.name)

    return migrated


if __name__ == "__main__":
    result = migrate_processos_despachos()
    print(f"[MIGRAÇÃO] {len(result)} OS(s) migrada(s): {result or 'nenhuma'}")