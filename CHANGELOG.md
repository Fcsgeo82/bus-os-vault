# Changelog — Bus OS Vault

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Unreleased]

### Adicionado
- **Exclusão de Ordens de Serviço em cascata:** novo endpoint `DELETE /api/os/{uid}` em [os.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/os.py) que remove a OS mestra, as notas de eventos vinculadas (por `os_origem`), os anexos Markdown em `03_Anexos/` (slug padrão e varredura por referência, cobrindo slugs legados) e os CSVs originais em `data/attachments/`, seguido de reindexação automática do RAG (LanceDB + BM25).
- **Botão de exclusão na interface:** ícone `Trash2` em cada card de OS na sidebar de consulta ([page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx)) com confirmação nativa (`window.confirm`) antes da exclusão e atualização imediata da lista.
- **Feedback visual via Toast:** novo componente [Toast.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/ui/Toast.tsx) com notificações de sucesso/erro após a exclusão (auto-dismiss em 5s, estilo glassmorphism consistente com o design system).

### Testes
- Novo `test_excluir_os_e_artefatos_vinculados` em [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) validando o fluxo completo: ingestão temporária → exclusão em cascata → verificação de remoção dos arquivos no Vault → 404 ao consultar → ausência da OS nos resultados do RAG.
- Suíte completa: **11/11 testes pytest aprovados**.

---

## [0.3.0] - 2026-09-11

### Corrigido
- **Carregamento de variáveis de ambiente:** chaves adicionadas ao `.env` após o servidor já estar rodando não eram carregadas (`pydantic-settings` lê o `.env` uma única vez no import; `uvicorn --reload` não observa o `.env`). Documentada a necessidade de reiniciar o backend após alterar o `.env`.
- **Modelos Gemini obsoletos:** embeddings `text-embedding-004` → `gemini-embedding-001`; chat `gemini-2.0-flash` → `gemini-2.5-flash` (config, `.env`, `.env.example` e `docker-compose.yml`).
- **Formato da resposta do SDK Gemini:** embeddings lidos de `res.embeddings[0].values` (antes `res.embedding.values`).
- **Esgotamento de cota (429) no Gemini:** embeddings agora enviados em lote (1 única chamada) e busca por provedores sem cota diária restritiva.

### Adicionado
- **Provedor LLM plugável:** `LLM_PROVIDER=gemini|openrouter`. Novo `_call_openrouter()` (httpx, API compatível com OpenAI) em [generator.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/generator.py) com fallback em cadeia OpenRouter → Gemini → síntese local das notas.
- **Embeddings locais como primário:** Sentence-Transformers `all-MiniLM-L6-v2` (384 dims normalizados) em [embeddings.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/embeddings.py), com Gemini (`gemini-embedding-001`) e hash como fallbacks. Dependência adicionada ao `requirements.txt`.
- **Filtros com popup no FilterBar:** busca por linhas e consórcios reais (via `GET /api/os/lines/all`, 5 linhas no seed) e opção de vigência `Só Vigentes | Todas`.
- **Correção de sobreposição do popup:** dropdown renderizado via React Portal em `document.body` com `position: fixed` e `z-index: 9999` — escapa do stacking context criado pelo `backdrop-filter` do `.glass-panel`.
- **Compartilhamento via Túnel (sem admin/firewall):** `TUNNEL_ENABLED=true` gera ao iniciar uma URL pública automaticamente (Cloudflare Quick Tunnel ou localtunnel, com fallback `auto`). Binário portátil cloudflared em `%TEMP%` e cliente localtunnel em `%TEMP%/bus-os-lt/` — instalação sem admin. Banner exibe URL de compartilhamento no terminal.
- **`.env.example`:** documentadas as novas chaves (`LLM_PROVIDER`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `TUNNEL_ENABLED`, `TUNNEL_PROVIDER`).

### Testes
- 10/10 testes pytest aprovados (2 warnings de depreciação `table_names()` → `list_tables()`).
- Validação manual: chat direto (2,8 s) e via proxy (8 s); busca retornando 3 resultados; frontend 200 com proxy `/api/:path*` → `127.0.0.1:8000`.

