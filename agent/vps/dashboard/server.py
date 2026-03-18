# agent/vps/dashboard/server.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: v2 — Rotas de configuração + seleção dinâmica de modelo

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict
import os
from interfaces.chat_manager import ChatManager
from core.tool_registry import registry
from core.config_loader import (
    get_available_models,
    get_active_chat_model,
    set_active_chat_model,
    get_agent_name,
    get_user_name,
    is_onboarding_completed,
    complete_onboarding
)

try:
    from local.executor_local import LocalExecutor
except ImportError:
    LocalExecutor = None

logger = logging.getLogger(__name__)

app = FastAPI(title="Rebeka Dashboard Backend")
chat_manager = ChatManager() # Deixa carregar o modelo do config
executor = LocalExecutor() if LocalExecutor else None

# Montar diretório de estáticos para servir o feed do browser
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ChatRequest(BaseModel):
    message: str

class ModelSelectRequest(BaseModel):
    model_id: str

class OnboardingRequest(BaseModel):
    agent_name: str
    user_name: str
    api_keys: Dict[str, str]

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Recebida mensagem do usuário: {request.message}")
        
        # 1. Primeira chamada: LLM decide se usa ferramenta
        tools = registry.get_tool_definitions()
        
        try:
            response_data = await chat_manager.get_response(request.message, tools=tools)
        except Exception as e:
            # Se o histórico estiver corrompido, resetar e tentar novamente
            logger.warning(f"Histórico corrompido detectado: {e}. Resetando conversa...")
            chat_manager.reset_history()
            return {
                "content": "Meu histórico de conversa foi resetado devido a um erro. Por favor, repita sua pergunta.",
                "action_log": "RESET: histórico corrompido"
            }
        
        # 2. Loop de Execução de Ferramentas
        iterations = 0
        max_iterations = 15  # Aumentado para tarefas complexas com muitas leituras de arquivo
        action_logs = []

        while response_data.get("tool_calls") and iterations < max_iterations:
            iterations += 1
            
            for tool_call in response_data["tool_calls"]:
                tool_name = tool_call.function.name
                import json
                
                try:
                    args = json.loads(tool_call.function.arguments)
                    logger.info(f"Executando {tool_name} pela Rebeka... (iteração {iterations})")
                    
                    # Execução REAL via LocalExecutor se disponível
                    if executor:
                        result = await executor.execute(tool_name, args)
                    else:
                        result = {"status": "error", "message": "Execução de ferramentas não suportada neste ambiente VPS."}
                    chat_manager.add_tool_result(tool_call.id, tool_name, json.dumps(result))
                    action_logs.append(f"EXEC: {tool_name}")
                except Exception as e:
                    error_result = {"status": "error", "message": str(e)}
                    chat_manager.add_tool_result(tool_call.id, tool_name, json.dumps(error_result))
                    action_logs.append(f"ERRO: {tool_name}")
                    logger.error(f"Erro ao executar {tool_name}: {e}")

            # Pedir para o LLM continuar baseado nos resultados obtidos
            try:
                response_data = await chat_manager.get_response(user_message=None, tools=tools)
            except Exception as e:
                logger.error(f"Erro ao continuar loop de ferramentas: {e}")
                break

        # CRÍTICO: Se o loop saiu por max_iterations e ainda há tool_calls pendentes,
        # precisamos adicionar respostas de erro para não corromper o histórico.
        if response_data.get("tool_calls"):
            import json
            for tc in response_data["tool_calls"]:
                error_msg = {"status": "error", "message": "Limite de iterações atingido. Tarefa interrompida."}
                chat_manager.add_tool_result(tc.id, tc.function.name, json.dumps(error_msg))
                action_logs.append(f"LIMITE: {tc.function.name}")
            logger.warning(f"Loop atingiu max_iterations ({max_iterations}). {len(response_data['tool_calls'])} tool_calls pendentes foram encerradas.")

        return {
            "content": response_data.get("content") or "Processamento concluído.",
            "action_log": " | ".join(action_logs) if action_logs else None
        }

    except Exception as fatal_err:
        import traceback
        logger.error(f"ERRO FATAL NO ENDPOINT DE CHAT: {fatal_err}")
        logger.error(traceback.format_exc())
        return {
            "content": f"Ocorreu um erro interno crítico ao processar sua mensagem: {str(fatal_err)}",
            "action_log": "ERRO FATAL"
        }

