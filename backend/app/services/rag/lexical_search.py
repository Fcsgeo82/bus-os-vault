"""Módulo de busca léxica exata utilizando o algoritmo BM25 (Okapi)."""

import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> List[str]:
    """Tokenização amigável a identificadores de linhas (ex: 006, lecd131, sn006)."""
    return re.findall(r"\b[\w\-]+\b", text.lower())


class LexicalSearcher:
    """Gerencia índice BM25 em memória para recuperação por termos exatos."""

    def __init__(self):
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None

    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """Constrói o índice BM25 a partir da lista de chunks."""
        self.corpus_chunks = chunks
        if not chunks:
            self.bm25 = None
            return

        tokenized_corpus = [_tokenize(c["texto"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Executa busca BM25 e retorna os top_k chunks mais relevantes."""
        if not self.bm25 or not self.corpus_chunks:
            return []

        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0.0:
                continue
            item = dict(self.corpus_chunks[idx])
            item["bm25_score"] = round(score, 4)
            results.append(item)
        return results


lexical_searcher = LexicalSearcher()
