"""Modelos Pydantic para o motor de busca e chat RAG."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Papel na conversa."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Mensagem de histórico da conversa."""
    role: ChatRole
    content: str


class RAGFilters(BaseModel):
    """Filtros operacionais opcionais para restringir a busca semântica."""
    apenas_vigentes: bool = Field(default=True, description="Restringir busca a OS e notas com vigência ativa")
    linhas: Optional[List[str]] = Field(default=None, description="Filtrar por códigos de linhas específicas")
    consorcios: Optional[List[str]] = Field(default=None, description="Filtrar por consórcios")
    ano_mes: Optional[str] = Field(default=None, description="Filtrar por período específico, ex: 2026/1")
    tipo_evento: Optional[str] = Field(default=None, description="Inclusão, Remoção, Ajuste, Retificação")


class RAGSource(BaseModel):
    """Referência bibliográfica do trecho recuperado no cofre."""
    chunk_id: str
    nota_titulo: str
    arquivo_path: str
    categoria: str  # "os_mestra", "nota_evento", "anexo_i", "anexo_ii"
    score: float = 0.0
    trecho: str
    metadata: dict = Field(default_factory=dict)


class ChatQuery(BaseModel):
    """Payload para envio de pergunta ao RAG."""
    query: str = Field(..., min_length=2, description="Pergunta em linguagem natural")
    history: List[ChatMessage] = Field(default_factory=list, description="Histórico de mensagens recentes")
    filters: Optional[RAGFilters] = Field(default=None, description="Filtros de escopo operacional")
    stream: bool = Field(default=False, description="Indica se deve retornar streaming de tokens")


class ChatResponse(BaseModel):
    """Resposta consolidada gerada pelo Gemini Flash com as fontes."""
    answer: str = Field(..., description="Texto da resposta formulada pelo assistente")
    sources: List[RAGSource] = Field(default_factory=list, description="Lista de notas e trechos consultados")
    execution_time_seconds: float = Field(0.0, description="Tempo total de recuperação e geração")


class SearchQuery(BaseModel):
    """Payload para consulta pura de trechos sem geração pelo LLM."""
    query: str = Field(..., min_length=2)
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[RAGFilters] = None


class SearchResponse(BaseModel):
    """Resultados de busca híbrida ranqueados."""
    total: int
    results: List[RAGSource]
