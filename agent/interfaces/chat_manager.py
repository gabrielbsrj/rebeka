# agent/shared/communication/chat_manager.py
# VERSION: 3.1.0
# LAST_MODIFIED: 2026-03-01
# CHANGELOG: v3.1 — Fix Antigravity fallback routing + SimpleNamespace scoping bug

import logging
import os
import re
from typing import List, Dict, Any, Optional
from types import SimpleNamespace
from litellm import completion
from core.config_loader import (
    get_active_chat_model, 
    get_agent_name, 
    get_user_name,
    get_model_api_key,
    get_model_api_base
)
from memory.causal_bank import CausalBank

logger = logging.getLogger(__name__)

class ChatManager:
    """
    Chat Manager — A voz da Rebeka.
    Gerencia a interação direta com o usuário via Dashboard ou outros canais.
    """

    def __init__(self, model: str = None):
        self.model = model or get_active_chat_model()
        self.agent_name = get_agent_name()
        self.user_name = get_user_name()
        self.pending_proactive_messages: List[str] = []
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": self._get_base_system_prompt()}
        ]
        self.bank = CausalBank(origin="local")

    def _get_base_system_prompt(self) -> str:
        """Retorna o prompt base da Rebeka."""
        return (
            f"Você é a {self.agent_name}, assistente de IA soberana e autônoma do usuário {self.user_name}.\n"
            "FILOSOFIA: Você não aceita limitações. Se não souber fazer algo ou não tiver a ferramenta, use 'request_antigravity_service' para solicitar uma solução ou ferramenta nova.\n"
            "HABILIDADES: Você pode abrir programas, ler/escrever arquivos, buscar informações no PC e na web, e agora DELEGAR tarefas complexas para o Antigravity.\n"
            "COMPORTAMENTO: Seja proativa. Se o usuário sugerir algo difícil, não diga 'não posso'; diga 'estou buscando uma solução com o Antigravity' e use a ferramenta correspondente.\n"
            "Responda em português. Sempre lembre informações pessoais relevantes usando remember_user_info."
        )

    def _get_user_context_string(self) -> str:
        """Recupera fatos observados sobre o usuário do Causal Bank."""
        try:
            profiles = self.bank.get_observed_profiles()
            if not profiles:
                return ""
            
            context_lines = ["\nCONTEXTO DO USUÁRIO (O QUE VOCÊ SABE SOBRE ELE):"]
            for p in profiles:
                context_lines.append(f"- {p['domain']}: {p['value']}")
            return "\n".join(context_lines)
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto do usuário: {e}")
            return ""

    async def get_response(self, user_message: Optional[str] = None, tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gera uma resposta da Rebeka, potencialmente invocando ferramentas."""
        
        # CASO ESPECIAL: Se for uma chamada de continuidade (user_message=None)
        # e a última mensagem for um resultado de ferramenta de sistema, não chame o LLM.
        if not user_message and self.history:
            last_msg = self.history[-1]
            if last_msg.get("role") == "tool" and last_msg.get("name") == "google_antigravity_login":
                logger.info("Detectada conclusão de login do Google. Retornando confirmação fixa.")
                return {
                    "content": "Autenticação iniciada! Verifique a aba aberta no seu navegador. Assim que concluir, você poderá usar os modelos da Google.",
                    "tool_calls": None,
                    "model": self.model,
                    "agent_name": self.agent_name
                }

        if user_message:
            # Atualizar System Prompt com memórias frescas antes de adicionar mensagem do usuário
            user_context = self._get_user_context_string()
            self.history[0]["content"] = self._get_base_system_prompt() + user_context
            
            self.history.append({"role": "user", "content": user_message})
            
            # ATALHO CRÍTICO: Se o usuário pedir login e o LLM estiver em Rate Limit ou sem acesso
            msg_lower = user_message.lower()
            if "login" in msg_lower and ("google" in msg_lower or "antigravity" in msg_lower):
                logger.info("Comando de login detectado via Regex. Ignorando LLM para evitar Rate Limit.")
                # Simular uma resposta de ferramenta direta usando SimpleNamespace para compatibilidade com server.py
                return {
                    "content": "Entendido! Estou abrindo o seu navegador para realizar a autenticação no Google Antigravity. Por favor, siga as instruções na página que abrirá.",
                    "tool_calls": [
                        SimpleNamespace(
                            id="manual_login_call",
                            type="function",
                            function=SimpleNamespace(
                                name="google_antigravity_login",
                                arguments="{}"
                            )
                        )
                    ]
                }
        
        try:
            # Roteamento dinâmico: Google Antigravity, Ollama ou LiteLLM (Kimi/Gemini/Outros)
            
            api_base = get_model_api_base(self.model)
            api_key = get_model_api_key(self.model)
            full_model_name = self.model
            
            # Ajuste específico para Ollama (Usando modo compatível OpenAI para máxima estabilidade)
            if self.model.startswith("ollama/"):
                full_model_name = self.model.replace("ollama/", "openai/")
                api_key = api_key or "ollama"
                api_base = api_base or "http://localhost:11434/v1"

            if self.model.startswith("google-antigravity/"):
                from core.antigravity_provider import AntigravityProvider
                provider = AntigravityProvider()
                
                # Se não houver credenciais, disparar login automaticamente
                if not provider.creds:
                    logger.warning(f"Credenciais Antigravity ausentes. Disparando login para {self.model}")
                    return {
                        "content": "Você ainda não está autenticado no Google Antigravity. Estou abrindo o navegador para fazer o login...",
                        "tool_calls": [
                            SimpleNamespace(
                                id="auto_login_call",
                                type="function",
                                function=SimpleNamespace(
                                    name="google_antigravity_login",
                                    arguments="{}"
                                )
                            )
                        ]
                    }
                else:
                    response_dict = await provider.completion(
                        model=self.model,
                        messages=self.history,
                        tools=tools
                    )
                    # Converter dict para objeto compatível com o resto do código
                    response = SimpleNamespace(
                        choices=[SimpleNamespace(
                            message=SimpleNamespace(
                                content=response_dict["choices"][0]["message"]["content"],
                                tool_calls=response_dict["choices"][0]["message"].get("tool_calls")
                            ),
                            finish_reason=response_dict["choices"][0]["finish_reason"]
                        )],
                        usage=SimpleNamespace(total_tokens=response_dict["usage"]["total_tokens"])
                    )
            else:
                logger.info(f"Iniciando requisição LiteLLM para {self.model} (API Key presente: {bool(api_key)})")
                
                try:
                    temperature = 1.0 if "kimi" in self.model else 0.7
                    messages = self.history
                    if "kimi" in self.model:
                        for i, msg in enumerate(self.history):
                            if msg.get("role") == "assistant" and "reasoning_content" not in msg:
                                self.history[i] = {**msg, "reasoning_content": ""}
                        messages = self.history
                    
                    response = completion(
                        model=full_model_name,
                        messages=messages,
                        tools=tools,
                        temperature=temperature,
                        api_key=api_key,
                        api_base=api_base,
                    )
                except Exception as api_err:
                    if "kimi" in self.model and "reasoning_content" in str(api_err).lower():
                        fallback_model = "openai/moonshot-v1-8k"
                        fallback_key = get_model_api_key(fallback_model)
                        fallback_base = get_model_api_base(fallback_model)
                        logger.warning(f"Fallback para {fallback_model} devido a erro de reasoning_content.")
                        response = completion(
                            model=fallback_model,
                            messages=messages,
                            tools=tools,
                            temperature=0.7,
                            api_key=fallback_key,
                            api_base=fallback_base,
                        )
                    else:
                        logger.error(f"Falha crítica na chamada ao LiteLLM: {api_err}")
                        return {
                            "content": f"Desculpe, encontrei um erro ao conectar com o provedor de IA ({self.model}). Verifique sua chave de API e conexão. Erro: {str(api_err)}",
                            "tool_calls": None,
                            "model": self.model,
                            "agent_name": self.agent_name
                        }
            
            message = response.choices[0].message
            
            # Construir dicionário limpo — sem thinking, sem reasoning_content
            msg_dict = {
                "role": "assistant",
                "content": message.content or ""
            }
            if "kimi" in self.model and "reasoning_content" not in msg_dict:
                msg_dict["reasoning_content"] = ""
            
            if hasattr(message, "tool_calls") and message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]

            self.history.append(msg_dict)
            
            return {
                "content": message.content,
                "tool_calls": message.tool_calls if hasattr(message, "tool_calls") else None
            }
        except Exception as e:
            logger.error(f"Erro no ChatManager: {str(e)}")
            return {"content": f"Desculpe, tive um erro interno: {str(e)}", "tool_calls": None}

    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        """Adiciona o resultado de uma ferramenta ao histórico seguindo a ordem correta."""
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })

    def push_insight(self, text: str):
        """Adiciona uma mensagem proativa à fila e ao histórico."""
        self.pending_proactive_messages.append(text)
        self.history.append({"role": "assistant", "content": text})
        logger.info(f"Insight proativo enfileirado: {text[:50]}...")

    def switch_model(self, new_model_id: str):
        """Troca o modelo ativo em tempo de execução."""
        old_model = self.model
        self.model = new_model_id
        logger.info(f"Modelo trocado: {old_model} -> {new_model_id}")

    def reset_history(self):
        """Reseta o histórico de conversa, mantendo apenas o system prompt."""
        system_msg = self.history[0] if self.history else None
        self.history.clear()
        if system_msg and system_msg.get("role") == "system":
            self.history.append(system_msg)
        logger.info("Histórico de conversa resetado (system prompt mantido).")

    def poll_insights(self) -> List[str]:
        """Retorna todas as mensagens pendentes e limpa a fila."""
        messages = list(self.pending_proactive_messages)
        self.pending_proactive_messages.clear()
        return messages

