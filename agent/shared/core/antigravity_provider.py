# agent/shared/core/antigravity_provider.py
# VERSION: 3.0.0
# LAST_MODIFIED: 2026-03-01
# CHANGELOG: v3 — Chamada HTTP direta ao Antigravity (sem LiteLLM), Bearer token auth

import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AntigravityProvider:
    """
    Adaptador para a API do Google Antigravity (Cloud Code Assist).
    Permite usar Claude Opus e Gemini via infra do Google Cloud.
    
    INTENÇÃO: Usa o access_token OAuth do login para fazer chamadas
    HTTP diretas à API Cloud Code Assist do Google, que roteia para Claude/Gemini.
    Não depende do LiteLLM — usa httpx com Bearer token.
    """
    
    API_BASE = "https://cloudcode-pa.googleapis.com/v1internal"
    
    MODEL_ALIASES = {
        "claude-opus-4-6-thinking": "claude-3-5-sonnet@20241022",
        "gemini-3-flash-preview": "gemini-2.0-flash",
        "gemini-3-pro-preview": "gemini-2.0-pro-exp-02-05",
        "gemini-pro-3-1": "gemini-2.0-pro-exp-02-05",
    }
    
    def __init__(self):
        self.creds = self._load_creds()
        
    def _load_creds(self) -> Optional[Dict[str, Any]]:
        try:
            from local.vault.master_vault import MasterVault
            vault = MasterVault()
            return vault.get_secret("google_antigravity_creds")
        except Exception as e:
            logger.error(f"Erro ao carregar credenciais do Antigravity: {e}")
            return None

    def _refresh_token_if_needed(self) -> bool:
        """
        Verifica se o token precisa de refresh e atualiza se necessário.
        
        Returns:
            True se o token é válido (original ou atualizado), False se falhou.
        """
        if not self.creds:
            return False
            
        import time
        
        expires_at = self.creds.get("expires_at", 0)
        now = time.time()
        
        # Se ainda tem 5 minutos de validade, não precisa refresh
        if expires_at > now + 300:
            return True
            
        # Token expirado - tentar refresh
        refresh_token = self.creds.get("refresh_token")
        if not refresh_token:
            logger.warning("Token expirado e sem refresh_token. Necessário novo login.")
            return False
            
        try:
            import requests
            from local.tools.login_antigravity import CLIENT_ID, CLIENT_SECRET, TOKEN_URL
            
            response = requests.post(TOKEN_URL, data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            
            if response.status_code != 200:
                logger.error(f"Refresh token falhou: {response.text}")
                return False
                
            data = response.json()
            self.creds["access_token"] = data["access_token"]
            self.creds["expires_at"] = time.time() + data.get("expires_in", 3600) - 300
            
            # Salvar credenciais atualizadas
            from local.vault.master_vault import MasterVault
            vault = MasterVault()
            vault.save_secret("google_antigravity_creds", self.creds)
            
            logger.info("Token do Antigravity atualizado com sucesso.")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar token: {e}")
            return False

    async def completion(self, model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Faz chamada direta ao Google Antigravity via HTTP com Bearer token.
        
        Formato de entrada: OpenAI-like.
        Formato de saída: OpenAI-like.
        """
        if not self.creds:
            raise Exception("Credenciais do Google Antigravity não encontradas. Faça login primeiro.")
        
        # Verificar/refresh token
        if not self._refresh_token_if_needed():
            raise Exception("Token expirado e não foi possível atualizar. Faça login novamente.")
        
        # Resolver alias de modelo
        model_name = model.split("/")[-1] if "/" in model else model
        resolved_model = self.MODEL_ALIASES.get(model_name, model_name)
        
        logger.info(f"Antigravity: chamando modelo {resolved_model} (original: {model})")
        
        # Construir payload OpenAI-compatible
        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": 1.0,
        }
        if tools:
            payload["tools"] = tools
        
        # Headers com Bearer token do OAuth
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.creds['access_token']}",
        }
        
        url = f"{self.API_BASE}/chat/completions"
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Antigravity API retornou {response.status_code}: {error_text}")
                raise Exception(f"Antigravity API error {response.status_code}: {error_text}")
            
            data = response.json()
            
            # Normalizar resposta para formato OpenAI-like
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})
            
            return {
                "choices": [{
                    "message": {
                        "role": message.get("role", "assistant"),
                        "content": message.get("content", ""),
                        "tool_calls": message.get("tool_calls")
                    },
                    "finish_reason": choice.get("finish_reason", "stop")
                }],
                "usage": {
                    "total_tokens": usage.get("total_tokens", 0)
                }
            }
            
        except httpx.TimeoutException:
            logger.error("Timeout na chamada ao Antigravity API")
            raise Exception("Timeout ao conectar com o Antigravity. Tente novamente.")
        except Exception as e:
            logger.error(f"Erro na API Antigravity: {e}")
            raise e
