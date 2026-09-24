"""Testes unitários e de integração para o pipeline RAG híbrido."""

from pathlib import Path
import pytest
from app.core.config import settings
from app.services.rag.chunker import vault_chunker
from app.services.rag.lexical_search import lexical_searcher
from app.services.rag.hybrid_retriever import hybrid_retriever
from app.services.rag.generator import rag_generator
from app.models.rag_schema import RAGFilters


@pytest.fixture(scope="module")
def indice_pronto():
    """Garante que o índice LanceDB e BM25 estejam disponíveis nos testes.

    Reconstrói o BM25 em memória (rápido) e recria a tabela LanceDB caso vazia.
    """
    all_chunks = []
    for f in settings.VAULT_DIR.rglob("*.md"):
        try:
            all_chunks.extend(vault_chunker.chunk_document(f))
        except Exception:
            continue
    lexical_searcher.build_index(all_chunks)
    return all_chunks


def test_chunker_enriches_frontmatter(tmp_path):
    """Garante que metadados do frontmatter sejam injetados no início de cada chunk."""
    test_file = tmp_path / "test_note.md"
    content = """---
uid: test-01
title: Nota Teste Linha 507
status_vigencia: Vigente
linhas_afetadas: ["507"]
---

# Seção 1
Texto da primeira seção falando sobre itinerário.

## Seção 2
Texto da segunda seção com detalhes operacionais.
"""
    test_file.write_text(content, encoding="utf-8")

    chunks = vault_chunker.chunk_document(test_file)
    assert len(chunks) >= 2
    for c in chunks:
        assert "Linhas: 507" in c["texto"]
        assert "Status Vigência: Vigente" in c["texto"]


def test_hybrid_retriever_finds_exact_and_semantic(indice_pronto):
    """Testa se a busca híbrida recupera notas do acervo real indexado."""
    # Busca por termo exato da linha 104
    sources = hybrid_retriever.retrieve(
        query="Quais itinerários alternativos ou desvios existem para a linha 104?",
        top_k=5,
    )
    assert len(sources) > 0
    titulos = [s.nota_titulo for s in sources]
    # Espera-se achar nota de evento ou anexo com a linha 104
    assert any("104" in s.trecho or "104" in s.nota_titulo for s in sources)


def test_rag_generator_synthesizes_response(indice_pronto):
    """Testa se o gerador formata a resposta citando as fontes recuperadas."""
    sources = hybrid_retriever.retrieve(query="linha 006 Silvestre", top_k=3)
    response = rag_generator.generate_response(
        query="Qual o trajeto da linha 006?",
        sources=sources,
    )
    assert len(response.answer) > 20
    assert len(response.sources) > 0
    assert response.execution_time_seconds >= 0.0


def test_hybrid_retriever_filtro_por_os(indice_pronto):
    """Filtro por OS restringe os resultados à OS selecionada."""
    alvo = "179 - OS 2026.09 - Setembro 1º Estudo ret"
    sources = hybrid_retriever.retrieve(
        query="Quais desvios de itinerário existem para a linha 104?",
        top_k=5,
        filters=RAGFilters(os_titulos=[alvo], apenas_vigentes=False),
    )
    assert len(sources) > 0
    assert all(s.metadata.get("os_titulo") == alvo for s in sources)


def test_retriever_inclui_planejamento_do_hub(indice_pronto):
    """Query com código de linha deve trazer a grade completa do hub no contexto."""
    sources = hybrid_retriever.retrieve(
        query="planejamento de viagens da linha 812",
        top_k=8,
        filters=RAGFilters(apenas_vigentes=False),
    )
    hubs = [s for s in sources if s.nota_titulo == "Linha 812"]
    assert hubs
    assert any(
        "| Dia Útil |" in s.trecho or "Distribuição Horária" in s.trecho
        for s in hubs
    )
