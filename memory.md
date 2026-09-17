# Memória do Projeto — Bus OS Vault

> Registro persistente de aprendizados, decisões consolidadas, padrões adotados e pontos de atenção.

---

## 1. Perfil e Domínio

- **Aplicação:** Gestão e consulta inteligente de Ordens de Serviço (OS) do transporte público coletivo por ônibus.
- **Entidades Centrais:**
  - **OS Mestra:** Documento formal que agrega metadados de processo, vigência e arquivos associados.
  - **Notas de Evento:** Granularidade por alteração (tipos: `Inclusão`, `Remoção`, `Ajuste`, `Correção/Retificação`).
  - **ANEXO I:** Matriz horária de partidas e quilometragens (117 colunas, 4 tipos de dia).
  - **ANEXO II:** Tabela de desvios e itinerários alternativos (8 colunas com eventos e ativações).

---

## 2. Decisões Técnicas Consolidadas

1. **Arquitetura Web Fullstack Desacoplada (Opção A):**
   - Frontend em Next.js 15 (React 19) com Vanilla CSS, Design System responsivo e navegação por abas.
   - Backend em FastAPI (Python 3.12+) com Pydantic v2 e endpoints assíncronos.
   - Banco Vetorial: LanceDB (embedded no filesystem sob `backend/data/lancedb`).
   - Busca Léxica: rank_bm25 em memória.
   - LLM: Plugável via `LLM_PROVIDER` — OpenRouter (free tier) ou Gemini Flash, com síntese fallback local.
   - Deploy: Railway (Dockerfiles e docker-compose.yml prontos).

2. **Fluxo de Ingestão de Novos Dados (Data Entry):**
   - Endpoint unificado `POST /api/os/ingest` que aceita payload JSON multipart e até dois arquivos CSV.
   - Criação atômica de notas no cofre e cópia de segurança dos CSVs originais em `backend/data/attachments/`.
   - Atualização automática de linhagem histórica quando a OS retifica uma anterior (`retifica_os` / `retificada_por`).
   - Sincronização automática em tempo real do motor RAG (LanceDB e BM25) sem necessidade de reiniciar o servidor.

3. **Estratégia de Ingestão de Anexos Grandes:**
   - O CSV de 117 colunas (ANEXO I) é sumarizado pelo `CSVAttachmentParser` em `ANEXO_I_Viagens_Resumo.md` por serviço/linha, permitindo chunking limpo sem estourar janelas ou degradar a recuperação.
   - O ANEXO II é convertido em tabela de desvios operacionais com colunas `Serviço`, `Vista`, `Consórcio`, `Sentido`, `Extensão`, `Evento`, `Descrição`, `Ativação`.

4. **Provedor LLM Plugável (Síntese):**
   - `LLM_PROVIDER=openrouter` (padrão) ou `gemini`; chaves em `OPENROUTER_API_KEY` / `GEMINI_API_KEY`.
   - Free tier do OpenRouter é mais confiável que a cota diária do Gemini (que esgota com 429).
   - Modelo padrão: `nvidia/nemotron-3-super-120b-a12b:free`. Descartados: `qwen/qwen3-8b:free` (404 descontinuado), `google/gemma-4-31b-it:free` (429), `thinkingmachines/inkling-small:free` (403 — somente agentic harnesses).

5. **Embeddings Locais como Primário:**
   - Ordem: Sentence-Transformers `all-MiniLM-L6-v2` (384 dims) → Gemini (`gemini-embedding-001`) → hash fallback.
   - Embeddings Gemini em lote em 1 única chamada para evitar 429.
   - Modelo local baixado para `~/.cache/huggingface`; warning de symlink no Windows é benigno.

6. **Popup de Filtros via React Portal:**
   - `.glass-panel` usa `backdrop-filter`, que cria stacking context; `z-index` de filhos não tem efeito.
   - Solução: `createPortal` para `document.body` com `position: fixed` e `z-index: 9999`; fecha em outside-click, scroll e resize.

