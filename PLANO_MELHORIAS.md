# Plano de Melhorias - Bus OS Vault

Este documento descreve um plano passo a passo para resolver os gargalos identificados no projeto Bus OS Vault. Cada etapa deve ser concluída, testada e commitada individualmente.

## Etapas de Implementação

### Etapa 1: Implementar Indexação Incremental
**Objetivo**: Substituir a reindexação completa por indexação incremental baseada em hash de arquivos para reduzir tempos de startup e sincronização.

**Localização**: 
- `backend/app/services/rag/indexer.py`
- `backend/app/services/rag/vector_store.py`
- `backend/app/services/rag/lexical_search.py`

**Tarefas**:
- [ ] Adicionar tabela SQLite ou arquivo JSON para armazenar metadata dos arquivos (path, hash, timestamp, chunk_ids)
- [ ] Modificar `VaultIndexer.index_entire_vault()` para:
  - Calcular hash SHA-256 de cada arquivo .md
  - Comparar com hash armazenado para detectar alterações
  - Processar apenas arquivos novos/modificados
  - Remover chunks de arquivos excluídos do índice
- [ ] Atualizar métodos de indexação para suportar atualização incremental (upsert em vez de overwrite)
- [ ] Implementar reconciliação na inicialização para detectar mudanças ocorridas enquanto o app estava offline
- [ ] Adicionar logs para monitorar desempenho da indexação incremental

**Critério de Sucesso**: 
- Tempo de startup reduzido em >80% para vaults com >100 arquivos após a primeira indexação
- Nenhuma perda de dados ou chunks órfãos no índice
- Testes automatizados passando

**Commit**: `feat(indexer): implement indexação incremental baseada em hash`

---

### Etapa 2: Paralelizar Processamento de Arquivos
**Objetivo**: Aproveitar múltiplos núcleos de CPU para acelerar o processo de chunking e geração de embeddings durante a indexação.

**Localização**: 
- `backend/app/services/rag/indexer.py`
- Possivelmente `backend/app/services/rag/chunker.py`

**Tarefas**:
- [ ] Substituir loop sequencial por processamento paralelo usando `concurrent.futures.ThreadPoolExecutor` ou `ProcessPoolExecutor`
- [ ] Garantir thread-safety no acesso ao vector store e lexical searcher durante a indexação
- [ ] Testar com diferentes números de workers (baseado em contagem de núcleos disponíveis)
- [ ] Adicionar configuração para controlar grau de paralelismo
- [ ] Tratar exceções em workers individuais sem falhar todo o processo

**Critério de Sucesso**:
- Redução de tempo de indexação proporcional ao número de núcleos disponíveis (ex: 2x mais rápido em CPU de 2 núcleos)
- Nenhuma corrompção de dados ou inconsistência no índice
- Testes de carga passando

**Commit**: `perf(indexer): paralelizar processamento de arquivos durante indexação`

---

### Etapa 3: Otimizar Uso de Memória do BM25
**Objetivo**: Reduzir o consumo de memória do índice BM25 para suportar vaults maiores sem degradação de performance.

**Localização**: 
- `backend/app/services/rag/lexical_search.py`

**Tarefas**:
- [ ] Investigar alternativas ao armazenamento completo do corpus em memória:
  - Opção A: Implementar BM25 baseado em disco (ex: usando whoosh ou similar)
  - Opção B: Arquitetura de blocos/paginação para o corpus
  - Opção C: Compressão inteligente dos tokens armazenados
- [ ] Implementar solução escolhida mantendo a mesma interface pública
- [ ] Benchmark de uso de memória vs performance com datasets de diferentes tamanhos
- [ ] Garantir que scores BM25 permaneçam consistentes com implementação original

**Critério de Sucesso**:
- Uso de memória cresce sublinearmente com o número de documentos (ideal: O(√n) ou melhor)
- Performance de busca não degradada mais que 10-15% comparada à implementação em memória
- Testes de regressão passando

**Commit**: `perf(lexical_search): otimizar uso de memória do índice BM25`

---

### Etapa 4: Ajustar Limites de Contexto do LLM
**Objetivo**: Otimizar os limites de contexto enviados ao LLM para melhor qualidade de resposta sem aumentar custos ou latência excessivamente.

**Localização**: 
- `backend/app/core/config.py`
- `backend/app/services/rag/generator.py`

**Tarefas**:
- [ ] Executar testes com diferentes combinações de:
  - `CONTEXT_MAX_DOCS` (atualmente 6)
  - `CONTEXT_MAX_CHARS` (atualmente 600)
  - `TRECHO_MAX_CHARS` (atualmente 800)
- [ ] Avaliar trade-off entre qualidade de resposta (medida por testes qualitativos) e:
  - Latência de geração
  - Custo de API (se aplicável)
  - Consumo de tokens
- [ ] Implementar estratégia de seleção inteligente de documentos (ex: priorizar por relevância e tipo de conteúdo)
- [ ] Considerar resumo automático de trechos muito longos antes de enviar ao LLM
- [ ] Atualizar documentação com valores recomendados baseado nos testes

**Critério de Sucesso**:
- Melhoria mensurável na qualidade de respostas para consultas complexas (validação via testes qualitativos)
- Aumento de custos/latência mantenido dentro de limites aceitáveis (<20%)
- Configuração pós-ajuste documentada no `.env.example` e README

