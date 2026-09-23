# Plano de Melhoria — Fix de Recuperação RAG (Linha 104)

> Documento de trabalho. Histórico relacionado: [PLANO_MELHORIAS.md](../PLANO_MELHORIAS.md).

## Contexto do Problema

Ao consultar "Quais desvios de itinerário existem para a linha 104?", o RAG respondeu
que nada foi encontrado, apesar de os dados existirem no cofre (`03_Anexos/.../ANEXO_II_Itinerarios.md`
com linhas `| **104** | ... |`).

## Causa Raiz

Não é falha semântica. É um **crash silencioso no chunker** que impede a indexação dos anexos:

1. `index_entire_vault` percorre 452 `.md` e engole exceções por arquivo com `except Exception`
   (apenas imprime e segue).
2. `_chunk_table` entra em **recursão infinita** (RecursionError) em tabelas grandes
   (ANEXO I/II, 39–80 KB) — reproduzido: 506 chamadas aninhadas até estourar `maximum recursion depth`.
3. Resultado: **6 de 452 arquivos não indexados** — exatamente os de `03_Anexos`.
   LanceDB contém 446 arquivos / 2357 chunks e **0 chunks de anexo**.
4. Os desvios/itinerários alternativos da linha 104 residem **somente** nos ANEXO II.
   Sem eles no índice, a busca densa retorna hubs genéricos (807, 217, 232, 350, 107...)
   e o BM25 não possui o token `104`. Daí a resposta "não encontrado".

Fator agravante (ranking): `hybrid_retriever` aplica `HUB_BOOST` a **todos** os hubs quando a
query contém código numérico (`_query_has_line_code`), não apenas ao hub da linha consultada.

## Objetivo

- Indexar os anexos do cofre corretamente (452 arquivos, incluindo `03_Anexos`).
- Garantir que a consulta da linha 104 recupere o ANEXO II correspondente.
- Tornar falhas de indexação visíveis (nunca silenciosas).
- Prevenir regressão com testes.

## Etapas

### Etapa 1 — Reescrever `_chunk_table` de forma iterativa

Arquivo: `backend/app/services/rag/chunker.py`

- Medir o tamanho médio de linha usando **todas** as linhas de dados (não apenas 5).
- Calcular `max_rows = clamp(⌊(max_chars − overhead)/avg⌋, min_rows, max_rows*2)` uma única vez.
- Emitir sub-chunks por grupos de `max_rows` com overlap.
- Linha que exceder `max_chars` é emitida inteira (não há como encolher mais).
- **Sem recursão** — elimina o loop infinito na linha 113.
- Não repetir `pre_table`/`post_table` a cada sub-chunk (causa do inchaço).

### Etapa 2 — Tornar falhas de indexação visíveis

Arquivo: `backend/app/services/rag/indexer.py`

- Coletar arquivos que falham e retorná-los em `index_entire_vault` (campo `falhas: [...]`).
- Se 0 arquivos forem processados com sucesso, levantar exceção.
- Manter mensagens de aviso.

### Etapa 3 — Testes de regressão

Arquivos: `backend/tests/test_chunker.py` (novo) e `backend/tests/test_rag.py` (ajustar/validar)

- Fixture: tabela grande (~150 linhas, contendo `| **104** | ... |`), asserção de
  **ausência de RecursionError**, chunks gerados e token `104` em algum `raw_body`.
- Fixture menor com tabela que exige sub-divisão única (limite respeitado).
- `test_hybrid_retriever_finds_exact_and_semantic` já cobre a query da linha 104
  (rodar após reindexação).

### Etapa 4 — Reindexação e verificação no mundo real

- Executar `index_entire_vault` (ex.: via `POST /api/rag/sync` ou script).
- Confirmar: 452 arquivos, 6 anexos no índice, nenhuma falha.
- Rodar a query "Quais desvios de itinerário existem para a linha 104?" e validar que
  o ANEXO II da 104 é recuperado.

### Etapa 5 (opcional, após validar etapas 1–4) — Boost específico por linha

Arquivo: `backend/app/services/rag/hybrid_retriever.py`

- Só aplicar `HUB_BOOST` ao hub cujo título/código corresponda ao número detectado na query.
- Evitar que hubs de outras linhas sejam inflados igualmente.

## Critérios de Aceite

- `03_Anexos` totalmente indexado (6/6 arquivos).
- `test_chunker.py` passa sem timeout.
- Query da linha 104 retorna fonte com ANEXO II da linha 104.
- Sem alteração de schema de frontmatter (não requer bump de `schema_version`).

## Status

- [x] Etapa 1 — chunker iterativo
- [x] Etapa 2 — indexer visível
- [x] Etapa 3 — testes
- [x] Etapa 4 — reindexação + validação
- [x] Etapa 5 (transformada em obrigatória) — boost específico por linha

## Resultado

- `03_Anexos` totalmente indexado (6/6 arquivos; 452/452 no cofre, 0 falhas).
- `tests/test_chunker.py` (5 testes) e `tests/test_rag.py` (3 testes) passam.
- Query "Quais desvios de itinerário existem para a linha 104?" agora retorna a Linha 104
  e os ANEXO II (174/178/179) com os desvios da 104 no ranking, e o LLM sintetiza resposta
  correta citando os anexos.
- Bônus: corrigida deprecation `table_names()` → `list_tables()` no LanceDBStore.
- `HUB_BOOST` agora é 2.5 e o boost é aplicado apenas aos chunks que tocam a linha consultada
  (por `**Código**` no texto ou código no título), não a todos os hubs.