---

## [0.2.0] - 2026-09-10

### Adicionado
- **Módulo de Ingestão de Novos Dados (Fase 2):**
  - Endpoint `POST /api/os/ingest` com suporte a `multipart/form-data` para envio unificado de metadados, lista de notas de eventos e arquivos CSV dos anexos I e II.
  - Modelos Pydantic v2 `NotaEventoInput`, `OSIngestPayload` e `OSIngestResponse`.
  - Escrita atômica no cofre para a nova OS mestra, notas de evento granulares, novos anexos sumarizados e criação automática de Hubs de Linhas.
  - Atualização automática de linhagem histórica quando a OS é do tipo `Retificada` (marca a OS anterior como `Substituída` e vincula `retificada_por`).
  - Sincronização automática em tempo real do motor RAG (LanceDB e BM25) ao cadastrar uma nova OS.
  - Componente de formulário web [DataEntryForm.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/entry/DataEntryForm.tsx) com validação, dropzones para CSVs e gerenciador dinâmico de múltiplas notas de eventos.
  - Sistema de abas na interface do usuário ([page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx)) alternando entre `Consulta & Chat RAG` e `Nova Ordem de Serviço`.
  - Suíte de testes de ingestão [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) (10 de 10 testes aprovados).
  - Plano de implementação da fase 2 arquivado em [docs/implementation_plan_fase2_ingestao.md](file:///c:/github_repositories/bus-os-vault/docs/implementation_plan_fase2_ingestao.md).

---

## [0.1.0] - 2026-09-10

### Adicionado
- **Documentação de Engenharia:**
  - `docs/architectural_analysis.md`: Análise profunda de arquitetura e trade-offs.
  - `docs/implementation_plan.md`: Plano de implementação detalhado com foco no MVP RAG.
  - `CONTEXT.md`, `README.md`, `AGENTS.md`, `memory.md`.
- **Backend (FastAPI + Python 3.12+):**
  - Modelos de domínio Pydantic v2: `OSMestra`, `NotaEvento`, `TipoOS`, `StatusVigencia`, `TipoEvento`, `Consorcio`.
  - Gerenciador de cofre Obsidian (`VaultWriter`) com operações atômicas em Markdown (`.tmp` → rename).
  - Parser sintetizador de CSVs reais (`CSVAttachmentParser`) para ANEXO I (117 colunas de viagens sumarizadas) e ANEXO II (desvios de itinerário).
  - Script de Seed do Vault (`seed_vault.py`): Ingestão inicial de 817 serviços e 475 desvios da pasta `referências/`.
- **Motor RAG Híbrido:**
  - Chunker hierárquico com enriquecimento de Frontmatter e preservação de Wikilinks.
  - Camada de persistência vetorial LanceDB (`vector_store.py`).
  - Indexador léxico BM25 (`lexical_searcher.py`).
  - Recuperador híbrido com fusão via Reciprocal Rank Fusion (`RRF k=60`) e filtros de vigência temporal.
  - Sintetizador e gerador de respostas com Google Gemini Flash e citação em Wikilinks.
  - Endpoints REST `/api/rag/chat`, `/api/rag/search`, `/api/rag/sync`, `/api/os`.
- **Frontend (Next.js 15 + React 19):**
  - Design System em Vanilla CSS com dark mode, glassmorphism e cores HSL.
  - Painel de Chat RAG (`ChatContainer`) com histórico, sugestões rápidas e balões estilizados.
  - Cartões de citação de fontes (`SourceCard`) com relevância e trechos.
  - Barra de filtros operacionais (`FilterBar`) por vigência, linha e consórcio.
  - Drawer modal de leitura de notas do Vault (`NoteViewerModal`) com inspeção de Frontmatter YAML.
- **Qualidade e Deploy:**
  - 9 testes automatizados com pytest (100% de aprovação).
  - Dockerfiles e `docker-compose.yml` para orquestração e deploy imediato (Railway).
