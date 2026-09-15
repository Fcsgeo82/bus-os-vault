# Contexto do Projeto — Bus OS Vault

> Documento vivo que registra decisões de design, requisitos levantados e contexto de domínio.
> Atualizado a cada fase de refinamento.

---

## 1. Domínio do Problema

### O que é uma Ordem de Serviço (OS)?

O sistema gerencia as **Ordens de Serviço (OS)** da rede municipal de transporte coletivo por ônibus. Cada OS formaliza alterações operacionais planejadas ou emergenciais para as linhas da cidade.

- **Frequência média:** ~2 OS por mês (com possíveis retificações).
- **Natureza dos Dados:** Mestre-Detalhe. Uma OS é a entidade agregadora que contém metadados formais, anexos operacionais completos (CSV) e múltiplas **Notas de Eventos** que descrevem cada modificação pontual.

### Usuários

- Volume máximo estimado: **5 usuários simultâneos** (ocasião rara).
- Perfil: Gestores, técnicos de planejamento e analistas de transporte público.
- Uso principal: Consulta semântica de histórico operacional, pesquisa por linha/desvio/viagem e cadastramento normatizado.

---

## 2. Decisões de Arquitetura

| Decisão | Escolha | Justificativa |
|---|---|---|
| **Arquitetura** | Web Fullstack (Next.js 15 + FastAPI) | Desacoplamento entre UI moderna e ecossistema maduro de IA/RAG em Python |
| **LLM** | Plugável: `LLM_PROVIDER=openrouter` (padrão) ou `gemini` | Free tier do OpenRouter mais confiável que a cota diária do Gemini (429); fallback em cadeia até síntese local |
| **Embeddings** | `sentence-transformers` `all-MiniLM-L6-v2` (local) como primário; Gemini `gemini-embedding-001` e hash como fallbacks | Dense search de alta relevância com custo zero e sem cota de API |
| **Vector Store** | LanceDB (embedded) | Sem dependência de serviços externos, persistência baseada em arquivos |
| **Busca Léxica** | rank_bm25 | Complementar para termos exatos (códigos de linha, números de despacho/processo) |
| **Deploy** | Railway (free tier) | Suporte robusto para containers Docker e automação de deploy |
| **Formato de Anexos** | CSV (.csv) | Formato padrão dos dados de viagens (ANEXO I) e itinerários (ANEXO II) |
| **Idioma da UI** | Português (Brasil) | Aplicação focada na operação de transporte municipal brasileira |
| **Storage do Vault** | Diretório estruturado em Markdown | 100% legível pelo Obsidian e interoperável com Git/FS |

---

## 3. Requisitos Funcionais

### RF-01: Painel RAG & Consulta Inteligente (Prioridade MVP)
- [ ] Chat conversacional para perguntas sobre o histórico de OS e linhas de ônibus.
- [ ] Busca híbrida (Vetorial LanceDB + Léxica BM25) com re-ranking ou Reciprocal Rank Fusion (RRF).
- [ ] Consciência temporal de vigência: discernir se uma OS foi retificada/substituída ou permanece em vigor.
- [ ] Citação explícita das fontes: link para a OS, notas de eventos e seções dos anexos consultados.
- [ ] Filtros rápidos na UI: por Código de Linha, Consórcio, Ano/Mês, Tipo de Evento e Status de Vigência.

### RF-02: Formulário de Entrada (Mestre-Detalhe)
- [ ] **Cabeçalho da OS:** Ano/Mês, Tipo (Normal, Retificada, Temporária), Processo.Rio, Despacho, Datas (Publicação, Início e Fim de Vigência), GTFS.
- [ ] **Relação de Retificação:** Indicação de OS anterior caso trate-se de retificação (`retifica_os`).
- [ ] **Lista Dinâmica de Notas de Evento:** Adição de 1 a N notas por OS:
  - Tipo de Evento: `Inclusão`, `Remoção`, `Ajuste`, `Correção/Retificação`.
  - Objeto Afetado: `Linhas/Serviços`, `Itinerários`, `Planejamento de Viagens`, `Quilometragem`, `Texto/GTFS`.
  - Linhas Afetadas (tags/códigos múltiplos, ex: `LECD131`, `006`).
  - Consórcios (`Intersul`, `Internorte`, `Transcarioca`, `Santa Cruz`).
  - Descrição detalhada e Justificativa operacional.
