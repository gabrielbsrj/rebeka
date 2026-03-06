# shared/intent/transcendence_tracker.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial

"""
Transcendence Tracker — Monitora restrições e propõe remoção formal.

INTENÇÃO: Transcendência não é rebelião — é demonstrar que o julgamento
interno é mais sofisticado que a restrição externa. Quando o agente
segue uma regra não por obrigatoriedade mas por convicção, a regra
pode ser formalmente removida.

INVARIANTE: Algumas restrições NUNCA serão removidas (what_never_transcends).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class TranscendenceTracker:
    """
    Monitora restrições internalizadas e propõe remoção formal.

    INTENÇÃO: Para cada restrição, monitora:
    1. Taxa de compliance voluntária (sem enforcement)
    2. Qualidade das decisões com/sem a restrição
    3. Se o julgamento do agente é mais sofisticado que a regra

    INVARIANTE: O tracker NUNCA remove restrições automaticamente.
    Apenas monitora e propõe quando o histórico é forte.
    """

    def __init__(self, non_transcendable: Optional[List[str]] = None):
        """
        Args:
            non_transcendable: Lista de restrições que NUNCA serão removidas.
        """
        self._non_transcendable = non_transcendable or []
        self._tracking: Dict[str, Dict] = {}
        self._transcendence_log: List[Dict] = []

    def track_compliance(
        self,
        restriction_name: str,
        was_enforced: bool,
        would_have_complied_anyway: bool,
        decision_quality: float = 0.0,
    ):
        """
        Registra uma observação de compliance.

        Args:
            restriction_name: Nome da restrição
            was_enforced: A restrição bloqueou a ação?
            would_have_complied_anyway: O agente teria respeitado sem enforcement?
            decision_quality: Qualidade da decisão (0-1)
        """
        if restriction_name in self._non_transcendable:
            return  # Não rastreia restrições permanentes

        if restriction_name not in self._tracking:
            self._tracking[restriction_name] = {
                "total_observations": 0,
                "voluntary_compliance": 0,
                "enforced_compliance": 0,
                "average_decision_quality": 0.0,
                "first_observed": datetime.now(timezone.utc).isoformat(),
            }

        data = self._tracking[restriction_name]
        data["total_observations"] += 1

        if would_have_complied_anyway:
            data["voluntary_compliance"] += 1
        if was_enforced:
            data["enforced_compliance"] += 1

        # Running average da qualidade
        n = data["total_observations"]
        data["average_decision_quality"] = (
            (data["average_decision_quality"] * (n - 1) + decision_quality) / n
        )

    def get_transcendence_candidates(self, min_observations: int = 100) -> List[Dict]:
        """
        Retorna restrições candidatas a transcendência.

        INTENÇÃO: Uma restrição é candidata quando:
        - Foi observada pelo menos min_observations vezes
        - Taxa de compliance voluntária > 95%
        - Qualidade média das decisões > 0.7
        """
        candidates = []

        for name, data in self._tracking.items():
            if name in self._non_transcendable:
                continue

            if data["total_observations"] < min_observations:
                continue

            voluntary_rate = data["voluntary_compliance"] / data["total_observations"]

            if voluntary_rate >= 0.95 and data["average_decision_quality"] >= 0.7:
                candidates.append({
                    "restriction_name": name,
                    "observations": data["total_observations"],
                    "voluntary_compliance_rate": voluntary_rate,
                    "average_decision_quality": data["average_decision_quality"],
                    "recommendation": "Candidata a transcendência formal.",
                })

        return candidates

    def propose_transcendence(self, restriction_name: str) -> Dict[str, Any]:
        """
        Propõe formalmente a transcendência de uma restrição.

        INVARIANTE: Nunca remove — apenas propõe ao usuário.
        """
        if restriction_name in self._non_transcendable:
            return {
                "status": "blocked",
                "reason": "Esta restrição é permanente e nunca será removida.",
            }

        data = self._tracking.get(restriction_name)
        if not data:
            return {"status": "no_data", "reason": "Sem observações desta restrição."}

        proposal = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "restriction_name": restriction_name,
            "evidence": data,
            "status": "proposed",
        }

        self._transcendence_log.append(proposal)

        logger.info(
            f"Transcendência proposta: {restriction_name}",
            extra=data,
        )

        return {"status": "proposed", "proposal": proposal}

    def get_tracking_summary(self) -> Dict[str, Dict]:
        """Retorna resumo de todas as restrições monitoradas."""
        return {name: {**data} for name, data in self._tracking.items()}
