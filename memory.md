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

---

## 3. Estado de Entrega (v0.5.0 Concluído)

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
- [x] 16 de 16 testes automatizados com pytest (100% de sucesso) e `tsc --noEmit` limpo.
- [x] Build de produção do frontend Next.js 15 compilado sem erros.
