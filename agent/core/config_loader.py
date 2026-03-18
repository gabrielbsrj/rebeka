# agent/shared/core/config_loader.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: v2 — Adicionado save_config, get_available_models, get_active_chat_model

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# ─── Catálogo de Modelos Disponíveis ───
AVAILABLE_MODELS = [
    {
        "id": "anthropic/glm-5",
        "name": "GLM-5 (Z.ai)",
        "provider": "zai",
        "description": "Modelo chinês SOTA. 744B parâmetros, raciocínio profundo. Gratuito.",
        "specialty": "Código & Raciocínio",
        "reasoning_power": 90,
        "requires_auth": False,
        "env_key": "ZAI_API_KEY",
        "api_base": "https://api.z.ai/api/anthropic",
    },
    {
        "id": "anthropic/minimax-m25",
        "name": "MiniMax M2.5",
        "provider": "minimax",
        "description": "Excelente para código e tarefas agentes. Gratuito.",
        "specialty": "Código & Deploy",
        "reasoning_power": 85,
        "requires_auth": False,
        "env_key": "MINIMAX_API_KEY",
        "api_base": "https://api.minimax.io/anthropic",
    },
    {
        "id": "gemini/gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "description": "Rápido e gratuito via AI Studio. Ideal para conversas e tarefas diárias.",
        "specialty": "Velocidade",
        "reasoning_power": 65,
        "requires_auth": False,
        "env_key": "GOOGLE_API_KEY",
    },
    {
        "id": "gemini/gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "google",
        "description": "Equilíbrio entre velocidade e qualidade. Ótimo para raciocínio.",
        "specialty": "Balanceado",
        "reasoning_power": 75,
        "requires_auth": False,
        "env_key": "GOOGLE_API_KEY",
    },
    {
        "id": "gemini/gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "provider": "google",
        "description": "Ultra-rápido e econômico. Perfeito para tarefas simples.",
        "specialty": "Ultra-Rápido",
        "reasoning_power": 55,
        "requires_auth": False,
        "env_key": "GOOGLE_API_KEY",
    },
    {
        "id": "openai/kimi-k2.5",
        "name": "Kimi K2.5",
        "provider": "moonshot",
        "description": "Kimi K2.5 da Moonshot AI. Raciocínio agente de última geração.",
        "specialty": "Agente",
        "reasoning_power": 95,
        "requires_auth": False,
        "env_key": "MOONSHOT_API_KEY",
        "api_base": "https://api.moonshot.ai/v1",
    },
    {
        "id": "google-antigravity/claude-opus-4-6-thinking",
        "name": "Claude Opus 4.6",
        "provider": "google-antigravity",
        "description": "O Especialista. Raciocínio superior para código, deploy e infraestrutura.",
        "specialty": "Código & Deploy",
        "reasoning_power": 95,
        "requires_auth": True,
        "auth_type": "google-antigravity-oauth",
    },
    {
        "id": "google-antigravity/gemini-3-flash-preview",
        "name": "Gemini 3 Flash",
        "provider": "google-antigravity",
        "description": "Velocidade extrema do Google. Bom para tarefas rápidas.",
        "specialty": "Ultra-Rápido",
        "reasoning_power": 50,
        "requires_auth": True,
        "auth_type": "google-antigravity-oauth",
    },
    {
        "id": "google-antigravity/gemini-3-pro-preview",
        "name": "Gemini 3 Pro",
        "provider": "google-antigravity",
        "description": "Equilíbrio entre velocidade e qualidade de raciocínio.",
        "specialty": "Balanceado",
        "reasoning_power": 75,
        "requires_auth": True,
        "auth_type": "google-antigravity-oauth",
    },
    {
        "id": "ollama/qwen3.5:9b",
        "name": "Qwen 3.5 9B (Local)",
        "provider": "ollama",
        "description": "Modelo local rodando via Ollama. 9B parâmetros. Privado e rápido.",
        "specialty": "Privacidade & Local",
        "reasoning_power": 88,
        "requires_auth": False,
        "env_key": None,
        "api_base": "http://localhost:11434/v1",
    },
]


def _resolve_config_path() -> Path:
    """Resolve o caminho absoluto do config.yaml."""
    # 1. Tentar relativo ao diretório de execução (raiz do projeto ou agent/)
    config_path = Path("agent/config/config.yaml")
    if not config_path.exists():
        config_path = Path("config/config.yaml")
        
    # 2. Fallback absoluto baseado na localização deste script (agent/core/config_loader.py)
    if not config_path.exists():
        config_path = Path(os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../config/config.yaml")
        ))
    return config_path


def load_config() -> Dict[str, Any]:
    """Carrega as configurações do agente de forma centralizada."""
    load_dotenv()
    config_path = _resolve_config_path()

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(updates: Dict[str, Any]) -> bool:
    """
    Atualiza campos específicos do config.yaml sem sobrescrever o resto.
    Faz um merge profundo (deep merge) das chaves fornecidas.
    """
    config_path = _resolve_config_path()
    if not config_path.exists():
        return False

    config = load_config()

    def _deep_merge(base: dict, overlay: dict):
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                _deep_merge(base[key], value)
            else:
                base[key] = value

    _deep_merge(config, updates)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return True


def get_agent_name() -> str:
    """Retorna o nome personalizado da IA."""
    config = load_config()
    return config.get("agent", {}).get("name", "Rebeka")


def get_user_name() -> str:
    """Retorna o nome do usuário."""
    config = load_config()
    return config.get("agent", {}).get("user_name", "Usuário")


