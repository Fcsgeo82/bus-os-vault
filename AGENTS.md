# Instruções para Agentes de IA — Bus OS Vault

> Este documento orienta agentes de IA (Copilot, Gemini, Claude, etc.) sobre o contexto,
> convenções e restrições do projeto.

---

## Sobre o Projeto

**Bus OS Vault** é um sistema web de gestão e consulta inteligente de Ordens de Serviço (OS)
da rede de ônibus municipal. Combina armazenamento estruturado em Markdown (Obsidian Vault)
com busca semântica via RAG (Retrieval-Augmented Generation).

## Arquitetura

- **Padrão:** Web Fullstack desacoplado (API REST)
- **Frontend:** Next.js 15 (App Router, React 19) — diretório `frontend/`
- **Backend:** FastAPI (Python 3.12+) — diretório `backend/`
- **LLM:** Plugável via `LLM_PROVIDER` — OpenRouter (free tier, padrão), NVIDIA NIM (free tier) ou Gemini Flash, com síntese fallback local
- **Embeddings:** Sentence-Transformers `all-MiniLM-L6-v2` (local), Gemini como fallback
- **Vector Store:** LanceDB (embedded)
- **Acesso externo:** Banner no startup com URLs Local/Rede; túnel Cloudflare/localtunnel via `TUNNEL_ENABLED` (sem admin/firewall)
- **Deploy:** Railway

## Convenções de Código

### Backend (Python)
- Python 3.12+
- Validação com Pydantic v2
- Type hints obrigatórios em todas as funções
- Docstrings em português (BR) para módulos e funções públicas
- Imports absolutos a partir de `app.`
- Async/await para I/O (aiofiles, httpx)
- Testes com pytest

### Frontend (TypeScript/React)
- TypeScript strict mode
- Componentes funcionais com hooks
- Validação client-side com Zod
- Nomes de componentes em PascalCase
- Nomes de arquivos em kebab-case
- CSS Modules ou Vanilla CSS (sem Tailwind a menos que especificado)

### Markdown / Vault
- Frontmatter YAML obrigatório em toda nota
- Campo `schema_version` para versionamento de schema
- UIDs únicos por nota
- Escrita atômica (temp file → rename)

## Idioma

- **UI:** Português (Brasil)
- **Código:** Inglês (variáveis, funções, classes)
- **Documentação:** Português (Brasil)
- **Commits:** Português (Brasil) — formato: `tipo: descrição curta`

## Restrições

- NÃO instalar dependências globalmente. Usar venv (Python) e npm (Node).
- NÃO usar APIs pagas sem confirmação explícita. O projeto usa exclusivamente free tiers.
- NÃO alterar o schema do Frontmatter sem atualizar `schema_version` e documentar em CONTEXT.md.
- NÃO expor chaves de API em código. Usar variáveis de ambiente (.env).
- Preservar a separação frontend/backend. Sem lógica de negócio no frontend.

## Documentos de Referência

- [CONTEXT.md](./CONTEXT.md) — Decisões de design, requisitos e perguntas pendentes
- [CHANGELOG.md](./CHANGELOG.md) — Histórico de mudanças
- [memory.md](./memory.md) — Memória persistente e decisões consolidadas
- [docs/architectural_analysis.md](./docs/architectural_analysis.md) — Análise arquitetural completa
