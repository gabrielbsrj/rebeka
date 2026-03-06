# shared/intent/feedback_collector.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Coleta feedback do usuário para aprendizado
#
# IMPACTO GÊMEO VPS: Não afetado diretamente
# IMPACTO GÊMEO LOCAL: Coleta feedback do usuário
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Feedback Collector — Captura feedback do usuário para aprendizado.

INTENÇÃO: O sistema aprende com feedback explícito do usuário.
Este módulo:
1. Captura feedback após fricções
2. Registra quando deveria ter perguntado
3. Coleta avaliações de clareza
4. Alimenta o meta-aprendizado
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Coleta feedback do usuário para aprendizado.

    INTENÇÃO: Captura o que o usuário pensa sobre as decisões do sistema.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def record_decision_feedback(
        self,
        decision_id: str,
        feedback_value: str,
        comment: Optional[str] = None,
    ) -> str:
        """
        Registra feedback sobre uma decisão do sistema.

        Args:
            decision_id: ID da decisão
            feedback_value: "correct", "incorrect", "should_have_asked"
            comment: Comentário opcional

        Returns:
            ID do feedback
        """
        return self.bank.insert_user_feedback({
            "feedback_type": "decision_approval",
            "context_id": decision_id,
            "context_type": "hypothesis",
            "feedback_value": feedback_value,
            "user_comment": comment,
        })

    def record_friction_response(
        self,
        friction_id: str,
        response: str,
        comment: Optional[str] = None,
    ) -> str:
        """
        Registra resposta do usuário a uma fricção.

        Args:
            friction_id: ID da fricção
            response: "receptivo", "defensivo", "ignorou", "refletiu"
            comment: Comentário opcional
        """
        return self.bank.insert_user_feedback({
            "feedback_type": "friction_response",
            "context_id": friction_id,
            "context_type": "friction",
            "feedback_value": response,
            "user_comment": comment,
        })

    def record_clarity_feedback(
        self,
        interaction_id: str,
        clarity_before: float,
        clarity_after: float,
        helpfulness: Optional[float] = None,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Registra feedback sobre clareza de uma interação.

        Args:
            interaction_id: ID da interação
            clarity_before: Clareza antes (0-1)
            clarity_after: Clareza depois (0-1)
            helpfulness: Helpfulness (0-1)
            rating: Avaliação (1-5)
            comment: Comentário opcional
        """
        quality_data = {
            "interaction_id": interaction_id,
            "interaction_type": "general",
            "clarity_before": clarity_before,
            "clarity_after": clarity_after,
            "helpfulness": helpfulness,
            "user_rating": rating,
            "feedback_text": comment,
        }
        
        return self.bank.insert_interaction_quality(quality_data)

    def record_escalation_feedback(
        self,
        decision_id: str,
        should_have_asked: bool,
        comment: Optional[str] = None,
    ) -> str:
        """
        Registra feedback sobre escalação.

        Args:
            decision_id: ID da decisão
            should_have_asked: Se o sistema deveria ter perguntado
            comment: Comentário opcional
        """
        value = "should_have_asked" if should_have_asked else "handled_correctly"
        
        return self.bank.insert_user_feedback({
            "feedback_type": "escalation_correct",
            "context_id": decision_id,
            "context_type": "hypothesis",
            "feedback_value": value,
            "user_comment": comment,
        })

    def ask_clarity_question(
        self,
        interaction_id: str,
        question: str,
    ) -> Dict[str, Any]:
        """
        Faz pergunta de clarificação ao usuário.

        Args:
            interaction_id: ID da interação
            question: Pergunta

        Returns:
            Dados para exibição ao usuário
        """
        return {
            "type": "clarity_question",
            "interaction_id": interaction_id,
            "question": question,
            "options": [
                {"value": "much_worse", "label": "Muito pior"},
                {"value": "worse", "label": "Pior"},
                {"value": "same", "label": "Same"},
                {"value": "better", "label": "Melhor"},
                {"value": "much_better", "label": "Muito melhor"},
            ],
        }

    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo de feedbacks.
        """
        feedbacks = self.bank.get_user_feedback(limit=100)
        
        if not feedbacks:
            return {"status": "no_feedback"}
        
        by_type = {}
        by_value = {}
        
        for f in feedbacks:
            t = f.get("type", "unknown")
            v = f.get("value", "unknown")
            
            by_type[t] = by_type.get(t, 0) + 1
            by_value[v] = by_value.get(v, 0) + 1
        
        qualities = self.bank.get_interaction_quality(limit=50)
        
        avg_clarity = 0
        avg_helpfulness = 0
        avg_rating = 0
        
        if qualities:
            valid_clarity = [q["clarity_delta"] for q in qualities if q.get("clarity_delta") is not None]
            valid_help = [q["helpfulness"] for q in qualities if q.get("helpfulness") is not None]
            valid_rating = [q["rating"] for q in qualities if q.get("rating") is not None]
            
            if valid_clarity:
                avg_clarity = sum(valid_clarity) / len(valid_clarity)
            if valid_help:
                avg_helpfulness = sum(valid_help) / len(valid_help)
            if valid_rating:
                avg_rating = sum(valid_rating) / len(valid_rating)
        
        return {
            "total_feedback": len(feedbacks),
            "by_type": by_type,
            "by_value": by_value,
            "avg_clarity_delta": avg_clarity,
            "avg_helpfulness": avg_helpfulness,
            "avg_rating": avg_rating,
        }


class MetaFeedbackLearner:
    """
    Aprende com feedback para ajustar comportamento.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def analyze_escalation_patterns(self) -> Dict[str, Any]:
        """Analisa padrões de escalação."""
        feedbacks = self.bank.get_user_feedback(feedback_type="escalation_correct", limit=50)
        
        if not feedbacks:
            return {"status": "no_data"}
        
        should_have = sum(1 for f in feedbacks if f.get("value") == "should_have_asked")
        handled_ok = sum(1 for f in feedbacks if f.get("value") == "handled_correctly")
        
        return {
            "total": len(feedbacks),
            "should_have_asked_count": should_have,
            "handled_correctly_count": handled_ok,
            "escalation_accuracy": handled_ok / len(feedbacks) if feedbacks else 0,
            "recommendation": "aumentar_threshold" if should_have > handled_ok else "manter",
        }

    def analyze_decision_accuracy(self) -> Dict[str, Any]:
        """Analisa precisão das decisões."""
        feedbacks = self.bank.get_user_feedback(feedback_type="decision_approval", limit=100)
        
        if not feedbacks:
            return {"status": "no_data"}
        
        correct = sum(1 for f in feedbacks if f.get("value") == "correct")
        incorrect = sum(1 for f in feedbacks if f.get("value") == "incorrect")
        
        return {
            "total": len(feedbacks),
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": correct / len(feedbacks) if feedbacks else 0,
        }

    def suggest_confidence_adjustment(self) -> Optional[Dict[str, Any]]:
        """Sugere ajuste no threshold de confiança."""
        escalation = self.analyze_escalation_patterns()
        decision = self.analyze_decision_accuracy()
        
        if escalation.get("status") == "no_data" or decision.get("status") == "no_data":
            return None
        
        if escalation.get("recommendation") == "aumentar_threshold":
            return {
                "action": "aumentar_threshold",
                "reason": "usuário indica que sistema deveria perguntar mais",
                "current_threshold": 0.5,
                "suggested_threshold": 0.6,
            }
        
        if decision.get("accuracy", 0) > 0.8:
            return {
                "action": "manter_confiança",
                "reason": "precisão alta em decisões autônomas",
                "accuracy": decision.get("accuracy"),
            }
        
        return None
