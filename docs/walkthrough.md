# Walkthrough — Implementação do MVP: Bus OS Vault

Concluímos a implementação de ponta a ponta do MVP do **Bus OS Vault**, priorizando o motor RAG híbrido, o processamento dos anexos reais do Obsidian Vault e a interface conversacional desacoplada.

---

## 1. O Que Foi Construído

### A. Documentação e Planejamento
- [x] Salvo o plano em [docs/implementation_plan.md](file:///c:/github_repositories/bus-os-vault/docs/implementation_plan.md).
- [x] Sincronizados [CONTEXT.md](file:///c:/github_repositories/bus-os-vault/CONTEXT.md), [CHANGELOG.md](file:///c:/github_repositories/bus-os-vault/CHANGELOG.md), [AGENTS.md](file:///c:/github_repositories/bus-os-vault/AGENTS.md) e [memory.md](file:///c:/github_repositories/bus-os-vault/memory.md).

---

### B. Ingestão e Processamento dos Dados Reais
- **ANEXO I (Grade de Viagens):** Processadas as **117 colunas** do CSV real com 817 registros de linhas. O `CSVAttachmentParser` calculou as partidas agregadas por período (manhã, entrepico, noite) e gerou o documento sintetizado `ANEXO_I_Viagens_Resumo.md`.
- **ANEXO II (Itinerários Alternativos):** Processados **475 desvios operacionais** com identificação de eventos (`[desvio_feira]`, `[desvio_tunel]`, `[reversivel]`, etc.) e gerado o documento `ANEXO_II_Itinerarios.md`.
- **Estrutura de Pastas do Vault:** Geradas em [backend/vault/](file:///c:/github_repositories/bus-os-vault/backend/vault):
  - `00_Ordens_de_Servico/`: Ficha mestra da OS com metadados de processo, despacho e vigência.
  - `01_Notas_de_Eventos/`: Notas granulares de alterações operacionais com tags e links bidirecionais.
  - `02_Linhas_e_Servicos/`: Hubs (MOC) para as linhas chave (`006`, `104`, `117`, `169`).
  - `03_Anexos/`: Tabelas e sumários dos anexos.

---

### C. Motor RAG Híbrido (LanceDB + BM25 + Gemini Flash)
- **Chunker Hierárquico:** Divide seções respeitando títulos `# / ##` e injeta metadados de Frontmatter (título, vigência, linhas e consórcios afetados) no início de cada chunk.
- **LanceDB Vector Store:** Tabela vetorial embedded criada sob `backend/data/lancedb` com 31 vetores indexados.
- **BM25 Lexical Search:** Indexador de termos exatos em memória (`rank_bm25`).
- **Reciprocal Rank Fusion (RRF):** Algoritmo com `k=60` combinando os rankings denso e léxico com filtros temporais de vigência.
- **Gerador Contextual:** Integração com o Google Gemini Flash, gerando respostas que citam as fontes no padrão de Wikilinks do Obsidian (`[[Nome da Nota]]`).

---

### D. Endpoints REST da API FastAPI
- `POST /api/rag/chat`: Envio de perguntas e histórico de conversa com retorno de resposta e fontes consultadas.
- `POST /api/rag/search`: Busca direta por trechos no cofre sem chamada ao LLM.
- `POST /api/rag/sync`: Reindexação instantânea do cofre sob demanda.
- `GET /api/os`: Listagem das Ordens de Serviço cadastradas.
- `GET /api/os/{uid}`: Ficha completa da OS com notas vinculadas.
- `GET /api/os/notes/{uid}`: Inspeção do conteúdo Markdown e do Frontmatter YAML de qualquer nota.
- `DELETE /api/os/{uid}`: Exclusão em cascata da OS (mestra + notas de eventos + anexos + CSVs) com reindexação RAG automática.

---

### E. Frontend Moderno (Next.js 15 + React 19)
- **Aesthetics & Design System:** Desenvolvido em Vanilla CSS com dark mode elegante, tokens HSL, cards em glassmorphism e tipografia Google Fonts (*Plus Jakarta Sans*).
- **Chat Conversacional:** Input com envio por `Enter`, balões distintos, estado de loading animado e botões de perguntas sugeridas.
- **Cartões de Fontes:** Exibem o score de relevância da citação, a categoria da nota e botão de inspeção direta.
- **Drawer de Notas:** Modal deslizante lateral que renderiza a nota Markdown e a tabela do Frontmatter YAML sem sair da tela.
- **Filtros Rápidos:** Toggles dinâmicos de *Apenas Vigentes*, seleção de linhas (`006`, `104`, `117`, `169`, `LECD131`) e consórcios.

---

## 2. Validação e Testes Realizados

### A. Testes Automatizados no Backend (pytest)
Executada a suíte de testes com **100% de aprovação (9 de 9 testes aprovados)**:

```bash
backend/tests/test_api.py::test_health_endpoint PASSED
backend/tests/test_api.py::test_list_os_endpoint PASSED
backend/tests/test_api.py::test_rag_search_endpoint PASSED
backend/tests/test_api.py::test_rag_chat_endpoint PASSED
backend/tests/test_csv_parser.py::test_parse_br_float PASSED
backend/tests/test_csv_parser.py::test_process_anexos_reais PASSED
backend/tests/test_rag.py::test_chunker_enriches_frontmatter PASSED
backend/tests/test_rag.py::test_hybrid_retriever_finds_exact_and_semantic PASSED
backend/tests/test_rag.py::test_rag_generator_synthesizes_response PASSED

======================== 9 passed in 3.32s ========================
```

### B. Build de Produção do Frontend (Next.js)
```bash
✓ Compiled successfully in 5.6s
✓ Generating static pages (4/4)
✓ Collecting build traces
```
Nenhum erro de tipo ou falha de build detectada.

---

## 3. Como Executar Localmente

### 1. Iniciar o Backend (FastAPI):
```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
*Swagger UI disponível em: `http://localhost:8000/docs`*

### 2. Iniciar o Frontend (Next.js):
```bash
cd frontend
npm run dev
```
*Aplicação web acessível em: `http://localhost:3000`*

### 3. Execução via Docker Compose (Opcional):
```bash
docker-compose up --build
```
