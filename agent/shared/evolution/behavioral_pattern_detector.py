import logging
from typing import Dict, Any, List, Optional
from shared.database.causal_bank import CausalBank
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class BehavioralPatternDetector:
    """
    Analisa as ações no banco causal para encontrar padrões de comportamento,
    incrementando a confiança quando o padrão se repete.
    
    INTENÇÃO: Antes de corrigir o usuário, Rebeka precisa ter 'certeza matemática'
    de que aquele padrão é limitador e repetitivo, não apenas um dia ruim.
    """

    def __init__(self, causal_bank: CausalBank):
        self.db = causal_bank
        
    def analyze_recent_actions(self, user_id: str, domain: str) -> None:
        """
        No futuro: Varre 'user_decisions' e 'trade_executions' (exemplo) buscando
        padrões. Se encontrar, chama `register_observation()`.
        """
        logger.info(f"Analisando histórico recente do domínio '{domain}' em busca de padrões.")
        pass

    def register_observation(self, domain: str, pattern_type: str, evidence: Dict[str, Any]) -> str:
        """
        Uma nova evidência de um padrão foi notada.
        Se o padrão já existe, incrementa. Se não, cria.
        """
        # 1. Busca se esse padrao existe ativo
        existing_patterns = self.db.get_behavioral_patterns(domain=domain)
        target_pattern = next((p for p in existing_patterns if p["type"] == pattern_type), None)
        
        if target_pattern:
            # Padrão existe, incrementa (com registro append-only no fundo)
            logger.info(f"Padrão limitante '{pattern_type}' re-observado. Aumentando confiança.")
            new_id = self.db.append_behavioral_evidence(target_pattern["id"], evidence)
            return new_id
        else:
            # Padrão novo
            logger.info(f"Novo padrão '{pattern_type}' detectado primeira vez. Inicializando.")
            pattern_data = {
                "domain": domain,
                "pattern_type": pattern_type,
                "description": f"Padrão {pattern_type} detectado inicialmente.",
                "confidence": 0.2,  # Baixa no inicio
                "first_detected_at": datetime.now(timezone.utc),
                "potentially_limiting": True,
                "evidence": [evidence],
                "confirmation_count": 1
            }
            return self.db.insert_behavioral_pattern(pattern_data)

    def is_pattern_confident(self, pattern_type: str, domain: str, threshold: float = 0.7) -> bool:
        """Retorna True se temos confiança estatística suficiente no padrão."""
        patterns = self.db.get_behavioral_patterns(domain=domain, min_confidence=threshold)
        for p in patterns:
            if p["type"] == pattern_type:
                return True
        return False