**Commit**: `tune(rag): otimizar limites de contexto do LLM baseado em testes de qualidade`

---

### Etapa 5: Melhorar Detecção de Categoria
**Objetivo**: Tornar a detecção de categoria de documentos mais robusta e menos acoplada à estrutura de pastas.

**Localização**: 
- `backend/app/services/rag/chunker.py` (linhas 150-163)

**Tarefas**:
- [ ] Substituir detecção baseada em string matching por:
  - Leitura de metadata específica no frontmatter (ex: campo `category`)
  - Fallback para detecção por caminho caso metadata não exista
  - Permitir configuração de mapeamento caminho → categoria
- [ ] Adicionar testes para múltiplos cenários de categorías
- [ ] Garantir compatibilidade retroativa com vaults existentes
- [ ] Documentar nova forma de especificar categoria no frontmatter

**Critério de Sucesso**:
- Funcionamento correto com estrutura de pastas atual (compatibilidade retroativa)
- Possibilidade de sobrescrever categoria via frontmatter
- Nenhuma quebra em funcionalidades existentes de busca ou chunking
- Testes unitários cobrindo novos cenários

**Commit**: `refactor(chunker): melhorar detecção de categoria com suporte a frontmatter`

---

### Etapa 6: Aprimorar Estratégia de Chunking de Tabelas
**Objetivo**: Tornar o chunking de tabelas mais adaptativo ao conteúdo em vez de usar contagem fixa de linhas.

**Localização**: 
- `backend/app/services/rag/chunker.py` (funções `_split_table_rows` e `_chunk_table`)

**Tarefas**:
- [ ] Analisar características das tabelas do ANEXO I e II para entender padrões
- [ ] Implementar estratégia híbrida:
  - Para tabelas simples: manter chunking por linhas fixas
  - Para tabelas com cabeçalhos complexos ou dados esparsos: usar quebra semântica ou por seções lógicas
  - Considerar sobreposição baseada em similaridade de conteúdo em vez de linhas fixas
- [ ] Adicionar métricas para avaliar qualidade do chunking (ex: coesão semântica dentro de chunks)
- [ ] Testar com diferentes tipos de tabelas presentes no vault
- [ ] Tornar parâmetros configuráveis via settings

**Critério de Sucesso**:
- Melhoria na relevância de busca para consultas que envolvem dados tabulares
- Redução de chunks excessivamente grandes ou pequenos para tabelas variadas
- Manutenção ou melhoria de performance de chunking
- Testes específicos para chunking de tabelas passando

**Commit**: `feat(chunker): aprimorar estratégia de chunking de tabelas adaptativa`

---

### Etapa 7: Fortalecer Mecanismo de Túnel Público
**Objetivo**: Melhorar a confiabilidade e experiência do recurso de túnel público para compartilhamento sem firewall.

**Localização**: 
- `backend/app/main.py` (funções de túnel e related)

**Tarefas**:
- [ ] Implementar health checks periódicos para o túnel ativo
- [ ] Adicionar mecanismo de reconexão automática em caso de falha
- [ ] Melhorar logging e notificação de falhas de túnel
- [ ] Adicionar timeout configurável e tentativa de provedores alternativos
- [ ] Considerar suporte a múltiplos túnels simultâneos (fallback em cascata)
- [ ] Atualizar documentação com dicas de solução de problemas
- [ ] Adicionar verificação de dependências durante startup com mensagens claras

**Critério de Sucesso**:
- Túnel permanece ativo por períodos prolongados (>4h) sem intervenção manual
- Recuperação automática de falhas comuns (rede instável, provedor indisponível)
- Mensagens de erro claras e acionáveis para o usuário
- Funcionamento testado com diferentes configurações de rede

**Commit**: `feat(tunnel): melhorar confiabilidade e recuperação automática do túnel público`

---

## Guia de Execução

Para cada etapa:
1. Crie uma branch a partir de `main`: `git checkout -b feature/etapa-X`
2. Implemente as mudanças conforme descrito na etapa
3. Execute testes locais:
   - Backend: `cd backend && pytest tests/ -v`
   - Frontend: `cd frontend && npm test` (se aplicável)
   - Testes manuais de funcionalidade crítica
4. Se tudo passar, faça commit: `git commit -m "<mensagem do commit acima>"`
5. Faça push e abra Pull Request para revisão
6. Após aprovado, faça merge em `main`
7. Repetir para a próxima etapa

## Dependências Observadas

- Etapa 1 (indexação incremental) deve ser concluída antes de Etapa 2 (paralelismo) para garantir correção da base
- Etapa 3 (BM25) pode ser feita em paralelo com Etapa 4 (contexto LLM) pois afetam subsistemas diferentes
- Etapas 5, 6 e 7 são mais independentes e podem ser abordadas em qualquer ordem após as melhorias de performance core
- Recomenda-se validar cada etapa com um vault de teste contendo dados representativos antes de aplicar em produção

## Métricas de Acompanhamento

Para cada etapa, considere medir:
- Tempo de startup/sincronização (antes e depois)
- Uso de memória durante indexação e busca
- Latência de consultas RAG
- Taxa de acerto/cache do sistema
- Feedback qualitativo sobre qualidade de respostas

---
*Plano criado em: $(date)*
*Baseado na análise de gargalos identificada no repositório Bus OS Vault*