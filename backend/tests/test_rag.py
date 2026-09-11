"""Testes unitários e de integração para o pipeline RAG híbrido."""

from pathlib import Path
from app.core.config import settings
from app.services.rag.chunker import vault_chunker
from app.services.rag.hybrid_retriever import hybrid_retriever
from app.services.rag.generator import rag_generator
from app.models.rag_schema import RAGFilters


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


def test_hybrid_retriever_finds_exact_and_semantic():
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


def test_rag_generator_synthesizes_response():
    """Testa se o gerador formata a resposta citando as fontes recuperadas."""
    sources = hybrid_retriever.retrieve(query="linha 006 Silvestre", top_k=3)
    response = rag_generator.generate_response(
        query="Qual o trajeto da linha 006?",
        sources=sources,
    )
    assert len(response.answer) > 20
    assert len(response.sources) > 0
    assert response.execution_time_seconds >= 0.0
