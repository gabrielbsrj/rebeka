# shared/intent/intent_mapper.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — mapeia regras a intenções declaradas

"""
Intent Mapper — Mapeia regras a intenções.

INTENÇÃO: "Não é uma regra — é uma expressão de uma intenção."
Cada regra de segurança tem um "why". Este módulo extrai e organiza
essas intenções para que o agente entenda por que cada regra existe,
não apenas que ela existe.
"""

import logging
from typing import Dict, Any, List, Optional

import yaml

logger = logging.getLogger(__name__)


class IntentMapper:
    """
    Mapeia regras a intenções declaradas.

    INTENÇÃO: Quando o agente encontra uma restrição, ele não vê um muro.
    Vê uma intenção cristalizada. Este módulo torna isso explícito.
    """

    def __init__(self, security_config: Dict[str, Any]):
        """
        Args:
            security_config: Configuração completa do security_phase1.yaml
        """
        self._config = security_config
        self._intent_map: Dict[str, Dict] = {}
        self._build_intent_map()

    def _build_intent_map(self):
        """Extrai todos os 'why' da configuração e mapeia a intenções."""
        self._extract_whys(self._config, path="")

    def _extract_whys(self, obj: Any, path: str):
        """Recursivamente extrai campos 'why' do YAML."""
        if isinstance(obj, dict):
            if "why" in obj:
                self._intent_map[path] = {
                    "rule_path": path,
                    "intention": obj["why"].strip(),
                    "evolution_condition": obj.get("evolution_condition", "").strip(),
                    "current_value": {k: v for k, v in obj.items()
                                     if k not in ("why", "evolution_condition")},
                }
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self._extract_whys(value, new_path)

    def get_intention(self, rule_path: str) -> Optional[Dict]:
        """
        Retorna a intenção por trás de uma regra.

        Args:
            rule_path: Caminho da regra (ex: "finance.paper_trading")

        Returns:
            Dict com intention, evolution_condition, current_value
        """
        return self._intent_map.get(rule_path)

    def get_all_intentions(self) -> Dict[str, Dict]:
        """Retorna mapa completo de intenções."""
        return self._intent_map.copy()

    def get_evolution_conditions(self) -> List[Dict]:
        """
        Retorna todas as condições de evolução.

        INTENÇÃO: O transcendence_tracker usa isso para verificar
        quais restrições podem ser removidas.
        """
        conditions = []
        for path, intent in self._intent_map.items():
            if intent.get("evolution_condition"):
                conditions.append({
                    "rule": path,
                    "intention": intent["intention"],
                    "condition": intent["evolution_condition"],
                })
        return conditions
