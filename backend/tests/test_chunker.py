"""Testes de regressão para o chunker de tabelas Markdown (fix RecursionError)."""

from pathlib import Path
from app.services.rag.chunker import vault_chunker, _chunk_table


def _gerar_tabela_anexo(num_linhas: int) -> str:
    """Gera uma tabela que simula o ANEXO II com pré-texto e N linhas de desvios."""
    linhas = [
        "**OS de Referência:** [[999 - OS Teste]]",
        "**Total de Desvios Cadastrados:** %d" % num_linhas,
        "",
        "| Linha | Consórcio | Sentido | Evento | Descrição | Extensão (km) | Ativação |",
        "|---|---|---|---|---|---|---|",
    ]
    for i in range(1, num_linhas + 1):
        linhas.append(
            "| **%03d** | Intersul | Ida | `[desvio_feira]` | nan | 27.085 | nan |" % i
        )
    return "\n".join(linhas)


def test_chunk_table_grande_sem_recursion_error():
    """Tabela muito grande (ANEXO II) não deve estourar recursão nem engolir linhas."""
    body = _gerar_tabela_anexo(150)
    chunks = _chunk_table(body, max_rows=10, overlap=2, max_chars=1500)
    assert len(chunks) > 1
    # A linha 104 deve estar presente em algum chunk
    assert any("**104**" in c for c in chunks)


def test_chunk_table_gigante_sem_recursion_error():
    """Tabela com mais de 500 linhas (pior caso real) também não recursa."""
    body = _gerar_tabela_anexo(509)
    chunks = _chunk_table(body, max_rows=10, overlap=2, max_chars=1500)
    assert len(chunks) > 1
    assert any("**104**" in c for c in chunks)


def test_chunk_table_pequena_retorna_inteira():
    """Tabela pequena é retornada inteira, sem divisão."""
    body = _gerar_tabela_anexo(3)
    chunks = _chunk_table(body, max_rows=10, overlap=2, max_chars=1500)
    assert chunks == [body]


def test_chunk_table_respeita_limite_aproximado():
    """Sub-chunks não devem exceder drasticamente o limite de caracteres."""
    body = _gerar_tabela_anexo(150)
    chunks = _chunk_table(body, max_rows=10, overlap=2, max_chars=1500)
    # Pré-texto + cabeçalho + linhas podem exceder ligeiramente; limite folgado.
    for c in chunks:
        assert len(c) < 2500


def test_chunker_documento_anexo_real():
    """Chunking de um ANEXO II real do cofre não deve estourar recursão."""
    anexo_candidates = list(
        Path("vault/03_Anexos").rglob("ANEXO_II_Itinerarios.md")
    )
    if not anexo_candidates:
        return  # Sem anexos reais disponíveis: teste passa sem assert
    for f in anexo_candidates[:1]:
        chunks = vault_chunker.chunk_document(f)
        assert len(chunks) > 0
        assert any("104" in c["raw_body"] or "104" in c["texto"] for c in chunks)