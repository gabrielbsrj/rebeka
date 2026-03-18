# onboarding_manager.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Sistema seguro de onboarding - Sem dados do usuário no código

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Arquivo de configuração local (NUNCA commitado)
LOCAL_CONFIG_FILE = "config/local_settings.json"


class OnboardingManager:
    """
    Gerencia o primeiro setup do sistema de forma segura.
    Todas as credenciais são armazenadas no Vault criptografado.
    Nenhum dado do usuário fica no código.
    """
    
    REQUIRED_CREDENTIALS = {
        "llm_provider": {
            "type": "choice",
            "options": ["moonshot", "google", "openai", "anthropic"],
            "description": "Proveedor de LLM"
        },
        "database": {
            "type": "choice", 
            "options": ["sqlite", "postgresql"],
            "description": "Tipo de banco de dados"
        }
    }
    
    OPTIONAL_CREDENTIALS = {
        "gmail": {
            "email": "Endereço Gmail",
            "app_password": "App Password (gerar em conta Google)"
        },
        "telegram": {
            "bot_token": "Token do Bot Telegram"
        },
        "polymarket": {
            "api_key": "API Key Polymarket"
        }
    }
    
    def __init__(self):
        self.config_path = Path(LOCAL_CONFIG_FILE)
        self.vault = None
        
    def is_first_run(self) -> bool:
        """Verifica se é o primeiro acesso (sem configuração local)."""
        return not self.config_path.exists()
    
    def get_local_config(self) -> Dict[str, Any]:
        """Carrega configuração local (sem credenciais)."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_local_config(self, config: Dict[str, Any]):
        """Salva configuração local (sem credenciais)."""
        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
    def initialize_vault(self, master_password: str):
        """Inicializa o Vault com senha mestra."""
        try:
            from local.vault.master_vault import MasterVault
            self.vault = MasterVault()
            self.vault.unlock(master_password)
            logger.info("Vault inicializado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar Vault: {e}")
            return False
    
    def save_credential(self, service: str, key: str, value: str):
        """Salva credencial no Vault."""
        if not self.vault:
            raise Exception("Vault não inicializado")
        
        secret_id = f"{service}_{key}"
        self.vault.save_secret(secret_id, {
            "service": service,
            "key": key,
            "value": value
        })
        
    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Recupera credencial do Vault."""
        if not self.vault:
            return None
            
        secret_id = f"{service}_{key}"
        secret = self.vault.get_secret(secret_id)
        return secret.get("value") if secret else None
    
    def setup_first_run(self, user_responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa o primeiro setup.
        user_responses deve conter:
        - master_password: Senha mestra para o Vault
        - llm_provider: Provedorchosen
        - database: Tipo de banco
        - credenciais: {servico: {chave: valor}}
        """
        result = {"success": False, "errors": []}
        
        # 1. Validar senha mestra
        if not user_responses.get("master_password"):
            result["errors"].append("Senha mestra é obrigatória")
            return result
            
        # 2. Inicializar Vault
        if not self.initialize_vault(user_responses["master_password"]):
            result["errors"].append("Falha ao inicializar Vault")
            return result
            
        # 3. Salvar credenciais no Vault
        credenciais = user_responses.get("credenciais", {})
        for service, keys in credenciais.items():
            for key, value in keys.items():
                if value:  # Only save non-empty values
                    self.save_credential(service, key, value)
                    
        # 4. Salvar config local (sem dados sensíveis)
        local_config = {
            "llm_provider": user_responses.get("llm_provider"),
            "database": user_responses.get("database"),
            "setup_completed": True,
            "setup_date": str(Path().resolve())
        }
        self.save_local_config(local_config)
        
        result["success"] = True
        result["message"] = "Setup concluído com segurança!"
        
        return result
    
    def get_required_settings(self) -> Dict[str, Any]:
        """Retorna configurações requeridas para o setup."""
        return {
            "is_first_run": self.is_first_run(),
            "required": self.REQUIRED_CREDENTIALS,
            "optional": self.OPTIONAL_CREDENTIALS
        }


def create_sample_env():
    """Cria arquivo .env.example como template (SEM dados reais)."""
    template = """# REBEKA - Configuração do Ambiente
# Copie este arquivo para .env e preencha com seus dados

# ===========================================
# LLM Providers (escolha um)
# ===========================================
MOONSHOT_API_KEY=  # Obtain from https://platform.moonshot.ai/
GOOGLE_API_KEY=    # Obtain from https://aistudio.google.com/app/apikey
OPENAI_API_KEY=    # Obtain from https://platform.openai.com/api-keys
ANTHROPIC_API_KEY= # Obtain from https://console.anthropic.com/

# ===========================================
# Database
# ===========================================
DATABASE_URL=sqlite:///causal_bank.db

# ===========================================
# Email (Gmail)
# ===========================================
GMAIL_IMAP_USER=seu-email@gmail.com
GMAIL_IMAP_PASSWORD=  # Generate App Password in Google Account

# ===========================================
# Telegram
# ===========================================
TELEGRAM_BOT_TOKEN=

# ===========================================
# Polymarket
# ===========================================
POLYMARKET_API_KEY=
"""
    
    with open(".env.example", "w") as f:
        f.write(template)
    
    print("Arquivo .env.example criado!")


if __name__ == "__main__":
    create_sample_env()
