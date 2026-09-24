# Changelog — Bus OS Vault

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [0.10.0] - 2026-09-24

### Adicionado
- **Filtro por OS nos Filtros RAG:** [FilterBar.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/filters/FilterBar.tsx) — os filtros por **linha** e **consórcio** foram substituídos por um seletor de **OS** (popup multi-seleção alimentado por `GET /api/os`), que restringe os arquivos consultados ao escopo da(s) OS selecionada(s). Filtros ativos: `apenas_vigentes`, `os_titulos` (lista de títulos) e `ano_mes`.
- **Campo `os_titulo` no chunking:** [chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py) — cada chunk recebe o título da OS de origem (extraído do wikilink `os_origem` do frontmatter ou o próprio título em notas mestras); persistido no LanceDB e no metadata dos resultados de busca.

### Corrigido
- **Erro de runtime no chunking de parágrafos:** o ramo `else` de [chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py) usava a variável `sub_body` (inexistente fora do laço), derrubando a reindexação em lotes (`cannot access local variable 'sub_body'`). Corrigido para `body`.
- **Extração de título de OS com colchetes aninhados:** wikilinks como `[[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]` eram truncados (perdiam o `]` final), fazendo o filtro por OS da 174 não retornar resultados. Extração agora via `find('[[')`/`rfind(']]')`.

### Melhorado
- **Pool de candidatos com filtro por OS:** [hybrid_retriever.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/hybrid_retriever.py) amplia o pool de recuperação (×5) quando `os_titulos` está ativo, evitando que chunks da OS selecionada fiquem fora do top-K global.

### Escopo
- Filtros RAG: "Linhas" e "Consórcios" **removidos** da UI; novo seletor "OS" adicionado. Busca da linha 104 continua recuperando Linha 104 + ANEXO II (174/178/179); filtros 174/178/179 e multi-OS validados na API.
- 9 testes passando (chunker + RAG, incl. `test_hybrid_retriever_filtro_por_os`); `tsc --noEmit` e `next build` limpos.

---

## [0.9.1] - 2026-09-23

### Corrigido
- **Indexação de anexos do cofre:** `_chunk_table` em [chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py) reescrito de forma **iterativa** (sem recursão). O algoritmo anterior entrava em `RecursionError` com tabelas grandes (ANEXO I/II, 39–80 KB), fazendo o indexador pular silenciosamente os 6 arquivos de `03_Anexos` (452 arquivos no cofre, apenas 446 indexados, 0 chunks de anexo). Como desvios/itinerários alternativos vivem nos ANEXO II, consultas como "Quais desvios de itinerário existem para a linha 104?" retornavam vazio. Agora o cofre indexa 452/452 arquivos com 0 falhas (2736 chunks).
- **Visibilidade de falhas de indexação:** [indexer.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/indexer.py) agora coleta os arquivos com erro no campo `falhas: [...]` do resultado e levanta exceção se nenhum chunk for gerado (antes falhava em silêncio, apenas com `print`).

