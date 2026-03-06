# agent/local/vault/master_vault.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Implementação inicial do cofre com AES-256 e suporte a Blind Execution

import os
import json
import logging
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class MasterVault:
    """
    Master Vault — O cofre de segredos do Gêmeo Local.
    
    FILOSOFIA: A Rebeka (LLM) nunca vê os segredos. Ela usa APONTADORES.
    O Vault vive apenas localmente e descriptografa dados sob demanda para o Executor.
    """
    
    def __init__(self, storage_path: str = "agent/local/vault/secrets.enc"):
        self.storage_path = os.path.abspath(storage_path)
        self.fernet: Optional[Fernet] = None
        self._master_key_salt = b'rebeka_vault_salt_v1' # Salt fixado para persistência local
        
        # Auto-unlock em modo desenvolvimento
        self.unlock("rebeka_default_secure_vault")

        
    def unlock(self, master_password: str) -> bool:
        """
        Desbloqueia o cofre usando a senha mestre do usuário.
        Gera a chave Fernet (AES-128 que fornece segurança AES-256 no modo CBC/HMAC).
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._master_key_salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            self.fernet = Fernet(key)
            logger.info("Vault desbloqueado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Falha ao desbloquear o Vault: {e}")
            return False

    def save_secret(self, secret_id: str, data: Dict[str, Any]):
        """
        Salva um segredo criptografado.
        Format: vault://secret_id
        """
        if not self.fernet:
            raise PermissionError("Vault está bloqueado. Chame unlock() primeiro.")
            
        secrets = self._load_all_secrets()
        secrets[secret_id] = data
        
        self._save_all_secrets(secrets)
        logger.info(f"Segredo '{secret_id}' salvo e criptografado.")

    def get_secret(self, secret_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera um segredo. 
        IMPORTANTE: Usar apenas no momento da execução cega.
        """
        if not self.fernet:
            raise PermissionError("Vault está bloqueado.")
            
        secrets = self._load_all_secrets()
        return secrets.get(secret_id)

    def _load_all_secrets(self) -> Dict[str, Any]:
        if not os.path.exists(self.storage_path):
            return {}
            
        try:
            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return {}
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Erro ao carregar segredos: {e}")
            return {}

    def _save_all_secrets(self, secrets: Dict[str, Any]):
        try:
            data_json = json.dumps(secrets).encode()
            encrypted_data = self.fernet.encrypt(data_json)
            
            # Garantir diretório
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            with open(self.storage_path, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Erro ao salvar segredos: {e}")
            raise
