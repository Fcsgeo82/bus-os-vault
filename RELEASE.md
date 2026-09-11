# 🚀 Bus OS Vault — Release v0.3.0 (`2026-09-11`)

> **Release Minor** focada em estabilizar o pipeline de IA: substituição do provedor LLM (Gemini → OpenRouter free tier), embedding local offline e correção de falhas de runtime que degradavam o motor RAG. Para o usuário final, esta versão entrega filtros inteligentes de busca (linhas, consórcios e vigência) e um chat consideravelmente mais confiável.

---

## ✨ Destaques da Versão (Highlights)

- 🔌 **Provedor LLM plugável** — síntese de conversas via `LLM_PROVIDER` (`openrouter` por padrão ou `gemini`), eliminando as falhas por esgotamento da cota diária do Gemini (HTTP 429).
- 🤖 **Embeddings 100% locais (primário)** — Sentence-Transformers `all-MiniLM-L6-v2` roda offline, sem depender de cota de API; Gemini/hash viram fallback automático.
- 🔍 **Filtros RAG com popup** — filtra por linhas e consórcios reais (carregados do backend) com busca instantânea e opção **Só Vigentes | Todas**.
- 🐛 **Correção de sobreposição de UI** — popups agora renderizam via React Portal acima de qualquer painel (`z-index: 9999`).
- ✅ **10/10 testes automatizados** aprovados e validação manual ponta a ponta (chat direto e via proxy).

---

## 🧠 Núcleo de IA & Pipeline RAG

- **Modelos:**
  - **LLM:** plugável — OpenRouter `nvidia/nemotron-3-super-120b-a12b:free` (padrão) ou Google `gemini-2.5-flash` (via `LLM_PROVIDER`).
  - **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` (local, 384 dims normalizado) → fallback `gemini-embedding-001` → hash.
- **Estratégia de Indexação & Chunking:** mantida (frontmatter enriquecido + Wikilinks); storage vetorial inalterado com **384 dims** — isto significa que **não é necessário reindexar a base** nesta release.
- **Busca & Recuperação (Retrieval):** híbrido LanceDB (vetorial) + BM25 (lexical) com fusão RRF; ganhos indiretos de Recall porque o embedding determinístico local elimina a degradação para hash-fallback causada por 429.
- **Prompt Engineering & Guardrails:** cadeia de fallback em 3 níveis (OpenRouter → Gemini → síntese local das notas) com aviso transparente ao usuário quando a resposta usa síntese sem LLM; citações em Wikilinks (`[[...]]`) preservadas.

---

## 🔌 Conectores & Ingestão de Dados

- Embeddings agrupados em **lote (1 única chamada por request)** — antes eram 1 por chunk, causa direta dos estouros de cota (429).
- Nenhum novo conector/parser adicionado; ingestão via `POST /api/os/ingest` inalterada (CSV ANEXO I/II + sincronização RAG em tempo real).

---

## 📊 Métricas & Performance

| Métrica | Valor |
|---|---|
| Latência de chat (direto, backend) | **~2,8 s** (antes chegava a ~97 s no free tier) |
| Latência de chat (via proxy frontend) | **~8 s** |
| Busca híbrida | 3 resultados relevantes retornados |
| Testes automatizados | **10/10** aprovados |
| Embeddings | Offline/local — custo de tokens = **zero**, risco de 429 eliminado |

---

## 🛠️ Novas Funcionalidades & APIs

- Provedor LLM configurável em runtime (env): `_call_openrouter()` com API compatível com OpenAI.
- Modo embedding local ativado por padrão (sem chave necessária).
- Filtro de busca com **autocomplete/checkbox** para linhas e consórcios (população dinâmica via `GET /api/os/lines/all` — 5 linhas no seed).
- Controle de vigência **Só Vigentes | Todas**.
- Popups de filtro via **React Portal** (`document.body`, `position: fixed`, `z-index: 9999`) com fechamento em outside-click, scroll e resize.

---

## 🐛 Correções de Bugs (Bug Fixes)

- **Chaves não carregadas em runtime:** `.env` agora exige reinício do backend (documentado) — `pydantic-settings` lê o arquivo uma única vez no import; `uvicorn --reload` não observa o `.env`.
- **Modelo de embedding obsoleto (404):** `text-embedding-004` → `gemini-embedding-001`.
- **Modelo de chat descontinuado:** `gemini-2.0-flash` → `gemini-2.5-flash`.
- **Formato errado da resposta SDK:** embeddings lidos de `res.embeddings[0].values` (antes `res.embedding.values`).
- **Esgotamento de cota (429) durante ingestão:** embeddings em lote único + migração para embedding local.
- **Popup de filtros atrás do painel RAG:** stacking context do `backdrop-filter` neutralizava `z-index`; resolvido com portal no `body`.

---

## ⚠️ Breaking Changes & Guia de Migração

- **Variáveis de ambiente novas** (todas com default — nenhuma ação obrigatória):
  - `LLM_PROVIDER` — `openrouter` (padrão) ou `gemini`
  - `OPENROUTER_API_KEY` — chave gratuita em https://openrouter.ai/keys
  - `OPENROUTER_MODEL` — default `nvidia/nemotron-3-super-120b-a12b:free`
- **Reindexação:** ❌ **não necessária** — a dimensão dos vetores (384) e o schema LanceDB foram mantidos.
- **Modelo Gemini atualizado:** se autogravado em `.env`, atualizar `GEMINI_MODEL=gemini-2.5-flash`.
- **Após alterar o `.env`, é obrigatório reiniciar o backend** para que os novos valores sejam lidos.
- **Dependência nova instalada:** `sentence-transformers` (baixa `all-MiniLM-L6-v2` no primeiro uso — ~90 MB em `~/.cache/huggingface`).

---

## 👥 Contribuidores & Agradecimentos

- Felipe Coriolano Siqueira (Tech Lead & AI Engineer) — arquitetura RAG, provedores de IA e pipeline de embeddings.
- Time de Qualidade — suíte pytest e validação ponta a ponta (latência e proxy).
- Comunidade open source — Sentence-Transformers, OpenRouter free tier, LanceDB e rank_bm25.
