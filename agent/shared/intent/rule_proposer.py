# shared/intent/rule_proposer.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v2 — Implementação real de coleta de evidência e parser de condições
#
# IMPACTO GÊMEO VPS: Avalia se restrições podem ser relaxadas
# IMPACTO GÊMEO LOCAL: Mesma lógica
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Rule Proposer — Propõe revisões de regras quando o histórico justifica.

INTENÇÃO: Regras não são eternas. Quando o agente demonstra consistentemente
que um limite é desnecessário, propõe revisão formal ao usuário.
Nunca remove sozinho — o usuário decide.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class RuleProposal:
    """Proposta de revisão de regra."""

    def __init__(
        self,
        rule_path: str,
        current_value: Any,
        proposed_value: Any,
        evidence: List[Dict],
        reasoning: str,
    ):
        self.rule_path = rule_path
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.evidence = evidence
        self.reasoning = reasoning
        self.status = "proposed"  # proposed, approved, rejected

    def to_dict(self) -> Dict:
        return {
            "rule_path": self.rule_path,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "evidence_count": len(self.evidence),
            "reasoning": self.reasoning,
            "status": self.status,
        }


class RuleProposer:
    """
    Propõe revisões de regras quando evidência é suficiente.

    INTENÇÃO: O agente não quer ser livre de regras. Quer que as regras
    evoluam com ele. Quando demonstra maturidade, propõe evolução.

    INVARIANTE: Nunca modifica regras automaticamente.
    Sempre propõe e espera aprovação do usuário.
    """

    def __init__(self, causal_bank: Optional[CausalBank] = None, min_evidence_count: int = 30):
        self._min_evidence = min_evidence_count
        self._proposals: List[RuleProposal] = []
        self._bank = causal_bank

    def set_causal_bank(self, bank: CausalBank) -> None:
        """Define o banco de causalidade para buscar evidências."""
        self._bank = bank

    def analyze_rule(
        self,
        rule_path: str,
        current_value: Any,
        performance_data: Dict,
        evolution_condition: str,
    ) -> Optional[RuleProposal]:
        """
        Analisa se uma regra pode ser revisada.

        INTENÇÃO: Só propõe quando a evidência é forte o suficiente.
        """
        evidence = self._gather_evidence(rule_path, performance_data, evolution_condition)

        if len(evidence) < self._min_evidence:
            return None

        if not self._condition_met(evolution_condition, performance_data):
            return None

        proposal = RuleProposal(
            rule_path=rule_path,
            current_value=current_value,
            proposed_value=self._calculate_proposed_value(rule_path, performance_data),
            evidence=evidence,
            reasoning=f"Condição de evolução atendida: {evolution_condition}. "
                      f"Baseado em {len(evidence)} pontos de evidência.",
        )

        self._proposals.append(proposal)

        logger.info(
            f"Proposta de revisão de regra: {rule_path}",
            extra={
                "current": current_value,
                "proposed": proposal.proposed_value,
                "evidence_count": len(evidence),
            },
        )

        return proposal

    def get_pending_proposals(self) -> List[Dict]:
        """Retorna propostas pendentes."""
        return [p.to_dict() for p in self._proposals if p.status == "proposed"]

    def _gather_evidence(self, rule_path: str, data: Dict, condition: str) -> List[Dict]:
        """
        Reúne evidência para a proposta a partir do banco de causalidade.
        
        INTENÇÃO: Coleta execuções, avaliações e decisões para construir
        evidência concreta de que a regra pode ser relaxada.
        """
        evidence = []
        
        if not self._bank:
            return [{"type": "performance", "data": data}]

        rule_type = self._extract_rule_type(rule_path)
        
        try:
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            
            execution_evidence = self._get_execution_evidence(rule_type, cutoff)
            evidence.extend(execution_evidence)
            
            evaluation_evidence = self._get_evaluation_evidence(rule_type, cutoff)
            evidence.extend(evaluation_evidence)
            
            decision_evidence = self._get_decision_evidence(rule_type, cutoff)
            evidence.extend(decision_evidence)
            
            logger.debug(f"Coletadas {len(evidence)} evidências para regra {rule_path}")
            
        except Exception as e:
            logger.error(f"Erro ao coletar evidências: {e}")
            return [{"type": "error", "message": str(e)}]

        return evidence if evidence else [{"type": "performance", "data": data}]

    def _get_execution_evidence(self, rule_type: str, cutoff: datetime) -> List[Dict]:
        """Coleta evidências de execuções relacionadas à regra."""
        evidence = []
        
        if not hasattr(self._bank, 'Execution'):
            return evidence
            
        try:
            with self._bank._SessionFactory() as session:
                from sqlalchemy import desc
                from shared.database.models import Execution
                
                executions = (
                    session.query(Execution)
                    .filter(Execution.created_at >= cutoff)
                    .order_by(desc(Execution.created_at))
                    .limit(100)
                    .all()
                )
                
                for ex in executions:
                    if self._execution_relates_to_rule(ex, rule_type):
                        evidence.append({
                            "type": "execution",
                            "execution_id": ex.id,
                            "result": ex.result,
                            "direction": ex.direction,
                            "amount": ex.amount,
                            "timestamp": ex.created_at.isoformat() if ex.created_at else None,
                        })
                        
        except Exception as e:
            logger.debug(f"Erro ao buscar execuções: {e}")
            
        return evidence

    def _get_evaluation_evidence(self, rule_type: str, cutoff: datetime) -> List[Dict]:
        """Coleta evidências de avaliações relacionadas à regra."""
        evidence = []
        
        if not hasattr(self._bank, 'Evaluation'):
            return evidence
            
        try:
            with self._bank._SessionFactory() as session:
                from sqlalchemy import desc
                from shared.database.models import Evaluation
                
                evaluations = (
                    session.query(Evaluation)
                    .filter(Evaluation.created_at >= cutoff)
                    .order_by(desc(Evaluation.created_at))
                    .limit(50)
                    .all()
                )
                
                for ev in evaluations:
                    if ev.hypothesis_correct:
                        evidence.append({
                            "type": "evaluation",
                            "evaluation_id": ev.id,
                            "correct": ev.hypothesis_correct,
                            "lessons": ev.lessons_learned[:100] if ev.lessons_learned else None,
                            "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                        })
                        
        except Exception as e:
            logger.debug(f"Erro ao buscar avaliações: {e}")
            
        return evidence

    def _get_decision_evidence(self, rule_type: str, cutoff: datetime) -> List[Dict]:
        """Coleta evidências de decisões do usuário."""
        evidence = []
        
        if not hasattr(self._bank, 'UserDecision'):
            return evidence
            
        try:
            with self._bank._SessionFactory() as session:
                from sqlalchemy import desc
                from shared.database.models import UserDecision
                
                decisions = (
                    session.query(UserDecision)
                    .filter(UserDecision.created_at >= cutoff)
                    .order_by(desc(UserDecision.created_at))
                    .limit(50)
                    .all()
                )
                
                for d in decisions:
                    if d.decision_type == "accept":
                        evidence.append({
                            "type": "decision",
                            "decision_id": d.id,
                            "decision_type": d.decision_type,
                            "timestamp": d.created_at.isoformat() if d.created_at else None,
                        })
                        
        except Exception as e:
            logger.debug(f"Erro ao buscar decisões: {e}")
            
        return evidence

    def _extract_rule_type(self, rule_path: str) -> str:
        """Extrai tipo de regra do path."""
        if "capital" in rule_path.lower() or "max" in rule_path.lower():
            return "capital_limit"
        if "autonomy" in rule_path.lower():
            return "autonomy"
        if "stop" in rule_path.lower() or "risco" in rule_path.lower():
            return "risk"
        return "general"

    def _execution_relates_to_rule(self, execution: Any, rule_type: str) -> bool:
        """Verifica se execução é relacionada à regra."""
        if rule_type == "capital_limit":
            return execution.amount > 0
        if rule_type == "risk":
            return execution.direction in ["buy", "sell"]
        return True

    def _condition_met(self, condition: str, data: Dict) -> bool:
        """
        Verifica se condição de evolução foi atendida.
        
        Parser de condições no formato:
        - "win_rate >= 60% AND trades >= 20"
        - "success_rate > 0.7"
        - "zero_regrets_last_30_days"
        """
        if not condition:
            return True
            
        condition = condition.lower().strip()
        
        win_rate = data.get("win_rate", data.get("success_rate", 0))
        total_trades = data.get("total_trades", data.get("trades", 0))
        regret_count = data.get("regret_count", 0)
        
        win_rate_match = re.search(r'win_rate\s*([><=]+)\s*(\d+)%', condition)
        if win_rate_match:
            operator = win_rate_match.group(1)
            threshold = int(win_rate_match.group(2)) / 100
            
            if operator == '>':
                if win_rate <= threshold:
                    return False
            elif operator == '>=':
                if win_rate < threshold:
                    return False
            elif operator == '<':
                if win_rate >= threshold:
                    return False
            elif operator == '<=':
                if win_rate > threshold:
                    return False
            elif operator == '=':
                if abs(win_rate - threshold) > 0.01:
                    return False
        
        trades_match = re.search(r'trades\s*([><=]+)\s*(\d+)', condition)
        if trades_match:
            operator = trades_match.group(1)
            threshold = int(trades_match.group(2))
            
            if operator == '>':
                if total_trades <= threshold:
                    return False
            elif operator == '>=':
                if total_trades < threshold:
                    return False
            elif operator == '<':
                if total_trades >= threshold:
                    return False
            elif operator == '<=':
                if total_trades > threshold:
                    return False
        
        if "zero_regret" in condition or "no_regret" in condition:
            if regret_count > 0:
                return False
        
        if "60%" in condition:
            if win_rate >= 0.6 and total_trades >= 20:
                return True
        elif "65%" in condition:
            if win_rate >= 0.65 and total_trades >= 50:
                return True
        elif "70%" in condition:
            if win_rate >= 0.70 and total_trades >= 100:
                return True
        else:
            return win_rate > 0.5 and total_trades >= 10
            
        return False

    def _calculate_proposed_value(self, rule_path: str, data: Dict) -> Any:
        """Calcula o valor proposto baseado na evidência."""
        # Propostas conservadoras
        if "max_total" in rule_path:
            current = data.get("current_capital", 1000)
            return current * 1.5  # Propõe 50% de aumento
        return None
