# Changelog — Bus OS Vault

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [0.6.1] - 2026-09-17

### Corrigido
- **Hubs presos na OS passada quando a linha era tocada só por nota de evento:** em [line_hub_service.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/line_hub_service.py), `sync_hubs_for_os` agora **migra a proveniência** (`os_origem`, vigência e histórico) de hubs existentes para a OS mais recente que referencia a linha apenas via evento (sem grade no ANEXO I), **preservando a grade operacional real** (schema v2) e as notas de eventos anteriores. A vigência nunca regressa para uma data anterior.
- **Exclusão em cascata deixava hubs referenciando a OS excluída:** `DELETE /api/os/{uid}` em [os.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/os.py) agora invoca o novo `detach_hub_references()`, que remove as referências da OS excluída dos hubs, **promove a próxima OS mais recente** para `os_origem` (com a vigência dela) e **remove hubs órfãos** (que ficam sem nenhuma OS restante). A resposta passou a incluir `hubs_atualizados`.
- **Parsing de wikilinks com `]]` internos:** a extração das OS relacionadas em hubs usa regex gulosa para preservar títulos como `174 - OS 2026.08 - Agosto 2º Estudo [ret4]` (antes, o `]` final do `[ret4]` era consumido).

### Testes
- Novo [test_line_hub_service.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_line_hub_service.py): hub tocado só por evento de OS recente migra de proveniência preservando os dados reais (idempotente); `detach_hub_references` remove as referências e promove a OS anterior após exclusão.
- [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) ampliado: exclusão em cascata agora também remove o hub mínimo criado para a linha tocada só pelo evento da OS excluída (órfão) — e o RAG não retorna referências residuais.
- Suíte completa: **27/27 testes pytest aprovados**.

---

## [0.6.0] - 2026-09-16

### Adicionado
- **Correção/Edição de Ordens de Serviço:** novo endpoint `POST /api/os/{uid}/correct` em [os.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/os.py) com suporte a correção de campos escalares (`tipo_os`, `status_vigencia`, `processo_rio`, `despacho`, `data_publicacao`, `inicio_vigencia`, `fim_vigencia`, `arquivo_gtfs`) e retitulação completa da OS.
- **Serviço de correção com propagação em cascata:** novo [os_correction_service.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/os_correction_service.py) que, ao alterar o `title`, propaga a mudança para o UID, nome do arquivo mestra, wikilinks `[[...]]`, notas de eventos, hubs de linha (`02_Linhas_e_Servicos/`), anexos (`03_Anexos/`), diretórios e CSVs internos em `data/attachments/` (prefixo `<slug>-anexo-i/ii.csv`), seguido de reindexação automática do RAG (LanceDB + BM25). Resumo da operação retorna `arquivos_atualizados`, `pastas_renomeadas`, `arquivos_renomeados` e `rag_reindexado`.
- **Validação de título unificada:** `validate_os_title_for_filename()` em [vault_writer.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/vault_writer.py) (raises `ValueError`; rejeita `<>:"/\\|?*`, espaços nas bordas, ponto final e nomes reservados do Windows), compartilhada entre ingestão e correção — título inválido vira `422 Unprocessable Entity`.
- **Guard slug idêntico:** correções em que o slug não muda (ex.: `1o` → `1º`) não renomeiam nem removem pastas de anexos/`attachments` (evita `os.replace` com origem=destino e deleção acidental de anexos).
- **Interface de correção:** modal [OSCorrectionModal.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/entry/OSCorrectionModal.tsx) acessado pelo botão de lápis em cada card de OS na sidebar de consulta ([page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx)), com aviso de propagação quando o título é alterado e atualização imediata da listagem após salvar. A listagem de OS passa a expor `fim_vigencia` e `arquivo_gtfs`.
- **Vault corrigido em produção:** OS "179 - OS 2026.09 - Setembro 1º Estudo" retificada para **178** no cofre real (mestra, nota de evento, 410+ hubs de linha, anexos e CSVs; 414 arquivos atualizados, RAG reindexado; zero referências residuais).