- [ ] **Upload e Processamento de Anexos:**
  - ANEXO I (Planejamento de Viagens): Validação das 117 colunas, sumarização por serviço e geração de Markdown estruturado.
  - ANEXO II (Itinerários Alternativos): Validação de desvios operacionais e conversão para tabela Markdown.

### RF-03: Visualização e Gestão do Acervo
- [x] Listagem consolidada de OS com status de vigência em tempo real.
- [x] Exclusão de OS em cascata (OS mestra + notas de eventos vinculadas + anexos + CSVs) com reindexação RAG automática e confirmação na UI.
- [ ] Linha do tempo / histórico de retificações de uma OS.
- [x] Fichas por linha/serviço agregando todas as menções ao longo das OS — **Hubs de Linha com dados reais** (grade horária, desvios e eventos vinculados, schema v2).

---

## 4. Modelagem de Dados e Estrutura no Obsidian Vault

A organização do cofre reflete uma arquitetura de grafos por meio de Wikilinks bidirecionais (`[[...]]`):

```
vault/
├── 00_Ordens_de_Servico/        # Fichas agregadoras de cada OS
│   └── OS 2026.01 - Janeiro 2º Estudo [retificado].md
├── 01_Notas_de_Eventos/         # Notas granulares de cada alteração (vindas do formulário)
│   ├── NOTA-2026.01-01-INC-LECD131.md
│   ├── NOTA-2026.01-02-REM-Linha-443.md
│   └── NOTA-2026.01-03-AJU-LECD128.md
├── 02_Linhas_e_Servicos/        # Hubs operacionais por Linha (dados reais, schema v2)
│   ├── Linha 006.md
│   └── Linha LECD128.md
└── 03_Anexos/                   # Anexos operacionais convertidos em Markdown sumarizado
    └── OS_2026.01_Estudo2_ret/
        ├── ANEXO_I_Viagens_Resumo.md
        └── ANEXO_II_Itinerarios.md
```

### 4.1 Schema da OS Mestra (`00_Ordens_de_Servico/`)

```yaml
---
uid: "os-2026-01-estudo-2-ret"
title: "105 - OS 2026.01 - Janeiro 2º Estudo [retificado]"
tipo_os: "Retificada"              # Normal | Retificada | Temporaria
status_vigencia: "Vigente"         # Vigente | Revogada | Substituida | Sem Vigencia
ano_mes_referencia: "2026/1"
processo_rio: "000399.000416/2026-49"
despacho: "947965"
data_publicacao: 2026-01-16
inicio_vigencia: 2026-01-19
fim_vigencia: null                 # null = Sem Vigência final definida
arquivo_gtfs: "095_gtfs_jan-26_2E-ret.zip"

# Relações de Linhagem e Retificação (P4)
retifica_os: "[[102 - OS 2026.01 - Janeiro 1º Estudo [retificado]]]"
substitui_os: null
retificada_por: null

tags: [os/retificada, ano/2026, mes/01, status/vigente]
created: 2026-09-10
schema_version: 1
---

# 105 - OS 2026.01 - Janeiro 2º Estudo [retificado]

## Resumo das Alterações (Notas de Evento)
- [[NOTA-2026.01-01-INC-LECD131]]: Inclusão do planejamento de viagens das linhas LECD131 e LECD132.
- [[NOTA-2026.01-02-REM-Linha-443]]: Retirada do planejamento operacional da linha 443.
- [[NOTA-2026.01-03-AJU-LECD128]]: Ajuste de viagens e itinerário na LECD128.

## Anexos Operacionais
- [[ANEXO_I_Viagens_Resumo]]: Grade horária de viagens e quilometragens.
- [[ANEXO_II_Itinerarios]]: Desvios e itinerários alternativos aprovados.
```

### 4.2 Schema da Nota de Evento (`01_Notas_de_Eventos/`)

```yaml
---
uid: "evt-2026-01-001"
title: "Inclusão de viagens das linhas LECD131 e LECD132"
type: nota_evento
os_origem: "[[105 - OS 2026.01 - Janeiro 2º Estudo [retificado]]]"
tipo_evento: "Inclusão"            # Inclusão | Remoção | Ajuste | Correção/Retificação
objeto_afetado: ["Linhas/Serviços", "Planejamento de Viagens"]
linhas_afetadas: ["LECD131", "LECD132"]
consorcios: ["Internorte"]
vigencia_inicio: 2026-01-19
vigencia_fim: null
tags: [evento/inclusao, linha/lecd131, linha/lecd132, consorcio/internorte]
created: 2026-09-10
schema_version: 1
---

# Inclusão de viagens das linhas LECD131 e LECD132

**OS:** [[105 - OS 2026.01 - Janeiro 2º Estudo [retificado]]]  
**Início da Vigência:** 19/01/2026  
**Linhas:** [[Linha LECD131]], [[Linha LECD132]]  

## Descrição
Inclusão do planejamento de viagens das linhas experimentais LECD131 e LECD132.

## Justificativa Operacional
Atendimento a demanda identificada pelo estudo de transporte na região norte.
```