@app.get("/api/chat/updates")
async def chat_updates_endpoint():
    """Retorna mensagens proativas pendentes do ChatManager."""
    new_messages = chat_manager.poll_insights()
    return {"messages": new_messages}

@app.post("/api/onboarding/setup")
async def onboarding_setup(request: OnboardingRequest):
    """Finaliza o setup inicial do usuário."""
    ok = complete_onboarding(request.agent_name, request.user_name, request.api_keys)
    if ok:
        chat_manager.agent_name = request.agent_name
        chat_manager.user_name = request.user_name
        chat_manager.reset_history()
        logger.info(f"Onboarding concluído. Agent Name: {request.agent_name}, User Name: {request.user_name}")
        return {"success": True}
    return {"success": False, "error": "Failed to save onboarding config"}

@app.post("/api/onboarding/reset")
async def onboarding_reset():
    """Reseta o onboarding e limpa as API keys, permitindo reconfiguração."""
    from core.config_loader import reset_onboarding
    ok = reset_onboarding()
    if ok:
        chat_manager.reset_history()
        logger.info("Onboarding resetado. Usuário precisará reconfigurar.")
        return {"success": True}
    return {"success": False, "error": "Failed to reset onboarding"}

@app.post("/api/onboarding/test_keys")
async def test_api_keys(request: OnboardingRequest):
    """Testa se as chaves de API informadas são válidas e conseguem completar prompts básicos."""
    import litellm
    
    # Suprime relatórios excessivos
    litellm.suppress_debug_info = True
    
    results = {}
    supplied_keys = 0
    failed_keys = 0
    
    # 1. Testa OpenAI
    openai_key = request.api_keys.get("openai", "").strip()
    if openai_key:
        supplied_keys += 1
        try:
            litellm.completion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Ping"}],
                api_key=openai_key,
                max_tokens=5
            )
            results["openai"] = {"success": True}
        except Exception as e:
            results["openai"] = {"success": False, "error": str(e)}
            failed_keys += 1

    # 2. Testa Moonshot
    moonshot_key = request.api_keys.get("moonshot", "").strip()
    if moonshot_key:
        supplied_keys += 1
        try:
            litellm.completion(
                model="openai/moonshot-v1-8k",
                messages=[{"role": "user", "content": "Ping"}],
                api_key=moonshot_key,
                api_base="https://api.moonshot.cn/v1",
                max_tokens=5
            )
            results["moonshot"] = {"success": True}
        except Exception as e:
            results["moonshot"] = {"success": False, "error": str(e)}
            failed_keys += 1

    # 3. Testa Anthropic
    anthropic_key = request.api_keys.get("anthropic", "").strip()
    if anthropic_key:
        supplied_keys += 1
        try:
            litellm.completion(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "Ping"}],
                api_key=anthropic_key,
                max_tokens=5
            )
            results["anthropic"] = {"success": True}
        except Exception as e:
            results["anthropic"] = {"success": False, "error": str(e)}
            failed_keys += 1

    # 4. Avalia Google (Gemini)
    google_key = request.api_keys.get("google", "").strip()
    if google_key:
        supplied_keys += 1
        try:
            litellm.completion(
                model="gemini/gemini-pro",
                messages=[{"role": "user", "content": "Ping"}],
                api_key=google_key,
                max_tokens=5
            )
            results["google"] = {"success": True}
        except Exception as e:
            results["google"] = {"success": False, "error": str(e)}
            failed_keys += 1
            
    # Checa credenciais do Antigravity no Vault
    has_antigravity = False
    try:
        from local.vault.master_vault import MasterVault
        vault = MasterVault()
        if vault.get_secret("google_antigravity_creds"):
            results["google_antigravity"] = {"success": True}
            has_antigravity = True
    except:
        pass

    # Condição de Falha Restrita:
    if failed_keys > 0:
        return {"success": False, "error": "Uma ou mais chaves fornecidas são inválidas.", "details": results}

    if supplied_keys == 0 and not has_antigravity:
        return {"success": False, "error": "Nenhuma chave preenchida e nenhum login Antigravity detectado.", "details": results}
        
    return {"success": True, "details": results}

