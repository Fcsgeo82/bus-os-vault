"""Módulo de configurações centrais do backend Bus OS Vault."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""

    # Aplicação
    APP_NAME: str = "Bus OS Vault API"
    APP_VERSION: str = "0.10.1"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # Cloudflare / localtunnel (URL pública para compartilhamento, sem admin/firewall).
    # Provedores: "auto" (tenta cloudflare, depois localtunnel), "cloudflare", "localtunnel".
    TUNNEL_ENABLED: bool = False
    TUNNEL_PROVIDER: str = "auto"

    # Diretórios do Sistema
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    VAULT_DIR: Path = BASE_DIR / "vault"
    DATA_DIR: Path = BASE_DIR / "data"
    LANCEDB_DIR: Path = DATA_DIR / "lancedb"

    # Google Gemini AI (Free tier)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Provedor LLM para síntese de respostas ("gemini" | "openrouter" | "nvidia_nim")
    LLM_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"

    # NVIDIA NIM (build.nvidia.com) — API compatível com OpenAI, free tier
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_NIM_MODEL: str = "nvidia/nemotron-3-super-120b-a12b"

    # Embeddings (Sentence Transformers local ou Gemini)
    EMBEDDING_MODEL_LOCAL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # Dimensão padrão do all-MiniLM-L6-v2

    # RAG Search Settings
    TOP_K_RETRIEVAL: int = 8
    RRF_K: int = 60

    # RAG Chunking Settings
    CHUNK_MAX_CHARS: int = 1500       # Limite de caracteres por chunk (≈400 tokens)
    CHUNK_TABLE_ROWS: int = 10        # Linhas de tabela por sub-chunk (~100 chars/row)
    CHUNK_TABLE_OVERLAP: int = 2      # Sobreposição de linhas entre sub-chunks de tabela
    CHUNK_PARAGRAPH_OVERLAP: int = 1  # Frases de sobreposição entre chunks de parágrafo

    # RAG Retrieval Settings
    TRECHO_MAX_CHARS: int = 3500       # Limite do trecho retornado ao caller (linhas do ANEXO I completas)
    CONTEXT_MAX_CHARS: int = 3500      # Limite do trecho no contexto do LLM
    CONTEXT_MAX_DOCS: int = 8         # Máximo de documentos no contexto do LLM
    HUB_BOOST: float = 2.5            # Multiplicador de score para chunks da linha consultada

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Garante que os diretórios necessários existem
settings.VAULT_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