### Corrigido
- **`NameError` na coleta do pytest:** o `@app.exception_handler(Exception)` era registrado antes da criação de `app = FastAPI(...)` em [main.py](file:///c:/github_repositories/bus-os-vault/backend/app/main.py); movido para depois da instância.

### Testes
- Novo [test_os_correction.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_os_correction.py) (5 testes): retitulação completa com renomeação de hub/apostilha e anexo simulado (181→180), correção de campo escalar, título inválido → 422, OS inexistente → 404 e regressão do caso "slug idêntico" preservando anexos/CSVs.
- [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) e [test_line_hub_service.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_line_hub_service.py) ampliados para cobrir o novo fluxo de correção.
- Suíte completa: **25/25 testes pytest aprovados** e `tsc --noEmit`/`npm run build` limpos no frontend.

---

## [0.5.0] - 2026-09-15

### Adicionado
- **Hubs de Linha com dados reais (schema v2):** novo [line_hub_service.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/line_hub_service.py) que gera hubs em `02_Linhas_e_Servicos/` (formato `Linha {codigo}.md`) com frontmatter `schema_version: 2` (`uid`, `codigo_linha`, `vista`, `consorcio`, `type: linha_servico`, `os_origem`, `vigencia_inicio`, `data_atualizacao`, `tags`). Cada hub traz, por sentido, o resumo operacional e a grade horária completa (distribuição de 14 faixas x 4 tipos de dia: Dia Útil, Sábado, Domingo e Ponto Facultativo), além de itinerários alternativos/desvios, ordens de serviço relacionadas e notas de eventos vinculadas (wikilinks sem `.md`).
- **Parser do ANEXO I estendido:** [csv_parser.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/csv_parser.py) agora expõe `partidas_ponto_facultativo`, `km_ponto_facultativo` e o dict `hourly` com os 4 tipos de dia; o resumo do anexo ganhou a coluna "Viagens Pt. Fac.".
- **Integração no fluxo de ingestão:** [ingest.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/ingest.py) sincroniza os hubs toda vez que uma OS é cadastrada (`sync_hubs_for_os`), coletando também as linhas citadas apenas em notas de eventos.
- **Script de rebuild:** [rebuild_line_hubs.py](file:///c:/github_repositories/bus-os-vault/backend/app/scripts/rebuild_line_hubs.py) regenera os hubs a partir dos CSVs de `referências/`, reconstrói os resumos dos anexos, remove hubs órfãos (`remove_orphans=True` — excluiu o hub `Linha LECD999.md`) e reindexa o RAG (LanceDB + BM25).
- **Seed atualizado:** [seed_vault.py](file:///c:/github_repositories/bus-os-vault/backend/app/scripts/seed_vault.py) passou a usar `sync_hubs_for_os` com `remove_orphans=True` em vez do bloco MOC hardcoded.
- **Vault regenerado:** 435 hubs criados/atualizados a partir dos dados reais da OS 174 (817 serviços do ANEXO I com vista única); 2ª execução idempotente (0 criados / 435 atualizados).

### Corrigido
- **Catálogo de Hubs de Linhas na interface:** o card lateral "Hubs de Linhas (MOC)" exibia uma lista fixa de 4 hubs; agora consome `GET /api/os/lines/all` e lista os 435 hubs reais do cofre (código da linha sem o prefixo "Linha", preview de 24 + "Ver todas" para expandir).
- **Versão da aplicação:** `APP_VERSION` promovida para `0.5.0` ([config.py](file:///c:/github_repositories/bus-os-vault/backend/app/core/config.py)).

### Testes
- Novo [test_line_hub_service.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_line_hub_service.py) (7 testes: agrupamento, conteúdo real, sync com remoção de órfãos, sync sem anexos preserva hubs existentes, OS 174 real com 435 hubs).
- [test_csv_parser.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_csv_parser.py) validando `hourly`, Ponto Facultativo e consistência de partidas; [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) valida hub para linha citada só em evento (LECD999).
- Suíte completa: **16/16 testes pytest aprovados** e `tsc --noEmit` limpo no frontend.

---

## [0.4.0] - 2026-09-15

### Adicionado
- **Exclusão de Ordens de Serviço em cascata:** novo endpoint `DELETE /api/os/{uid}` em [os.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/os.py) que remove a OS mestra, as notas de eventos vinculadas (por `os_origem`), os anexos Markdown em `03_Anexos/` (slug padrão e varredura por referência, cobrindo slugs legados) e os CSVs originais em `data/attachments/`, seguido de reindexação automática do RAG (LanceDB + BM25).
- **Botão de exclusão na interface:** ícone `Trash2` em cada card de OS na sidebar de consulta ([page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx)) com confirmação nativa (`window.confirm`) antes da exclusão e atualização imediata da lista.
- **Feedback visual via Toast:** novo componente [Toast.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/ui/Toast.tsx) com notificações de sucesso/erro após a exclusão (auto-dismiss em 5s, estilo glassmorphism consistente com o design system).

### Testes
- Novo `test_excluir_os_e_artefatos_vinculados` em [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) validando o fluxo completo: ingestão temporária → exclusão em cascata → verificação de remoção dos arquivos no Vault → 404 ao consultar → ausência da OS nos resultados do RAG.
- Suíte completa: **11/11 testes pytest aprovados** (16/16 na versão seguinte, 0.5.0).

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
