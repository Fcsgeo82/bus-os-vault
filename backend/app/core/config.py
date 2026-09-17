"""Módulo de configurações centrais do backend Bus OS Vault."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""

    # Aplicação
    APP_NAME: str = "Bus OS Vault API"
    APP_VERSION: str = "0.7.1"
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

    # Provedor LLM para síntese de respostas ("gemini" | "openrouter")
    LLM_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"

    # Embeddings (Sentence Transformers local ou Gemini)
    EMBEDDING_MODEL_LOCAL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # Dimensão padrão do all-MiniLM-L6-v2

    # RAG Search Settings
    TOP_K_RETRIEVAL: int = 8
    RRF_K: int = 60

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