7. **Variáveis de Ambiente lidas no import:**
   - `pydantic-settings` lê o `.env` uma única vez no import; `uvicorn --reload` não observa o `.env`.
   - Alterou o `.env`? Então reinicie o backend.

8. **Compartilhamento de Acesso (sem admin):**
   - O acesso externo via IP de rede depende do Firewall do Windows, que exige admin para liberar a porta.
   - Solução em duas camadas no startup: banner com URL **Rede** (LAN) e **Túnel público** (`TUNNEL_ENABLED=true`).
   - Rede atual bloqueia Cloudflare (`api.trycloudflare.com`) e ngrok; **localtunnel funciona** — por isso o `.env` usa `TUNNEL_PROVIDER=localtunnel`.
   - Binários portáteis: `cloudflared.exe` em `%TEMP%` e cliente `localtunnel` em `%TEMP%\bus-os-lt\` (Node.js requerido). Provisionamento sem admin.
   - O processo do túnel é iniciado no lifespan e encerrado no shutdown do uvicorn.

9. **Exclusão de OS em Cascata (Delete):**
   - Novo endpoint `DELETE /api/os/{uid}`; não conflita com `GET /api/os/{uid}` nem `GET /api/os/notes/{uid}` (métodos distintos).
   - Remoção em ordem: notas de eventos (`01_Notas_de_Eventos/`, por `os_origem`) → anexos (`03_Anexos/`) → CSVs (`data/attachments/`) → nota mestra (`00_Ordens_de_Servico/`) → reindexação RAG.
   - **Slugs legados:** os anexos da OS 174 usam slug fora do padrão (`OS_2026.08_Estudo2_ret4` ≠ `slugify(title)`); por isso a exclusão não depende apenas do slug — também varre `03_Anexos/` e `data/attachments/` inspecionando notas por `os_origem` e nomes de arquivo.
   - UI: confirmação nativa (`window.confirm`) + Toast de feedback; testes end-to-end em `test_ingest.py` (11/11 aprovados).

10. **Hubs de Linha com Dados Reais (schema v2, não-MOC):**
    - `line_hub_service.sync_hubs_for_os()` gera hubs em `02_Linhas_e_Servicos/` no formato `Linha {codigo}.md` com frontmatter `schema_version: 2` — a **única versão de schema** (v1 era MOC/placeholder; hubs reais exigem v2) → documentado em CONTEXT.md.
    - Campos do frontmatter: `uid`, `codigo_linha`, `vista`, `consorcio`, `type: linha_servico`, `os_origem`, `vigencia_inicio`, `data_atualizacao`, `tags` (`linha/{codigo}`, `consorcio/{slug}`, `tipo/municipal`).
    - Conteúdo por sentido (Ida/Volta): "## Planejamento Operacional de Viagens" (resumo + tabela "Distribuição Horária" de 9 colunas × 14 faixas por tipo de dia), "## Itinerários Alternativos e Desvios" (por evento), "## Ordens de Serviço Relacionadas" e "## Notas de Eventos Vinculadas" (wikilinks **sem** `.md`).
    - **Linhas citadas só em eventos** ("event-only"): criam hub mínimo apenas se ainda não existirem; nunca sobrescreve hub com dados reais.
    - **remove_orphans é opt-in** (`False` por padrão): ingestões rotineiras nunca apagam hubs (evita remover hubs de outras OS); somente `rebuild_line_hubs.py` e `seed_vault.py` usam `remove_orphans=True`.
    - Rebuild idempotente: 2ª execução → 0 criados / 435 atualizados; hub órfão `Linha LECD999.md` (OS 180 excluída, sem dono no vault) removido.
    - **Frontend:** o card lateral "Hubs de Linhas" consome `GET /api/os/lines/all` (não mais a lista MOC fixa); exibe apenas o código da linha (sem o prefixo "Linha"), com preview de 24 e link "Ver todas (N)" para expandir.

11. **Parser ANEXO I com grade horária completa:**
    - `csv_parser.py` expõe `partidas_ponto_facultativo` / `km_ponto_facultativo` e o dict `hourly` com os 4 tipos de dia (`dia_util`, `sabado`, `domingo`, `ponto_facultativo`) × 14 faixas (`00-01`…`23-24`).
    - Resumo do anexo (`ANEXO_I_Viagens_Resumo.md`) ganhou a coluna "Viagens Pt. Fac."; linha de rodapé do resumo passou a citar os 4 tipos de dia.
    - Script `rebuild_line_hubs.py` regenera os hubs e também os resumos dos anexos a partir dos CSVs de `referências/`, seguido de `index_entire_vault()`.

12. **Correção/Edição de OS (retitulação em cascata):**
    - Endpoint `POST /api/os/{uid}/correct`; campos escalares (tipo, status, processo, despacho, datas, GTFS) e `title` via `OSCorrectionPayload`.
    - **Retitulação propaga tudo:** UID, nome do arquivo mestra, wikilinks `[[...]]`, notas de eventos (`01_`), hubs de linha (`02_`, campo `os_origem`), anexos (`03_`) e CSVs em `data/attachments/` — inclusive renomeando o diretório `<old_slug>` → `<new_slug>` e os arquivos internos `<old_slug>-anexo-*.csv` → `<new_slug>-anexo-*.csv`. Termina com `index_entire_vault()`.
    - **Guard `old_slug != new_slug`:** quando o slug não muda (ex.: corrigir `1o` → `1º`), pastas de anexos/`attachments` **não** são renomeadas nem removidas — o bug real foi `shutil.rmtree(new_dir)` com old==new apagando a pasta do próprio anexo; coberto por teste de regressão.
    - **Validação compartilhada:** `vault_writer.validate_os_title_for_filename()` alimenta ingestão e correção (ValueError → 422); registros inválidos rejeitados antes de qualquer escrita.
    - Aplicação real: OS "179 …" → **178** no cofre (414 arquivos atualizados, 2 pastas + 1 arquivo renomeados, RAG reindexado; zero referências a "179").
    - UI: botão de lápis + `OSCorrectionModal` com aviso de propagação; listagem de OS expõe `fim_vigencia` e `arquivo_gtfs`.

13. **Invariante: hub de linha = OS mais recente que toca a linha (v0.6.1):**
    - **Caminho de anexo:** linha no ANEXO I da OS nova → hub totalmente sobrescrito (grade nova). Já valia desde 0.5.0.
    - **Caminho event-only:** linha citada só por nota de evento da OS nova → hub existente **migra proveniência** (`os_origem`, vigência) para a OS nova preservando a grade real e o histórico; cria hub mínimo só se não existir. **Vigência nunca regressa** (comparação ISO; títulos `[ret4]` não quebram o parsing de wikilinks — regex gulosa).
    - **Exclusão (`detach_hub_references`):** `DELETE /api/os/{uid}` remove as referências da OS nos hubs, promove a próxima OS mais recente para `os_origem` (com a vigência dela, lida da nota da OS) e **remove hubs órfãos** (nenhuma OS restante). Resposta inclui `hubs_atualizados`.
    - **Testes na integração usam linha própria ("9999"):** não poluem hubs reais do cofre ao validar o fluxo de exclusão.

14. **Múltiplos processos e despachos por OS (v0.7.0 — breaking change):**
    - `processo_rio` e `despacho` passaram de string única para `List[str]` (máx. 2, ordem preservada) em `OSMestraBase`, `OSIngestPayload` e `OSCorrectionPayload`; `GET /api/os` retorna arrays.
    - Validação em `field_validator(mode="before")` aceita string legada (normalizada para lista de 1) — retrocompatível na entrada. Processo com regex Processo.Rio `^\d{6}\.\d{6}/\d{4}-\d{2}$`; despacho sem padrão rígido.
    - Migração idempotente `migrate_processos.py` roda no lifespan antes da indexação RAG (string → lista no frontmatter).
    - Frontend: componente reutilizável `ui/MultiInputField.tsx` (add/remove até 2, validação em blur, erro inline), usado em `DataEntryForm.tsx` e `OSCorrectionModal.tsx`; exibição em lista em `page.tsx` e `NoteViewerModal.tsx`.

15. **Listagem de OS sempre fresca após mutações (v0.7.1):**
    - `fetchOsList()` em `page.tsx` é o único ponto de refresh da sidebar (usado por cadastro, exclusão, correção e sync). O `fetch("/api/os")` sem anti-cache podia servir a resposta em cache (URL idêntica à da carga inicial), então a nova OS só surgia após F5.
    - Fix: `fetch(`/api/os?t=${Date.now()}`)` — cache-busting por chamada, sem alterar o backend.

---

## 3. Estado de Entrega (v0.7.3 Concluído)

- [x] Documentos em `docs/`: `architectural_analysis.md`, `implementation_plan.md` (Fase 1) e `implementation_plan_fase2_ingestao.md` (Fase 2).
- [x] Seed do cofre com dados reais em `backend/vault/`.
- [x] Motor RAG híbrido (LanceDB + BM25 + LLM plugável OpenRouter/Gemini).
- [x] Endpoint de Ingestão `POST /api/os/ingest` com escrita atômica e sincronização RAG imediata.
- [x] Interface Frontend com abas de navegação (`Consulta & RAG` e `Nova Ordem de Serviço`) e formulário dinâmico mestre-detalhe.
- [x] Provedor LLM plugável (OpenRouter free tier) com fallback em cadeia e síntese local.
- [x] Embeddings locais Sentence-Transformers (`all-MiniLM-L6-v2`) com fallbacks Gemini/hash.
- [x] Filtros RAG com popup em portal: busca por linhas/consórcios reais e opção de vigência.
- [x] Banner de acesso no startup: URLs Local, Rede, Docs e Túnel público (via TUNNEL_ENABLED).
- [x] Exclusão de OS em cascata (`DELETE /api/os/{uid}`) com remoção de eventos, anexos e CSVs, e reindexação RAG automática.
- [x] Feedback via Toast e confirmação nativa na UI de exclusão.
- [x] Hubs de linha com dados reais (435 hubs da OS 174, `schema_version: 2`) com grade horária completa (14 faixas × 4 tipos de dia), desvios e notas de eventos vinculadas.
- [x] Script de rebuild (`rebuild_line_hubs.py`) com `remove_orphans=True`, regeneração dos resumos dos anexos e reindexação RAG; seed atualizado para usar o serviço de hubs.
- [x] **Correção/Edição de OS** (`POST /api/os/{uid}/correct`) com retitulação em cascata (UID, wikilinks, hubs, anexos e CSVs) e correção escalar; validação de título unificada; guard de slug idêntico.
- [x] **Vault corrigido para v0.6.0:** OS 179 → 178 aplicada no cofre real (mestra, nota, hubs, anexos e CSVs consistente; RAG reindexado).
- [x] **Hubs representam a OS mais recente (v0.6.1):** migração event-only preservando grade, `detach_hub_references` na exclusão e remoção de hubs órfãos.
- [x] **Múltiplos processos/despachos por OS (v0.7.0):** listas (máx. 2, ordem preservada), validação Processo.Rio, migração automática de dados legados e componente `MultiInputField` no frontend.
- [x] **Listagem de OS atualizada sem F5 (v0.7.1):** cache-busting no `fetchOsList` (`/api/os?t=${Date.now()}`).
- [x] **Notas de evento com nomes únicos por OS (v0.7.2):** padrão `NOTA-{slug-da-os}-{índice}-{título}` evita colisão entre OS do mesmo mês; renomeação em cascata na correção de OS.
- [x] **Ingestão da OS 179 (v0.7.3):** retificação da OS 178 com 5 notas de evento, ANEXO I (810 serviços) e ANEXO II (529 desvios); 435 hubs sincronizados; nomes das notas corrigidos para o padrão com slug da OS.
- [x] 31 de 31 testes automatizados com pytest (100% de sucesso) e `tsc --noEmit`/`next build` limpos.
- [x] Build de produção do frontend Next.js 15 compilado sem erros.
