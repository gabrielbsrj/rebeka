import logging
from typing import Dict, Any, Optional
from shared.database.causal_bank import CausalBank
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class IntentionalFriction:
    """
    Decide quando e quanta fricção aplicar a uma decisão/comportamento do usuário.
    
    INTENÇÃO: Agentes normais dizem 'sim senhor'. A Rebeka (Orquestradora de crescimento)
    diz: 'Espera aí. Você quer mesmo fazer X com base nessas evidências de que X dói?'
    """

    def __init__(self, causal_bank: CausalBank):
        self.db = causal_bank

    def evaluate_action(self, action_context: Dict[str, Any], detected_pattern: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Avalia uma intenção de ação no calor do momento.
        Se bater com padrão limitante com alta confidence, aplica fricção.
        """
        if not detected_pattern:
            # Sem padrão identificado, deixa seguir
            return {"apply_friction": False, "level": "none", "message": ""}
            
        confidence = detected_pattern.get("confidence", 0.0)
        pattern_type = detected_pattern.get("type", "unknown")
        
        # Decide nivel de fricção
        friction_level, message = self._decide_friction_level(pattern_type, confidence)
        
        if friction_level == "none":
            return {"apply_friction": False, "level": "none", "message": ""}
            
        logger.info(f"Aplicando fricção '{friction_level}' sobre ação ativando padrão '{pattern_type}'")
        
        # Registra fricção
        friction_data = {
            "category": pattern_type,
            "pattern_triggered": detected_pattern.get("id"),
            "friction_level": friction_level,
            "message_sent": message,
            "response_timestamp": datetime.now(timezone.utc)
        }
        self.db.insert_friction_log(friction_data)
        
        return {
            "apply_friction": True,
            "level": friction_level,
            "message": message
        }
        
    def _decide_friction_level(self, pattern_type: str, confidence: float) -> tuple[str, str]:
        """Lógica de escala de fricção."""
        if confidence < 0.6:
            return "none", ""
            
        elif 0.6 <= confidence < 0.8:
            return "leve", (
                "Rebeka 💭: Identifiquei um padrão aqui... Só para confirmar: "
                "Certeza que quer seguir por esse caminho agora?"
            )
            
        elif 0.8 <= confidence < 0.9:
            return "moderada", (
                "Rebeka 🤚: Opa, peraí. Você definiu que faria diferente. "
                "Essa ação parece entrar naquele padrão que combinamos de evitar. "
                "Quer que eu bloqueie essa ação por 5 minutos pra você pensar?"
            )
            
        else: # > 0.9 = Certeza matemática, fricção direta
            return "direta", (
                "Rebeka 🛑: Não vou executar isso agora. Você está prestes a repetir "
                "exatamente o que lhe causa dor. Prove para mim no prompt o raciocínio lógico "
                "dessa ação ou cancele."
            )
