# shared/database/pattern_pruner.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — gerenciador de decaimento temporal

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PatternPruner:
    """
    Gerencia o decaimento temporal e arquivamento de padrões.

    INTENÇÃO: O mundo muda. O que funcionava ontem pode não funcionar hoje.
    Reduz pesos de padrões sem confirmação e move para 'deprecated' se necessário.
    """

    def __init__(self, decay_rate: float = 0.01, min_weight: float = 0.2):
        self.decay_rate = decay_rate
        self.min_weight = min_weight

    def apply_decay(self, current_weight: float, days_since_last_confirmation: int) -> float:
        """
        Calcula o novo peso baseado no tempo.
        
        Fórmula: weight = current_weight * (1 - decay_rate)^days
        """
        new_weight = current_weight * ((1 - self.decay_rate) ** days_since_last_confirmation)
        return max(new_weight, self.min_weight)

    def should_deprecate(self, weight: float, confidence: float) -> bool:
        """
        Determina se um padrão deve ser arquivado.
        """
        # Se o peso caiu muito e a confiança é baixa, arquiva.
        return weight <= self.min_weight and confidence < 0.4
