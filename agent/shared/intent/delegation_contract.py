# agent/shared/intent/delegation_contract.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DelegationContract:
    """
    Delegation Contract — Define o 'Mandato' de uma credencial.
    
    INTENÇÃO: Impedir que uma credencial do portal jurídico seja usada
    para, por exemplo, tentar acessar uma rede social ou corretora.
    Atrela a permissão à INTENÇÃO do Planejador.
    """
    
    def __init__(self, role: str, credential_id: str, allowed_intents: List[str], forbidden_intents: Optional[List[str]] = None):
        self.role = role
        self.credential_id = credential_id # O ID no vault://
        self.allowed_intents = allowed_intents
        self.forbidden_intents = forbidden_intents or []
        self.autonomy_level = "Fase_1" # Começa pedindo confirmação

    def validate_action(self, current_intent: str) -> Dict[str, Any]:
        """
        Verifica se a intenção atual é permitida pelo contrato deste mandato.
        """
        if current_intent in self.forbidden_intents:
            return {
                "allowed": False, 
                "reason": f"Ação '{current_intent}' é explicitamente PROIBIDA no contrato de {self.role}."
            }
            
        if current_intent in self.allowed_intents:
            return {"allowed": True, "reason": "Ação permitida pelo contrato."}
            
        # Para intenções não listadas explicitamente
        return {
            "allowed": False, 
            "reason": f"Ação '{current_intent}' está fora do escopo do contrato de {self.role}."
        }

class ContractRegistry:
    """
    Gerencia todos os contratos de delegação ativos.
    """
    def __init__(self):
        self.contracts: Dict[str, DelegationContract] = {}

    def register_contract(self, contract: DelegationContract):
        self.contracts[contract.credential_id] = contract
        logger.info(f"Contrato de delegação registrado para: {contract.credential_id} ({contract.role})")

    def check_authorization(self, credential_id: str, intent: str) -> Dict[str, Any]:
        contract = self.contracts.get(credential_id)
        if not contract:
            return {"allowed": False, "reason": f"Nenhum contrato de delegação encontrado para {credential_id}."}
        
        return contract.validate_action(intent)
