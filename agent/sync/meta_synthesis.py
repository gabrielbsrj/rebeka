# agent/sync/meta_synthesis.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — aprendizado sobre divergências

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MetaSynthesis:
    """
    Meta-Synthesis — O aprendizado da divergência.
    
    INTENÇÃO: Aprende quais tipos de divergência são sintetizáveis 
    sem intervenção humana e quais requerem o usuário.
    """

    def __init__(self):
        self._synthesis_history: List[Dict] = []
        self._divergence_patterns: Dict[str, int] = {}

    def record_attempt(self, synthesis_result: Dict[str, Any], vps_view: Dict, local_view: Dict):
        """
        Registra um log estruturado da tentativa de síntese.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthesis_id": synthesis_result.get("synthesis_id"),
            "divergence_root": synthesis_result.get("divergence_root"),
            "quality": synthesis_result.get("synthesis_quality", 0.0),
            "requires_user": synthesis_result.get("requires_user", False),
            "views": {
                "vps": vps_view,
                "local": local_view
            }
        }
        
        self._synthesis_history.append(entry)
        
        # Incrementar padrão de divergência
        root = entry["divergence_root"] or "unknown"
        self._divergence_patterns[root] = self._divergence_patterns.get(root, 0) + 1
        
        logger.info(
            "Tentativa de síntese registrada no Meta-Synthesis",
            extra={"root": root, "requires_user": entry["requires_user"]}
        )

    def get_divergence_report(self) -> Dict[str, Any]:
        """
        Retorna relatório das divergências recorrentes.
        """
        return {
            "total_attempts": len(self._synthesis_history),
            "recurring_patterns": self._divergence_patterns,
            "average_quality": sum(h["quality"] for h in self._synthesis_history) / (len(self._synthesis_history) or 1),
            "user_intervention_rate": sum(1 for h in self._synthesis_history if h["requires_user"]) / (len(self._synthesis_history) or 1)
        }

    def suggest_optimization(self) -> Optional[str]:
        """
        Sugere melhorias no prompt da Synthesis Engine com base no histórico.
        """
        if not self._synthesis_history:
            return None
            
        # Simplificação: se muitas falhas em um root específico, sugere atenção
        for root, count in self._divergence_patterns.items():
            if count > 5:
                # Se o padrão de divergência for recorrente, sugere evoluir o prompt
                # para tratar esse caso específico via Causal Pattern
                return f"Divergência recorrente detectada em: {root}. Sugerir inclusão como Causal Pattern."
        
        return None