### 4.3 Schema do Hub de Linha (`02_Linhas_e_Servicos/`)

> **Importante:** hubs de linha usam `schema_version: 2` (dados reais). A v1 era MOC/placeholder e não é mais gravada.

```yaml
---
uid: "hub-linha-006"
codigo_linha: "006"
vista: "Silvestre - Castelo"
consorcio: "Intersul"
type: linha_servico
os_origem: "174 - OS 2026.08 - Agosto 2º Estudo [ret4]"
vigencia_inicio: 2026-08-16
data_atualizacao: 2026-09-15
tags: [linha/006, consorcio/intersul, tipo/municipal]
schema_version: 2
---

# Linha 006

## Planejamento Operacional de Viagens

### Ida (Silvestre → Castelo)
[resumo de partidas/km por tipo de dia + tabela "Distribuição Horária" de 9 colunas × 14 faixas]

## Itinerários Alternativos e Desvios
[desvios do ANEXO II agrupados por evento/ativação]

## Ordens de Serviço Relacionadas
- [[174 - OS 2026.08 - Agosto 2º Estudo [ret4]]]

## Notas de Eventos Vinculadas
- [[NOTA-2026.08-01-AJU-Intersul]]: ...
```

- **Geração:** `line_hub_service.sync_hubs_for_os()` integrado ao fluxo de ingestão (`POST /api/os/ingest`).
- **Regeneração:** `rebuild_line_hubs.py` reconstrói hubs e resumos de anexos a partir dos CSVs de `referências/`, com remoção de hubs órfãos (`remove_orphans=True`) — ingestões rotineiras **não** removem hubs.
- **Linhas citadas só em eventos** criam hub mínimo apenas se ainda não existirem (sem sobrescrever dados reais).

---

## 5. Especificação dos Anexos Operacionais

### 5.1 ANEXO I — Planejamento de Viagens (`.csv`)
* **Volume típico:** ~800+ linhas por estudo.
* **Colunas de Cabeçalho (117 colunas totais):**
  1. `Serviço` (ex: `006`, `104`, `LECD128`)
  2. `Vista` (ex: `Silvestre - Castelo`)
  3. `Consórcio` (`Intersul`, `Internorte`, `Transcarioca`, `Santa Cruz`)
  4. `Sentido` (`Ida`, `Volta`, `Circular`)
  5. `Extensão` (em km com 3 casas decimais, ex: `8.460`)
  6. **Matriz de Viagens & Quilometragem (112 colunas):**
     - Desdobrada em 4 tipos de dia: `Dia Útil`, `Sábado`, `Domingo` e `Ponto Facultativo`.
     - 14 faixas horárias por tipo de dia (00h-01h até 23h-24h).
     - 2 métricas por faixa: `Partidas` e `Quilometragem`.
* **Estratégia de Ingestão para RAG:**
  - Preservar o CSV íntegro no backend.
  - Gerar arquivo Markdown sumarizado (`ANEXO_I_Viagens_Resumo.md`) por serviço, apresentando: totais de partidas por período do dia (Manhã, Tarde, Noite, Madrugada), quilometragem total por tipo de dia (incluindo Ponto Facultativo) e a coluna "Viagens Pt. Fac.".
  - O parser expõe também o dict `hourly` (14 faixas × 4 tipos de dia) e campos `partidas_ponto_facultativo`/`km_ponto_facultativo`, usados pelos Hubs de Linha (grade horária completa).

### 5.2 ANEXO II — Itinerários Alternativos (`.csv`)
* **Volume típico:** ~400 a 500 desvios operacionais.
* **Colunas (8 colunas):**
  1. `Serviço` (ex: `006`, `100`, `117`)
  2. `Vista` (ex: `Silvestre - Castelo`)
  3. `Consórcio` (`Intersul`, `Internorte`, etc.)
  4. `Sentido` (`Ida`, `Volta`)
  5. `Extensão` (em km do desvio)
  6. `Evento` (tag do desvio, ex: `[desvio_feira]`, `[desvio_tunel]`, `[desvio_maracana]`, `[reversivel]`, `[excepcionalidade]`)
  7. `Descrição` (detalhe textual do desvio, ex: `Feira Livre da Rua Carlos Sampaio`, `Fechamento do túnel Santa Bárbara`)
  8. `Ativação` (`Automática`, `Manual, mediante provocação do operador`)
