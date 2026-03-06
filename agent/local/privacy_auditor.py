# agent/local/privacy_auditor.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v2 — Implementação de get_audit_trail com busca no banco

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from shared.database.causal_bank import CausalBank
from shared.database.models import PrivacyAuditLog

logger = logging.getLogger(__name__)

class PrivacyAuditor:
    """
    Auditor de Privacidade do Gêmeo Local.
    
    INTENÇÃO: Todo dado que sai do dispositivo local deve ser logado.
    O usuário tem o direito soberano de saber o que foi compartilhado.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def _auto_redact(self, text: str) -> str:
        import re
        if not isinstance(text, str):
            return text
            
        # Regex Padrões
        cpf_pattern = r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b'
        cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
        
        redacted = re.sub(cpf_pattern, '[CONFIDENTIAL_CPF_REDACTED]', text)
        redacted = re.sub(cc_pattern, '[CONFIDENTIAL_CC_REDACTED]', redacted)
        
        return redacted

    def audit_outgoing(self, data_type: str, content: Any, destination: str = "vps"):
        """
        Registra o compartilhamento de um dado. Filtra dados PII ativos.
        """
        safe_content = content
        if isinstance(content, str):
            safe_content = self._auto_redact(content)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_type": data_type,
            "destination": destination,
            "summary_hash": str(hash(str(safe_content))) 
        }
        
        try:
            self.bank.insert_privacy_audit_log({
                "data_type": data_type,
                "destination": destination,
                "abstraction_sent": str(safe_content)[:200], 
                "approved_by_filter": True,
                "transmission_confirmed": False
            })
            
            logger.info(f"Audit Log: Compartilhamento de {data_type} registrado. Msc: {str(safe_content)[:30]}...")
        except Exception as e:
            logger.error(f"Falha ao registrar log de auditoria: {str(e)}")

    def get_audit_trail(self, limit: int = 100, data_type: str = None) -> List[Dict[str, Any]]:
        """
        Retorna os últimos registros de auditoria.
        
        INTENÇÃO: Permite ao usuário ver exatamente o que foi compartilhado
        com o gêmeo VPS ou outros destinos.
        
        Args:
            limit: Número máximo de registros
            data_type: Filtrar por tipo de dado (opcional)
            
        Returns:
            Lista de registros de auditoria
        """
        try:
            session = self.bank._SessionFactory()
            
            query = session.query(self.bank.PrivacyAuditLog).order_by(
                self.bank.PrivacyAuditLog.timestamp.desc()
            ).limit(limit)
            
            if data_type:
                query = query.filter(self.bank.PrivacyAuditLog.data_type == data_type)
            
            logs = query.all()
            
            result = []
            for log in logs:
                result.append({
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "data_type": log.data_type,
                    "destination": log.destination,
                    "abstraction_sent": log.abstraction_sent[:100] + "..." if log.abstraction_sent and len(log.abstraction_sent) > 100 else log.abstraction_sent,
                    "approved_by_filter": log.approved_by_filter,
                    "transmission_confirmed": log.transmission_confirmed,
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar audit trail: {str(e)}")
            return []