### Melhorado
- **Boost específico por linha:** [hybrid_retriever.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/hybrid_retriever.py) aplica `HUB_BOOST` (agora `2.5` em [config.py](file:///c:/github_repositories/bus-os-vault/backend/app/core/config.py)) apenas aos chunks que **tocam a linha consultada** (`**Código**` no texto ou código no título) via `_chunk_toca_linha` — não mais a todos os hubs de linha. Evita que hubs de outras linhas dominem o ranking quando a query cita uma linha específica.
- **Orientações de síntese:** [generator.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/generator.py) — o prompt de sistema agora instrui a priorizar as tabelas dos ANEXO II ao responder sobre desvios/itinerários alternativos (a seção "Notas de Eventos Vinculadas" de um hub não é a única fonte).
- **Deprecation removida:** [vector_store.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/vector_store.py) — `table_names()` → `list_tables()`.

### Adicionado
- **Testes de regressão:** [test_chunker.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_chunker.py) (5 testes: tabela grande sem RecursionError, ANEXO II real, limites e presença do token `104`); fixture `indice_pronto` em [test_rag.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_rag.py) reconstrói o BM25 nos testes de integração.
- **Plano:** [docs/implementation_plan_fix_recuperacao_rag.md](file:///c:/github_repositories/bus-os-vault/docs/implementation_plan_fix_recuperacao_rag.md) documentando causa raiz, etapas e resultados.

### Escopo
- Consulta "Quais desvios de itinerário existem para a linha 104?" agora recupera a Linha 104 e os ANEXO II (174/178/179) e o LLM sintetiza a resposta citando os anexos.
- 8 testes passando (RAG + chunker).

---

## [0.9.0] - 2026-09-23

### Adicionado
- **Provedor LLM NVIDIA NIM (free tier):** novo provider direto em [generator.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/generator.py) (`_call_nvidia_nim`, endpoint OpenAI-compatível `https://integrate.api.nvidia.com/v1`) selecionável via `LLM_PROVIDER=nvidia_nim`. Novas env vars em [config.py](file:///c:/github_repositories/bus-os-vault/backend/app/core/config.py): `NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_BASE_URL`, `NVIDIA_NIM_MODEL` (default `nvidia/nemotron-3-super-120b-a12b`).
- **Resiliência no OpenRouter:** `_call_openrouter` em [generator.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/generator.py) agora lê o campo `error` do corpo (HTTP 200 não é garantia de sucesso) e faz retry (3 tentativas) quando o upstream responde `provider_overloaded` — comum em modelos gratuitos compartilhados. Antes, sobrecarga da NVIDIA no OpenRouter virava a mensagem genérica "Resposta vazia do OpenRouter".
- **`PLANO_MELHORIAS.md`:** documento com o plano de melhorias do projeto (7 etapas); etapas 4, 5 e 6 implementadas nesta release.

### Melhorado
- **Limites de contexto do LLM otimizados (Etapa 4):** em [config.py](file:///c:/github_repositories/bus-os-vault/backend/app/core/config.py), `TRECHO_MAX_CHARS` 800→1000, `CONTEXT_MAX_CHARS` 600→1000 e `CONTEXT_MAX_DOCS` 6→8. Mais contexto por consulta para respostas de melhor qualidade sem extrapolar custos.
- **Detecção de categoria por frontmatter (Etapa 5):** [chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py) agora lê o campo `category` do frontmatter (valores esperados: `os_mestra`, `nota_evento`, `linha_servico`, `anexo_operacional`, `outros`) antes do fallback por pasta. Sobrescrita via metadata com compatibilidade retroativa total.
- **Chunking de tabelas adaptativo (Etapa 6):** `_chunk_table` em [chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py) calcula o tamanho médio de linha (amostra de 5) e ajusta dinamicamente o número de linhas por chunk entre `max_rows//2` e `max_rows*2` para caber em `CHUNK_MAX_CHARS`, com divisão recursiva de chunks que ainda estouram o limite. Substitui a contagem fixa de linhas; reduz chunks grandes demais em tabelas densas do ANEXO I.

### Escopo
- `.env.example` documentado com as novas chaves NVIDIA NIM.

---

## [0.8.0] - 2026-09-18

### Melhorado
- **Pipeline de busca RAG reformulado:** busca por dados tabulares (ANEXO I) agora funciona corretamente.
  - **Table-aware chunking** ([chunker.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/chunker.py)): tabelas Markdown são divididas em sub-chunks de 10 linhas com sobreposição de 2, respeitando limite de 1500 caracteres por chunk. Antes, uma tabela de 769 linhas virava 4 chunks de 10.000+ chars que estouravam o embedding model (512 tokens).
  - **Resumos em linguagem natural** ([csv_parser.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/csv_parser.py)): ANEXO I agora gera seção "Resumo por Linha" com frases como "A linha 010 possui extensão de 8.460 km, com 37 viagens e 315.02 km percorridos em dia útil" — ideais para embedding semântico.
  - **Boost para hubs** ([hybrid_retriever.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/hybrid_retriever.py)): chunks de hub de linha recebem multiplicador 1.5x no score RRF quando a query contém código numérico de linha.
  - **Truncamento de trecho** ([hybrid_retriever.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/hybrid_retriever.py)): trecho retornado limitado a 800 chars (antes: texto integral de 10.000+ chars).
  - **Contexto do LLM limitado** ([generator.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/generator.py)): máximo de 6 documentos com 600 chars cada no contexto enviado ao LLM (antes: todos os trechos sem limite).
  - **Filtro ano_mes** ([hybrid_retriever.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/hybrid_retriever.py)): parâmetro `ano_mes` agora é aplicado na filtragem (antes era aceito mas ignorado).
  - **Campo is_hub** ([vector_store.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/rag/vector_store.py)): schema LanceDB inclui flag booleana `is_hub` para identificar chunks de hub de linha.
  - **Novos parâmetros de config** ([config.py](file:///c:/github_repositories/bus-os-vault/backend/app/core/config.py)): `CHUNK_MAX_CHARS`, `CHUNK_TABLE_ROWS`, `CHUNK_TABLE_OVERLAP`, `TRECHO_MAX_CHARS`, `CONTEXT_MAX_CHARS`, `CONTEXT_MAX_DOCS`, `HUB_BOOST`.

### Escopo
- Vault reindexado: 452 arquivos → 2852 chunks (antes: ~1200 chunks com many exceeding model limits).

---

## [0.7.5] - 2026-09-18

### Corrigido
- **Exclusão em cascata robusta no Windows:** todos os `unlink()` e `shutil.rmtree()` no endpoint `DELETE /api/os/{uid}` ([os.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/os.py)) agora são envoltos em `try/except OSError`, evitando crash (500) por falhas de encoding de nomes de arquivo Unicode no Windows (ex.: `ç`, `ã`). Warnings são logados no console sem interromper a operação.
- **Artefatos órfãos removidos:** OS 999 ("Estudo de Exclusão") e nota de evento vinculada, criadas por teste automatizado e não limpas devido ao bug acima, foram removidas do vault.

---

## [0.7.4] - 2026-09-18

### Adicionado
- **Grafo do Cofre (v0.1):** nova aba "Grafo do Cofre" na interface principal com visualização interativa do relacionamento entre todas as notas do vault usando force-directed layout 3D (reagraph/WebGL).
  - **Backend:** novo módulo `vault_reader.py` com `list_all_notes()` que varre todas as pastas do vault, extrai metadados do frontmatter e resolve wikilinks `[[...]]` do conteúdo. Novo endpoint `GET /api/vault/graph` retorna a estrutura completa do grafo (uid, title, category, wikilinks).
  - **Frontend:** novo componente `VaultGraph.tsx` com `GraphCanvas` (reagraph), filtros por categoria (OS/Evento/Linha/Anexo), estatísticas (nós/arestas) e legenda. Novo utilitário `build-vault-graph.ts` transforma dados crus da API em formato `GraphCanvas`. Novo arquivo de tipos `vault-graph.ts`.
  - **Categorias e cores:** OS (azul `#38bdf8`), Evento (amarelo `#f59e0b`), Linha (verde `#10b981`), Anexo (violeta `#8b5cf6`).

---

## [0.7.3] - 2026-09-17

### Adicionado
- **Ingestão da OS 179 (retificação da OS 178):** "179 - OS 2026.09 - Setembro 1º Estudo ret" cadastrada no cofre com 5 notas de evento, ANEXO I (810 serviços) e ANEXO II (529 desvios). OS 178 marcada como `Substituída` com `retificada_por` apontando para OS 179.
- **Sincronização de hubs:** 435 hubs de linha atualizados com dados da OS 179.

### Corrigido
- **Notas de evento criadas com nome legado (sem slug da OS):** as 5 notas de evento da OS 179 foram ingeridas antes da correção v0.7.2 ser recarregada, resultando em nomes `NOTA-{ano_mes}-{índice}-{título}` em vez de `NOTA-{slug-da-os}-{índice}-{título}`. Arquivos renomeados manualmente para o padrão correto e 30 wikilinks atualizados na OS 178, OS 179 e 24 hubs.

---

## [0.7.2] - 2026-09-17

### Corrigido
- **Colisão de nomes de notas de evento entre OS do mesmo mês (perda de dados):** o nome do arquivo de evento era `NOTA-{ano_mes}-{índice}-{título}`, sem qualquer identificação da OS. Assim, duas OS do mesmo mês com notas de evento de título semelhante geravam o **mesmo caminho** e a segunda sobrescrevia a primeira (caso real: evento da OS 178 sobrescrito pelo evento #01 da OS 179). O nome passou a ser `NOTA-{slug-da-os}-{índice}-{título}` em [ingest.py](file:///c:/github_repositories/bus-os-vault/backend/app/api/ingest.py), tornando cada nota única por OS. O esquema cobre OS distintas do mesmo mês, estudos diferentes (`Setembro 1º Estudo`, `Setembro 2º Estudo`) e retificações (`ret`, `ret1`, `ret2`), já que o slug inclui o número e os sufixos da OS.
- **Renomeação das notas de evento ao corrigir o título da OS:** como o nome da nota agora embute o slug da OS, [os_correction_service.py](file:///c:/github_repositories/bus-os-vault/backend/app/services/vault/os_correction_service.py) passou a renomear também os arquivos de evento (novo `_rename_notes_with_slug`), mantendo os wikilinks de OS e hubs consistentes. Os contadores `arquivos_renomeados` da resposta agora incluem essas notas.

### Testes
- Novo teste de regressão em [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py): duas OS do mesmo mês com notas de evento homônimas geram arquivos distintos.
- [test_os_correction.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_os_correction.py) ajustado para localizar a nota de evento pelo novo nome (antes e depois da retitulação) e validar que o arquivo antigo deixa de existir.
- Suíte afetada: **14/14 testes aprovados**.

---

## [0.7.1] - 2026-09-17

### Corrigido
- **Nova OS não aparecia na listagem "Ordens de Serviço" logo após o cadastro:** o `fetch` de `GET /api/os` em [page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx) (`fetchOsList`) podia ser servido pelo cache do navegador, pois a URL era idêntica à da carga inicial. A listagem só refletia o cadastro após um recarregamento manual (F5). Adicionado *cache-busting* com timestamp (`/api/os?t=${Date.now()}`), forçando uma requisição real ao backend a cada atualização. A correção beneficia também a atualização da lista após exclusão, correção de OS e sincronização do cofre (todas usam `fetchOsList`).

---

## [0.7.0] - 2026-09-17

### ⚠️ Breaking change
- **`processo_rio` e `despacho` agora são listas** (`List[str]`) em vez de stringes únicas nos payloads e nas respostas da API (`POST /api/os/ingest`, `GET /api/os`, `POST /api/os/{uid}/correct`). `GET /api/os` passou a retornar `meta["processo_rio"]` / `meta["despacho"]` como arrays (antes, string ou ausentes).

### Adicionado
- **Múltiplos processos e despachos por OS (máx. 2, ordem preservada):** [os_schema.py](file:///c:/github_repositories/bus-os-vault/backend/app/models/os_schema.py) passou a aceitar até 2 itens com ordem preservada em `OSMestraBase`, `OSIngestPayload` e `OSCorrectionPayload`. Validação em `field_validator(mode="before")` continua aceitando string legada (convertida automaticamente em lista de 1).
- **Validação de formato do Processo.Rio:** regex `^\d{6}\.\d{6}\/\d{4}-\d{2}$` aplicada ao(s) processo(s) administrativo(s) (ex.: `000399.000000/2026-01`); valor inválido ou mais de 2 itens retorna `422 Unprocessable Entity`. Despachos seguem sem padrão rígido (apenas máx. 2).
- **Migração automática de dados legados:** novo script [migrate_processos.py](file:///c:/github_repositories/bus-os-vault/backend/app/scripts/migrate_processos.py) converte threads OS cujo frontmatter ainda trazia `processo_rio`/`despacho` como string em listas de 1 elemento (escrita atômica, idempotente). Executado automaticamente no startup ([main.py](file:///c:/github_repositories/bus-os-vault/backend/app/main.py)) antes da indexação RAG.
- **Interface com múltiplos campos:** novo componente reutilizável [MultiInputField.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/ui/MultiInputField.tsx) (inputs empilhados, botão "Adicionar" até o limite de 2, remoção por item, validação em blur e mensagem de erro inline), aplicado em [DataEntryForm.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/entry/DataEntryForm.tsx) (cadastro) e [OSCorrectionModal.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/entry/OSCorrectionModal.tsx) (correção). Valores vazios são filtrados antes do envio.
- **Exibição em listas:** `GET /api/os` e o modal de leitura de notas agora renderizam múltiplos processos separados por vírgula em [page.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/app/page.tsx) e [NoteViewerModal.tsx](file:///c:/github_repositories/bus-os-vault/frontend/src/components/vault/NoteViewerModal.tsx).

### Testes
- [test_ingest.py](file:///c:/github_repositories/bus-os-vault/backend/tests/test_ingest.py) ampliado: ordem preservada com 2 processos/despachos, rejeição de 3 processos e de formato inválido (422), e conversão de string legada em lista.
- Suíte completa: **31/31 testes pytest aprovados** (13 min) e `tsc --noEmit`/`npm run build` limpos no frontend.

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
