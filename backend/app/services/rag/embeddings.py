"""Provedor unificado de embeddings para o motor de busca vetorial do RAG."""

import hashlib
import numpy as np
from typing import List
from app.core.config import settings


class EmbeddingProvider:
    """Gera representações vetoriais para chunks de texto e queries do usuário."""

    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_LOCAL)
        except Exception as e:
            print(f"Aviso ao carregar SentenceTransformer local: {e}")

        self._gemini_client = None

        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                print(f"Aviso ao inicializar Gemini client para embeddings: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um único texto."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings para um lote de textos."""
        if not texts:
            return []

        # Tentativa 1: SentenceTransformer local (gratuito, offline e determinístico)
        if self._model is not None:
            try:
                vecs = self._model.encode(texts, normalize_embeddings=True)
                return [v[:self.dimension].tolist() for v in vecs]
            except Exception as e:
                print(f"Erro no SentenceTransformer local: {e}. Tentando Gemini...")

        # Tentativa 2: API do Gemini se configurada
        if self._gemini_client:
            try:
                res = self._gemini_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=texts,
                )
                return [e.values[:self.dimension] for e in res.embeddings]
            except Exception as e:
                print(f"Erro na API de embeddings do Gemini: {e}. Usando fallback local...")

        # Fallback local determinístico de alta dispersão (baseado em hash pseudo-semântico com n-grams)
        return [self._local_fallback_embedding(t) for t in texts]

    def _local_fallback_embedding(self, text: str) -> List[float]:
        """Gera vetor determinístico normalizado para testes locais sem requisições externas."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dimension
            val = ((h >> 8) % 1000) / 500.0 - 1.0
            vec[pos] += val * (1.0 / (i + 1) ** 0.3)

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


embedding_provider = EmbeddingProvider()