# ─── CONFIG / MODEL SELECTION ───

@app.get("/api/config")
async def get_config():
    """Retorna o modelo ativo e a lista de modelos disponíveis."""
    return {
        "active_model": get_active_chat_model(),
        "models": get_available_models(),
    }

@app.post("/api/config")
async def set_config(request: ModelSelectRequest):
    """Atualiza o modelo ativo e recarrega o ChatManager."""
    model_id = request.model_id.strip()
    if not model_id:
        return {"success": False, "error": "model_id required"}

    # Persistir no config.yaml
    ok = set_active_chat_model(model_id)
    if not ok:
        return {"success": False, "error": "Failed to save config"}

    # Atualizar o ChatManager em tempo real
    chat_manager.switch_model(model_id)

    logger.info(f"Modelo alterado para: {model_id}")
    return {"success": True, "active_model": model_id}

@app.get("/api/status")
async def get_status():
    """Retorna informações gerais de status do sistema e onboarding."""
    return {
        "active_model": chat_manager.model,
        "vps_status": "ONLINE",
        "local_status": "ONLINE",
        "sync_status": "ESTÁVEL",
        "onboarding_completed": is_onboarding_completed(),
        "agent_name": get_agent_name(),
        "user_name": get_user_name()
    }

@app.get("/api/patterns")
async def get_patterns():
    from memory.causal_bank import CausalBank
    bank = CausalBank(origin="vps")
    # Busca padrões de todos os domínios
    all_patterns = []
    domains = ["macro", "geopolitics_to_finance", "general"]
    for domain in domains:
        patterns = bank.get_active_patterns(domain)
        all_patterns.extend(patterns)
    return all_patterns

def start_dashboard(host: str = "0.0.0.0", port: int = 8085):
    import uvicorn
    import asyncio
    logger.info(f"Dashboard disponível em http://localhost:{port}")
    config = uvicorn.Config(app, host=host, port=port, loop="asyncio")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


# === VOICE ENDPOINTS ===

@app.post("/api/voice/speak")
async def speak_endpoint(request: Request):
    """Make Rebeka speak the given text."""
    try:
        body = await request.json()
        text = body.get("text", "")
        
        if not text:
            return {"success": False, "error": "No text provided"}
            
        # Import and use voice module
        from interfaces.voice_module import get_voice_manager
        voice = get_voice_manager()
        voice.speak(text)
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Voice speak error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/voice/status")
async def voice_status_endpoint():
    """Get voice status."""
    from interfaces.voice_module import get_voice_manager
    voice = get_voice_manager()
    return {
        "voice_enabled": voice.is_voice_enabled(),
        "tts_available": True,
        "stt_available": True
    }


@app.post("/api/voice/toggle")
async def voice_toggle_endpoint(request: Request):
    """Toggle voice on/off."""
    try:
        body = await request.json()
        enabled = body.get("enabled", True)
        
        from interfaces.voice_module import get_voice_manager
        voice = get_voice_manager()
        voice.toggle_voice(enabled)
        
        return {"success": True, "voice_enabled": enabled}
    except Exception as e:
        logger.error(f"Voice toggle error: {e}")
        return {"success": False, "error": str(e)}


