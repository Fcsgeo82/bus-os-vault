"""Aplicação principal FastAPI do Bus OS Vault."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.rag import router as rag_router
from app.api.os import router as os_router
from app.api.ingest import router as ingest_router
from app.services.rag.indexer import vault_indexer

# Garante exibição de emojis e acentos no console do Windows (cp1252)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _get_lan_ip() -> str | None:
    """Detecta o IP desta máquina na rede local (via rota padrão, sem enviar pacotes)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def _find_cloudflared() -> str | None:
    """Procura o binário cloudflared no PATH e no diretório temporário local."""
    in_path = shutil.which("cloudflared")
    if in_path:
        return in_path
    local_path = Path(tempfile.gettempdir()) / "cloudflared.exe"
    return str(local_path) if local_path.exists() else None


def _find_localtunnel() -> str | None:
    """Procura o cliente localtunnel instalado localmente (sem admin)."""
    lt_path = Path(tempfile.gettempdir()) / "bus-os-lt" / "node_modules" / "localtunnel" / "bin" / "lt.js"
    return str(lt_path) if lt_path.exists() else None


def _await_tunnel_url(
    log_path: str, proc: subprocess.Popen, pattern: str, timeout_secs: int = 15
) -> str:
    """Aguarda a URL do túnel aparecer no log de saída. Retorna "" se expirar."""
    regex = re.compile(pattern)
    for _ in range(int(timeout_secs * 2)):
        time.sleep(0.5)
        if proc.poll() is not None:
            break
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    match = regex.search(line)
                    if match:
                        return match.group(0).strip()
        except FileNotFoundError:
            continue
    return ""


def _start_cloudflared(port: int) -> tuple[str, subprocess.Popen | None]:
    """Inicia Cloudflare Quick Tunnel e retorna (url, processo)."""
    cloudflared = _find_cloudflared()
    if not cloudflared:
        return "", None
    log_path = os.path.join(tempfile.gettempdir(), "bus-os-vault-tunnel.log")
    try:
        proc = subprocess.Popen(
            [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=open(log_path, "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return "", None
    url = _await_tunnel_url(log_path, proc, r"https://\S+trycloudflare\.com\S*")
    return url, proc


def _start_localtunnel(port: int) -> tuple[str, subprocess.Popen | None]:
    """Inicia localtunnel (via node local) e retorna (url, processo)."""
    lt_js = _find_localtunnel()
    node = shutil.which("node")
    if not lt_js or not node:
        return "", None
    log_path = os.path.join(tempfile.gettempdir(), "bus-os-vault-tunnel.log")
    try:
        proc = subprocess.Popen(
            [node, lt_js, "--port", str(port)],
            stdout=open(log_path, "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return "", None
    url = _await_tunnel_url(log_path, proc, r"https://\S+loca\.lt\S*")
    return url, proc


def _start_tunnel(port: int, provider: str = "auto") -> tuple[str, str | None, subprocess.Popen | None]:
    """Inicia um túnel público seguindo a ordem do provedor configurado.

    Retorna (url, provedor_usado, processo).
    """
    providers: dict[str, tuple[str, object]] = {
        "cloudflare": ("cloudflare", _start_cloudflared),
        "localtunnel": ("localtunnel", _start_localtunnel),
    }
    order: list[tuple[str, object]] = list(providers.values())
    if provider.lower() == "localtunnel":
        order.reverse()

    for name, starter in order:  # type: ignore[assignment]
        url, proc = starter(port)  # type: ignore[misc]
        if url:
            return url, name, proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
    return "", None, None


def _print_network_urls(port: int, host: str = "127.0.0.1", tunnel_url: str = "", tunnel_provider: str = "") -> None:
    """Exibe no terminal as URLs de acesso: local, rede e (opcional) túnel público."""
    lan_ip = _get_lan_ip()
    base_local = f"http://{host}:{port}" if host not in ("0.0.0.0", "::") else f"http://127.0.0.1:{port}"
    print("\n" + "=" * 60)
    print(f"Bus OS Vault v{settings.APP_VERSION} pronto!")
    print(f"  Local:  {base_local}")
    if lan_ip:
        print(f"  Rede:   http://{lan_ip}:{port}")
        print(f"  Docs:   http://{lan_ip}:{port}/docs")
    else:
        print(f"  Docs:   {base_local}/docs")
    if tunnel_url:
        print(f"  Tunel:  {tunnel_url}  ({tunnel_provider})")
    print("=" * 60)
    if tunnel_url:
        print("Compartilhe a URL 'Tunel' — funciona de qualquer dispositivo, sem firewall.")
    elif lan_ip:
        print("Compartilhe a URL 'Rede' com dispositivos na mesma rede.")
        print("(sem admin p/ abrir o firewall, habilite TUNNEL_ENABLED=true no .env)")
    print("=" * 60 + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerenciamento de ciclo de vida da aplicação (startup e shutdown)."""
    # Cria diretórios vitais
    settings.VAULT_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.LANCEDB_DIR.mkdir(parents=True, exist_ok=True)

    # Carrega / atualiza índice em memória na inicialização
    try:
        vault_indexer.index_entire_vault()
    except Exception as e:
        print(f"[AVISO] Falha ao indexar cofre no startup: {e}")

    # Túnel público (se habilitado) — sem depender do firewall local
    tunnel_url = ""
    tunnel_provider = ""
    tunnel_proc: subprocess.Popen | None = None
    if settings.TUNNEL_ENABLED:
        print("Iniciando túnel público (Cloudflare/localtunnel)...")
        tunnel_url, tunnel_provider, tunnel_proc = _start_tunnel(
            settings.APP_PORT, settings.TUNNEL_PROVIDER
        )
        app.state.tunnel_proc = tunnel_proc
        if tunnel_url:
            app.state.tunnel_url = tunnel_url
            print(f"Túnel público ativo ({tunnel_provider}).")
        else:
            print("[AVISO] Túnel indisponível (provedores bloqueados ou não instalados).")

    _print_network_urls(settings.APP_PORT, settings.APP_HOST, tunnel_url, tunnel_provider)

    yield

    # Encerra o processo do túnel ao desligar
    tunnel_proc = getattr(app.state, "tunnel_proc", None)
    if tunnel_proc:
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=3)
        except Exception:
            try:
                tunnel_proc.kill()
            except Exception:
                pass

    print(f"[{settings.APP_NAME}] Encerrando...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para gestão e busca semântica em Ordens de Serviço do transporte municipal via Obsidian Vault e RAG híbrido.",
    lifespan=lifespan,
)

# Registra os roteadores da API
app.include_router(rag_router)
app.include_router(os_router)
app.include_router(ingest_router)

# Configuração de CORS para permitir acesso seguro do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção com Railway, pode ser restringido ao domínio do front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Status"])
async def root():
    """Endpoint de boas-vindas e verificação inicial."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "vault_path": str(settings.VAULT_DIR),
    }


@app.get("/health", tags=["Status"])
async def health():
    """Verificação de integridade operacional do sistema."""
    return {
        "status": "healthy",
        "vault_accessible": settings.VAULT_DIR.exists(),
        "lancedb_accessible": settings.LANCEDB_DIR.exists(),
    }
