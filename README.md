# 🚌 Bus OS Vault

Sistema de gestão e consulta inteligente de Ordens de Serviço (OS) da rede de ônibus municipal, com armazenamento estruturado em Markdown (Obsidian Vault) e interface de busca semântica via RAG.

---

## Visão Geral

O **Bus OS Vault** é uma aplicação web fullstack que oferece:

1. **Painel RAG (Consulta Inteligente)** — Interface de chat para perguntas sobre o acervo de Ordens de Serviço, com busca semântica híbrida (vetorial + lexical).
2. **Formulário de Entrada** — Cadastro padronizado de novas OS com validação de campos, importação de planilhas CSV (viagens e itinerários) e geração automática de arquivos Markdown estruturados.
3. **Catálogo de Linhas** — Hubs por linha com dados reais das OS (grade horária completa em 4 tipos de dia, desvios/itinerários alternativos e notas de eventos vinculadas), gerados automaticamente na ingestão.
4. **Gestão de Acervo** — Exclusão de OS com confirmação, remoção em cascata de eventos e anexos (incluindo slugs legados), e reindexação automática do RAG.

## Stack Tecnológica

| Camada          | Tecnologia                           |
|-----------------|--------------------------------------|
| **Frontend**    | Next.js 15 (React 19)               |
| **Backend**     | FastAPI (Python 3.12+)              |
| **Validação**   | Pydantic v2 (backend) + Zod (frontend) |
| **LLM**         | Plugável via `LLM_PROVIDER`: OpenRouter (free tier) ou Google Gemini Flash |
| **Embeddings**  | Sentence-Transformers `all-MiniLM-L6-v2` (local), Gemini ou hash (fallback) |
| **Vector Store**| LanceDB (embedded)                  |
| **Busca Léxica**| rank_bm25                           |
| **Deploy**      | Railway (free tier)                 |
| **Idioma UI**   | Português (Brasil)                  |

## Estrutura do Projeto

```
bus-os-vault/
├── docs/                          # Documentação do projeto
│   └── architectural_analysis.md  # Análise arquitetural completa
├── backend/                       # FastAPI (Python)
│   ├── app/
│   │   ├── api/                   # Rotas da API
│   │   ├── core/                  # Config, settings
│   │   ├── models/                # Schemas Pydantic
│   │   ├── services/              # Lógica de negócio
│   │   │   ├── vault/             # Escrita/leitura do Vault
│   │   │   ├── rag/               # Pipeline RAG
│   │   │   └── ingest/            # Import de CSV
│   │   └── main.py
│   ├── vault/                     # Obsidian Vault (dados MD)
│   ├── data/                      # Vector store, índices
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                      # Next.js (React)
│   ├── src/
│   │   ├── app/                   # App Router pages
│   │   ├── components/            # Componentes React
│   │   └── lib/                   # Utilitários, schemas Zod
│   ├── package.json
│   └── Dockerfile
├── CONTEXT.md                     # Contexto do projeto e decisões
├── CHANGELOG.md                   # Histórico de mudanças
├── AGENTS.md                      # Instruções para agentes de IA
├── README.md                      # Este arquivo
└── docker-compose.yml             # Orquestração local/deploy
```

## Como Executar (em construção)

```bash
# Backend
cd backend
python -m venv .venv
# source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0

# Frontend
cd frontend
npm install
npm run dev
```

> Ao iniciar, o backend exibe no terminal as URLs **Local** e **Rede**. Use a URL de
> **Rede** (ex.: `http://10.31.4.229:8000`) para compartilhar o acesso com outros
> dispositivos na mesma rede local — isso exige `--host 0.0.0.0` (já incluído acima).

### Variáveis de Ambiente (`backend/.env`)

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave do Google AI Studio (https://aistudio.google.com/app/apikey) |
| `GEMINI_MODEL` | Modelo de chat Gemini (padrão `gemini-2.5-flash`) |
| `LLM_PROVIDER` | `openrouter` (padrão) ou `gemini` |
| `OPENROUTER_API_KEY` | Chave do OpenRouter (https://openrouter.ai/keys) |
| `OPENROUTER_MODEL` | Modelo OpenRouter; gratuitos terminam em `:free` (padrão `nvidia/nemotron-3-super-120b-a12b:free`) |
| `DEBUG` | `true`/`false` |
| `TUNNEL_ENABLED` | `true`/`false` — habilita URL pública (túnel) ao iniciar |
| `TUNNEL_PROVIDER` | `auto` (padrão, tenta cloudflare → localtunnel), `cloudflare` ou `localtunnel` |

> **Importante:** o `.env` é lido uma única vez no import do backend. **Reinicie o servidor** após alterá-lo (`uvicorn --reload` não observa o `.env`).

### Compartilhamento via Túnel (sem admin/firewall)

Se `TUNNEL_ENABLED=true` está definido, o backend gera automaticamente ao iniciar uma **URL pública** (Cloudflare ou localtunnel) que funciona de qualquer dispositivo, independente do firewall e da subnet.

**Pré-requisitos (já instalados neste ambiente):**
- **Cloudflare:** binário em `%TEMP%\cloudflared.exe` (portátil, sem instalação)
- **localtunnel:** cliente em `%TEMP%\bus-os-lt\` (requer Node.js no PATH)

```bash
# Habilitar no .env
echo TUNNEL_ENABLED=true >> backend/.env
echo TUNNEL_PROVIDER=auto >> backend/.env

# Reiniciar o backend
uvicorn app.main:app --reload --host 0.0.0.0
```

Exemplo de saída no terminal:
```
Iniciando túnel público (Cloudflare/localtunnel)...
Túnel público ativo (localtunnel).
============================================================
Bus OS Vault v0.6.1 pronto!
  Local:  http://127.0.0.1:8000
  Rede:   http://10.31.4.229:8000
  Docs:   http://10.31.4.229:8000/docs
  Tunel:  https://giant-shrimps-travel.loca.lt  (localtunnel)
============================================================
Compartilhe a URL 'Tunel' — funciona de qualquer dispositivo, sem firewall.
============================================================
```

## Status

🟢 **Em funcionamento** — MVP com painel RAG híbrido, formulário de entrada de OS e filtros por linha/consórcio/vigência. Decisões de design em [CONTEXT.md](./CONTEXT.md) e histórico em [CHANGELOG.md](./CHANGELOG.md).

## Licença

A definir.