* **Estratégia de Ingestão:** Conversão direta para tabelas Markdown agrupadas por Linha/Serviço.

---

## 6. Rastreabilidade e Perguntas de Refinamento

| Pergunta | Status | Definição Consolidada |
|---|---|---|
| **P1 — Estrutura de Viagens** | ✅ Resolvido | Mapeadas as 117 colunas do ANEXO I (5 de cadastro + 112 da matriz operacional). |
| **P2 — Estrutura de Itinerários** | ✅ Resolvido | Mapeadas as 8 colunas do ANEXO II (Serviço, Vista, Consórcio, Sentido, Extensão, Evento, Descrição, Ativação). |
| **P3 — Campos da OS** | ✅ Resolvido | Levantados diretamente do controle real: Ano/Mês, Tipo, Processo.Rio, Despacho, Publicação, Início e Fim de Vigência, GTFS. |
| **P4 — Relacionamento e Retificação** | ✅ Resolvido | Suporte a encadeamento de retificação (`retifica_os`, `retificada_por`) e status de vigência ativo/revogado. |
| **P5 — Armazenamento dos CSVs** | ✅ Resolvido | CSVs originais serão mantidos íntegros no storage/anexos, e o sistema gerará Markdowns sumarizados otimizados para RAG. |

---

## 7. Cronologia de Decisões

| Data | Decisão |
|---|---|
| 2026-09-10 | Análise arquitetural concluída. Opção A (Web Fullstack) selecionada. |
| 2026-09-10 | Definido: Gemini Flash (LLM), Railway (deploy), CSV (import), PT-BR (UI). |
| 2026-09-10 | Projeto inicializado: `bus-os-vault`. Documentação base criada. |
| 2026-09-10 | Análise dos arquivos reais em `referências/` (Controle OS, ANEXO I e ANEXO II). |
| 2026-09-10 | Aprovada arquitetura Mestre-Detalhe (OS + Notas de Eventos com tipos: Inclusão, Remoção, Ajuste, Retificação). |
| 2026-09-10 | Especificada rastreabilidade de retificação entre OS (P4) e colunas exatas dos anexos (P1, P2). |
| 2026-09-11 | Provedor LLM movido para OpenRouter (free tier) após esgotamento da cota Gemini; Gemini mantido como alternativa via `LLM_PROVIDER`. |
| 2026-09-11 | Embeddings locais (Sentence-Transformers `all-MiniLM-L6-v2`) como primário; Gemini `gemini-embedding-001` e hash como fallbacks. |
| 2026-09-11 | Filtros RAG com popup em portal: busca por linhas/consórcios reais e opção de vigência. |
| 2026-09-11 | Banner de acesso no startup (URLs Local/Rede/Docs). Compartilhamento externo via túnel (`TUNNEL_ENABLED`) após constatar bloqueio do firewall sem admin. |
| 2026-09-15 | Exclusão de OS em cascata (`DELETE /api/os/{uid}`) com botão na UI, confirmação nativa e Toast de feedback; reindexação RAG automática após remoção. |
| 2026-09-15 | Testes do fluxo de exclusão adicionados; suíte ampliada para 11/11 aprovados. |
| 2026-09-15 | **Hubs de Linha com dados reais (schema v2):** `line_hub_service` integrado ao ingest; grade horária completa (14 faixas × 4 tipos de dia), desvios e eventos vinculados. 435 hubs gerados para a OS 174. |
| 2026-09-15 | Parser ANEXO I expõe Ponto Facultativo e dict `hourly`; resumo do anexo com coluna "Viagens Pt. Fac.". Remoção de hubs órfãos somente no rebuild (`remove_orphans=True`), nunca em ingestões rotineiras. Hub órfão `Linha LECD999.md` excluído. Suíte ampliada para 16/16 testes. |
| 2026-09-15 | Interface: card "Hubs de Linhas" passa a consumir o catálogo real (`GET /api/os/lines/all`) no lugar da lista MOC fixa. `APP_VERSION` promovida para `0.5.0`. |