def is_onboarding_completed() -> bool:
    """Verifica se o onboarding já foi realizado."""
    config = load_config()
    return config.get("agent", {}).get("onboarding_completed", False)


def get_active_chat_model() -> str:
    """Retorna o modelo configurado para o chat (ChatManager)."""
    config = load_config()
    return config.get("ai", {}).get("chat", {}).get("model", "anthropic/glm-5")


def set_active_chat_model(model_id: str) -> bool:
    """Atualiza o modelo do chat no config.yaml."""
    return save_config({"ai": {"chat": {"model": model_id}}})


def get_model_api_key(model_id: str) -> Optional[str]:
    """Retorna a chave de API correta para o modelo solicitado."""
    config = load_config()
    api_keys = config.get("agent", {}).get("api_keys", {})
    
    if "glm-5" in model_id or "zai" in model_id:
        return api_keys.get("zai") or os.getenv("ZAI_API_KEY")
    if "minimax" in model_id:
        return api_keys.get("minimax") or os.getenv("MINIMAX_API_KEY")
    if "moonshot" in model_id or "kimi" in model_id:
        return api_keys.get("moonshot") or os.getenv("MOONSHOT_API_KEY")
    if "openai" in model_id:
        return api_keys.get("openai") or os.getenv("OPENAI_API_KEY")
    if "anthropic" in model_id or "claude" in model_id:
        return api_keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY")
    if "google" in model_id or "gemini" in model_id:
        return api_keys.get("google") or os.getenv("GOOGLE_API_KEY")
        
    return None


def get_model_api_base(model_id: str) -> Optional[str]:
    """Retorna o API base correto para o modelo solicitado."""
    config = load_config()
    
    # Encontrar o modelo no catálogo
    for model in AVAILABLE_MODELS:
        if model["id"] == model_id:
            return model.get("api_base")
    
    # Fallbacks baseados no provider
    if "glm-5" in model_id:
        return os.getenv("ZAI_API_BASE", "https://api.z.ai/api/anthropic")
    if "minimax" in model_id:
        return os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/anthropic")
    if "kimi" in model_id:
        return os.getenv("OPENAI_API_BASE", "https://api.moonshot.ai/v1")
    if "gemini" in model_id:
        return os.getenv("GOOGLE_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
    if "ollama" in model_id:
        return os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
    
    return None


def complete_onboarding(agent_name: str, user_name: str, api_keys: Dict[str, str]) -> bool:
    """Finaliza o onboarding salvando nome da IA, do usuário e chaves iniciais."""
    return save_config({
        "agent": {
            "name": agent_name,
            "user_name": user_name,
            "onboarding_completed": True,
            "api_keys": api_keys
        }
    })


def reset_onboarding() -> bool:
    """Reseta o onboarding, limpando API keys e permitindo reconfiguração."""
    return save_config({
        "agent": {
            "onboarding_completed": False,
            "api_keys": {
                "moonshot": "",
                "openai": "",
                "anthropic": "",
                "google": ""
            }
        }
    })


def get_available_models() -> List[Dict[str, Any]]:
    """Retorna a lista de modelos disponíveis para o usuário."""
    active = get_active_chat_model()
    result = []
    for m in AVAILABLE_MODELS:
        entry = dict(m)
        entry["active"] = (m["id"] == active)
        result.append(entry)
    return result


def get_model_config(module_name: str) -> Dict[str, Any]:
    config = load_config()
    ai_config = config.get("ai", {})

    module_map = {
        "planner": "planner",
        "evaluator": "evaluator",
        "causal_validator": "causal_validator",
        "observer": "planner",
        "developer": "planner",
        "security_analyzer": "evaluator",
    }

    key = module_map.get(module_name)
    if not key:
        return {"model": "gpt-4-turbo-preview", "temperature": 0.7}

    conf = ai_config.get(key, {})
    model_name = conf.get('model', 'kimi-k2.5')
    
    # Para Moonshot/Kimi, usar formato OpenAI-compatible (padrão LiteLLM)
    if 'kimi' in model_name:
        return {
            "model": f"openai/{model_name}",
            "temperature": conf.get("temperature", 1.0),
            "max_tokens": conf.get("max_tokens", 4000),
            "api_base": "https://api.moonshot.ai/v1",
            "api_key": get_model_api_key("kimi")
        }
    elif 'claude' in model_name:
        return {
            "model": f"anthropic/{model_name}",
            "temperature": conf.get("temperature", 1.0),
            "max_tokens": conf.get("max_tokens", 4000),
            "api_key": get_model_api_key(model_name)
        }
    elif 'gemini' in model_name or 'vertex_ai' in model_name:
        return {
            "model": model_name,  # Use as-is (e.g., vertex_ai/gemini-1.5-pro)
            "temperature": conf.get("temperature", 1.0),
            "max_tokens": conf.get("max_tokens", 4000),
            "api_base": "https://aiplatform.googleapis.com/v1",
            "api_key": get_model_api_key(model_name)
        }
    elif model_name.startswith('ollama/'):
        actual_model = model_name.replace('ollama/', '')
        return {
            "model": f"openai/{actual_model}",
            "temperature": conf.get("temperature", 0.7),
            "max_tokens": conf.get("max_tokens", 4000),
            "api_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1"),
            "api_key": "ollama" # Ollama não exige chave real no modo compatível
        }
    else:
        provider_prefix = "openai/"
        return {
            "model": f"{provider_prefix}{model_name}",
            "temperature": conf.get("temperature", 1.0),
            "max_tokens": conf.get("max_tokens", 4000),
            "api_key": get_model_api_key(model_name)
        }
