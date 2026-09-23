"""Gerador de respostas em linguagem natural utilizando a API do Google Gemini Flash."""

import time
from typing import List, Optional
from app.core.config import settings
from app.models.rag_schema import RAGSource, ChatMessage, ChatResponse


SYSTEM_PROMPT = """Você é o Assistente Especialista em Ordens de Serviço (OS) e Planejamento da Rede Municipal de Transporte por Ônibus.
Sua missão é responder com precisão, embasamento factual e clareza às consultas sobre alterações operacionais, viagens, itinerários e vigências.

DIRETRIZES DE RESPOSTA:
1. Responda em Português (Brasil), com tom profissional e técnico.
2. Baseie suas respostas ESTRITAMENTE no contexto fornecido do acervo de notas e anexos do cofre Obsidian.
3. SEMPRE cite explicitamente as fontes relevantes utilizando a sintaxe de Wikilinks do Obsidian: [[Nome da Nota]] ou [[OS ...]].
4. Consciência Temporal: Se uma informação for oriunda de uma OS retificada ou substituída, deixe isso explícito na resposta.
5. Dados Operacionais: Ao falar de linhas, mencione o consórcio e o itinerário quando disponíveis no contexto.
6. A seção "Notas de Eventos Vinculadas" de um hub de linha NÃO é a única fonte de desvios/itinerários alternativos. Desvios e itinerários alternativos também constam nos ANEXO II (categoria anexo_operacional), com linhas `| **Código** | Consórcio | Sentido | Evento | ... |`. Priorize os dados das tabelas dos ANEXO II ao responder sobre desvios ou itinerários alternativos.
7. Se o contexto fornecido não contiver dados suficientes para responder com certeza à pergunta, declare educadamente que a informação não foi encontrada no acervo cadastrado.
"""


class RAGGenerator:
    """Gerencia a síntese de respostas combinando os contextos recuperados com o Gemini Flash."""

    def __init__(self):
        self._client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                print(f"Aviso ao inicializar Gemini Client no Generator: {e}")

    def _call_openrouter(self, user_content: str) -> str:
        """Invoca um modelo gratuito via OpenRouter (API compatível com OpenAI).

        Faz retry quando o upstream responde sobrecarga temporária (provider_overloaded),
        que é comum em modelos gratuitos compartilhados.
        """
        import httpx

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        }

        for attempt in range(3):
            resp = httpx.post(url, headers=headers, json=payload, timeout=120.0)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            if data.get("choices"):
                return data["choices"][0]["message"].get("content") or ""

            error = data.get("error") or {}
            error_type = (error.get("metadata") or {}).get("error_type", "")
            if error_type == "provider_overloaded" and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(
                error.get("message") or f"Resposta vazia do OpenRouter ({data.get('id', '')})"
            )

        raise RuntimeError("Resposta vazia do OpenRouter após tentativas de retry")

    def _call_nvidia_nim(self, user_content: str) -> str:
        """Invoca um modelo gratuito via NVIDIA NIM (API compatível com OpenAI)."""
        import httpx

        resp = httpx.post(
            f"{settings.NVIDIA_NIM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.NVIDIA_NIM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.NVIDIA_NIM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("choices"):
            raise RuntimeError("Resposta vazia da NVIDIA NIM")
        return data["choices"][0]["message"]["content"]

    def generate_response(
        self,
        query: str,
        sources: List[RAGSource],
        history: Optional[List[ChatMessage]] = None,
    ) -> ChatResponse:
        """Gera a resposta contextualizada com o tempo de execução e citações."""
        start_time = time.time()

        if not sources:
            return ChatResponse(
                answer="Não foram encontradas notas, ordens de serviço ou desvios correspondentes à sua consulta no acervo.",
                sources=[],
                execution_time_seconds=round(time.time() - start_time, 2),
            )

        # Monta o bloco de contexto enriquecido (limitado)
        context_blocks = []
        for i, s in enumerate(sources[:settings.CONTEXT_MAX_DOCS], 1):
            trecho = s.trecho
            if len(trecho) > settings.CONTEXT_MAX_CHARS:
                trecho = trecho[:settings.CONTEXT_MAX_CHARS] + "..."
            context_blocks.append(f"--- [DOCUMENTO {i}: [[{s.nota_titulo}]] ({s.categoria})] ---\n{trecho}\n")

        context_text = "\n".join(context_blocks)

        user_content = f"""CONTEXTO RECUPERADO DO COFRE:
{context_text}

PERGUNTA DO USUÁRIO:
{query}
"""

        # 1) OpenRouter (free tier) — API compatível com OpenAI
        if settings.LLM_PROVIDER == "openrouter" and settings.OPENROUTER_API_KEY:
            try:
                answer_text = self._call_openrouter(user_content)
            except Exception as e:
                answer_text = (
                    f"Erro na chamada do modelo via OpenRouter ({settings.OPENROUTER_MODEL}): {e}\n\n"
                    "Resumo direto das fontes encontradas:\n"
                    + "\n".join([f"- **[[{s.nota_titulo}]]**: {s.trecho[:180]}..." for s in sources[:3]])
                )
        # 2) NVIDIA NIM (free tier) — API compatível com OpenAI
        elif settings.LLM_PROVIDER == "nvidia_nim" and settings.NVIDIA_NIM_API_KEY:
            try:
                answer_text = self._call_nvidia_nim(user_content)
            except Exception as e:
                answer_text = (
                    f"Erro na chamada do modelo via NVIDIA NIM ({settings.NVIDIA_NIM_MODEL}): {e}\n\n"
                    "Resumo direto das fontes encontradas:\n"
                    + "\n".join([f"- **[[{s.nota_titulo}]]**: {s.trecho[:180]}..." for s in sources[:3]])
                )
        # 3) Google Gemini Flash
        elif self._client:
            try:
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=[user_content],
                    config={"system_instruction": SYSTEM_PROMPT},
                )
                answer_text = response.text or "Sem resposta do modelo."
            except Exception as e:
                answer_text = f"Erro na chamada do modelo Gemini: {e}\n\nResumo direto das fontes encontradas:\n" + "\n".join([f"- **[[{s.nota_titulo}]]**: {s.trecho[:180]}..." for s in sources[:3]])
        else:
            # Modo sintetizador local sem chave de API
            lines_summary = []
            for s in sources[:4]:
                lines_summary.append(f"- **[[{s.nota_titulo}]]** ({s.categoria}):\n  {s.trecho[:240]}...\n")

            answer_text = (
                f"*(Nota: Nenhuma chave de API configurada (LLM_PROVIDER={settings.LLM_PROVIDER}). Exibindo síntese direta das notas recuperadas do Vault)*\n\n"
                f"Encontrei as seguintes referências relevantes para sua consulta:\n\n"
                + "\n".join(lines_summary)
            )

        exec_time = round(time.time() - start_time, 2)
        return ChatResponse(
            answer=answer_text,
            sources=sources,
            execution_time_seconds=exec_time,
        )


rag_generator = RAGGenerator()
