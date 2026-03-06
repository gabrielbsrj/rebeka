# shared/intent/scope_learner.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Aprende os limites do conhecimento e quando escalar para o usuário
#
# IMPACTO GÊMEO VPS: Aprende limites no contexto global
# IMPACTO GÊMEO LOCAL: Aprende limites no contexto pessoal
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — escopo é universal

"""
Scope Learner — Aprende onde o conhecimento termina.

INTENÇÃO: O sistema deve saber dizer "não sei" com a mesma
exatidão que diz "sei". Este módulo:

1. Detecta quando não tem informação suficiente
2. Aprende quais domínios são mais incertos
3. Identifica quando deve escalar para o usuário
4. Reconhece padrões que são resistentes a mudança

INVARIANTE: Sempre que possível, indica nível de confiança
INVARIANTE: Quando incerto, sugere perguntar ao usuário
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class ScopeLearner:
    """
    Aprende os limites do conhecimento do sistema.

    INTENÇÃO: O sistema não deve fingir saber o que não sabe.
    Este módulo detecta incerteza e sugere quando escalar.
    """

    UNCERTAINTY_THRESHOLDS = {
        "high_confidence": 0.8,
        "medium_confidence": 0.5,
        "low_confidence": 0.3,
    }

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank
        self._uncertainty_events: List[Dict] = []
        self._escalation_history: List[Dict] = []

    def assess_decision_confidence(
        self,
        decision_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Avalia confiança do sistema em tomar uma decisão.

        Args:
            decision_type: Tipo de decisão necessária
            context: Contexto atual

        Returns:
            Avaliação de confiança com recomendações
        """
        confidence_factors = self._calculate_confidence_factors(decision_type, context)
        
        overall_confidence = self._aggregate_confidence(confidence_factors)
        
        recommendation = self._get_recommendation(overall_confidence, confidence_factors)
        
        assessment = {
            "decision_type": decision_type,
            "confidence": overall_confidence,
            "confidence_level": self._get_confidence_level(overall_confidence),
            "factors": confidence_factors,
            "recommendation": recommendation,
            "should_escalate": overall_confidence < self.UNCERTAINTY_THRESHOLDS["medium_confidence"],
            "needs_more_data": confidence_factors.get("data_availability", 0) < 0.5,
        }
        
        if assessment["should_escalate"]:
            self._record_escalation(decision_type, assessment)
        
        return assessment

    def _calculate_confidence_factors(
        self,
        decision_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calcula fatores que afetam a confiança."""
        factors = {
            "data_availability": 0.5,
            "pattern_strength": 0.5,
            "historical_accuracy": 0.5,
            "temporal_relevance": 0.5,
            "cross_validation": 0.5,
        }
        
        try:
            patterns = self.bank.get_active_patterns(domain=decision_type, min_confidence=0.3)
            if patterns:
                avg_confidence = sum(p.get("confidence", 0) for p in patterns) / len(patterns)
                factors["pattern_strength"] = avg_confidence
        except:
            pass
        
        try:
            recent_signals = self.bank.get_similar_signals(domain=decision_type, limit=10)
            if len(recent_signals) >= 5:
                factors["data_availability"] = min(1.0, len(recent_signals) / 10)
            elif len(recent_signals) == 0:
                factors["data_availability"] = 0.1
        except:
            pass
        
        try:
            stats = self.bank.get_performance_stats()
            if stats.get("total_trades", 0) > 20:
                factors["historical_accuracy"] = min(1.0, stats.get("win_rate", 0.5))
        except:
            pass
        
        if context.get("time_since_last_signal"):
            days = context.get("time_since_last_signal")
            if days < 7:
                factors["temporal_relevance"] = 1.0
            elif days < 30:
                factors["temporal_relevance"] = 0.7
            else:
                factors["temporal_relevance"] = 0.3
        
        return factors

    def _aggregate_confidence(self, factors: Dict[str, float]) -> float:
        """Agrega fatores em confiança geral."""
        weights = {
            "data_availability": 0.25,
            "pattern_strength": 0.25,
            "historical_accuracy": 0.25,
            "temporal_relevance": 0.15,
            "cross_validation": 0.10,
        }
        
        total = sum(factors.get(k, 0.5) * v for k, v in weights.items())
        return max(0.0, min(1.0, total))

    def _get_confidence_level(self, confidence: float) -> str:
        """Retorna nível textual de confiança."""
        if confidence >= self.UNCERTAINTY_THRESHOLDS["high_confidence"]:
            return "high"
        elif confidence >= self.UNCERTAINTY_THRESHOLDS["medium_confidence"]:
            return "medium"
        else:
            return "low"

    def _get_recommendation(
        self,
        confidence: float,
        factors: Dict[str, float],
    ) -> str:
        """Gera recomendação baseada na confiança."""
        if confidence >= 0.8:
            return "Agir com base na análise"
        elif confidence >= 0.6:
            return "Agir mas informar incerteza ao usuário"
        elif confidence >= 0.4:
            return "Propor ao usuário com contexto completo"
        else:
            reasons = []
            if factors.get("data_availability", 0.5) < 0.3:
                reasons.append("dados insuficientes")
            if factors.get("pattern_strength", 0.5) < 0.3:
                reasons.append("padrões fracos")
            if factors.get("historical_accuracy", 0.5) < 0.3:
                reasons.append("histórico pouco confiável")
            
            reason = ", ".join(reasons) if reasons else "incerteza elevada"
            return f"Recomenda-se perguntar ao usuário ({reason})"

    def _record_escalation(self, decision_type: str, assessment: Dict) -> None:
        """Registra necessidade de escalação."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_type": decision_type,
            "confidence": assessment["confidence"],
            "factors": assessment.get("factors", {}),
        }
        self._escalation_history.append(event)
        logger.info(f"Escalação registrada: {decision_type} (confiança: {assessment['confidence']:.2f})")

    def detect_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        Detecta lacunas de conhecimento do sistema.

        Returns:
            Lista de áreas com conhecimento insuficiente
        """
        gaps = []
        
        domains = ["trading", "polymarket", "macro", "geopolitics", "commodities"]
        
        for domain in domains:
            try:
                signals = self.bank.get_similar_signals(domain=domain, limit=5)
                patterns = self.bank.get_active_patterns(domain=domain, min_confidence=0.3)
                
                signal_count = len(signals)
                pattern_count = len(patterns)
                
                gap_severity = 1.0
                if signal_count >= 10:
                    gap_severity -= 0.4
                if pattern_count >= 3:
                    gap_severity -= 0.3
                
                if gap_severity > 0.3:
                    gaps.append({
                        "domain": domain,
                        "severity": gap_severity,
                        "signals_count": signal_count,
                        "patterns_count": pattern_count,
                        "recommendation": "Coletar mais dados ou perguntar ao usuário",
                    })
                    
            except Exception as e:
                logger.debug(f"Erro ao verificar domínio {domain}: {e}")
        
        return sorted(gaps, key=lambda x: x["severity"], reverse=True)

    def should_defer_to_user(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determina se deve deferir para o usuário.

        Args:
            context: Contexto da decisão

        Returns:
            (defer, reason)
        """
        assessment = self.assess_decision_confidence(
            decision_type=context.get("domain", "general"),
            context=context,
        )
        
        if assessment["confidence"] < 0.3:
            return True, "confiança muito baixa"
        
        if assessment["needs_more_data"]:
            return True, "dados insuficientes"
        
        if context.get("user_expertise") == "high" and assessment["confidence"] < 0.7:
            return True, "usuário mais capaz de decidir"
        
        if context.get("reversibility") == "high" and assessment["confidence"] < 0.5:
            return True, "decisão reversível - usuário pode preferir"
        
        return False, "sistema confiante"

    def get_uncertainty_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de incertezas do sistema.
        """
        gaps = self.detect_knowledge_gaps()
        
        escalation_count = len(self._escalation_history)
        
        recent_escalations = [
            e for e in self._escalation_history
            if datetime.fromisoformat(e["timestamp"]) > datetime.now(timezone.utc) - timedelta(days=7)
        ]
        
        return {
            "knowledge_gaps": gaps,
            "total_escalations": escalation_count,
            "recent_escalations_7d": len(recent_escalations),
            "avg_confidence_when_escalating": (
                sum(e["confidence"] for e in recent_escalations) / len(recent_escalations)
                if recent_escalations else 0
            ),
            "domains_needing_attention": [g["domain"] for g in gaps[:3]],
        }


class HorizonRealismTracker:
    """
    Rastrea se horizontes de crescimento são realistas.

    INTENÇÃO: O sistema deve saber quando um horizonte declarado
    é irrealista baseado em dados históricos.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def assess_horizon_realism(
        self,
        target_id: str,
    ) -> Dict[str, Any]:
        """
        Avalia se um horizonte é realista.

        Args:
            target_id: ID do horizonte de crescimento

        Returns:
            Avaliação de realismo
        """
        targets = self.bank.get_active_growth_targets()
        target = next((t for t in targets if t["id"] == target_id), None)

        if not target:
            return {"status": "not_found"}

        history = self.bank.get_growth_progress_history(target_id)
        
        if not history:
            return {
                "status": "insufficient_data",
                "target_id": target_id,
                "realism_score": 0.5,
                "recommendation": "Aguardar mais dados",
            }

        trend = history[0].get("trend", "unknown")
        distance = history[0].get("distance", 1.0)
        
        weeks_tracked = len(history)
        
        expected_improvement_per_week = 0.1
        
        expected_distance = max(0.0, 1.0 - (weeks_tracked * expected_improvement_per_week))
        
        realism_score = 1.0 - abs(distance - expected_distance)
        realism_score = max(0.0, min(1.0, realism_score))
        
        assessment = "realista" if realism_score > 0.5 else "otimista"
        
        if realism_score < 0.3:
            recommendation = (
                "Horizonte muito otimista. Considere estender prazo ou "
                "redefinir métricas mais alcançáveis."
            )
        elif realism_score < 0.5:
            recommendation = "Progresso mais lento que esperado. Manter monitoramento."
        else:
            recommendation = "Horizonte realista. Continuar monitoramento."
        
        return {
            "status": "analyzed",
            "target_id": target_id,
            "domain": target.get("domain"),
            "weeks_tracked": weeks_tracked,
            "current_distance": distance,
            "expected_distance": expected_distance,
            "realism_score": realism_score,
            "assessment": assessment,
            "recommendation": recommendation,
            "should_suggest_redefinition": realism_score < 0.3,
        }

    def get_all_horizons_realism(self) -> List[Dict[str, Any]]:
        """Avalia realismo de todos os horizontes."""
        targets = self.bank.get_active_growth_targets()
        
        assessments = []
        for target in targets:
            assessment = self.assess_horizon_realism(target["id"])
            assessments.append(assessment)
        
        return assessments


class PatternResistanceDetector:
    """
    Detecta padrões comportamentais resistentes a mudança.

    INTENÇÃO: Alguns padrões são muito difíceis de mudar.
    Este módulo detecta quando uma estratégia diferente é necessária.
    """

    RESISTANCE_THRESHOLDS = {
        "high": 0.8,
        "medium": 0.5,
    }

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def assess_pattern_resistance(
        self,
        pattern_type: str,
    ) -> Dict[str, Any]:
        """
        Avalia resistência de um padrão a mudanças.

        Args:
            pattern_type: Tipo de padrão comportamental

        Returns:
            Avaliação de resistência
        """
        patterns = self.bank.get_behavioral_patterns(min_confidence=0.3)
        
        matching = [p for p in patterns if p.get("type") == pattern_type]
        
        if not matching:
            return {
                "status": "not_found",
                "pattern_type": pattern_type,
            }
        
        pattern = matching[0]
        
        friction_history = self.bank.get_friction_history(category=pattern_type, limit=20)
        
        friction_count = len(friction_history)
        
        if friction_count == 0:
            resistance_score = 0.5
            resistance_level = "unknown"
        else:
            receptivo_count = sum(1 for f in friction_history if f.get("user_response") == "receptivo")
            effectiveness = receptivo_count / friction_count
            
            if effectiveness > 0.6:
                resistance_score = 0.3
                resistance_level = "low"
            elif effectiveness > 0.3:
                resistance_score = 0.6
                resistance_level = "medium"
            else:
                resistance_score = 0.9
                resistance_level = "high"
        
        confirmation_count = pattern.get("confirmation_count", 0)
        if confirmation_count > 10:
            resistance_score += 0.1
        if confirmation_count > 20:
            resistance_score += 0.1
        
        resistance_score = min(1.0, resistance_score)
        
        strategy = self._suggest_strategy(resistance_level, pattern_type)
        
        return {
            "status": "analyzed",
            "pattern_type": pattern_type,
            "resistance_score": resistance_score,
            "resistance_level": resistance_level,
            "friction_attempts": friction_count,
            "effectiveness_rate": 1 - resistance_score,
            "strategy": strategy,
            "should_try_different_approach": resistance_score > self.RESISTANCE_THRESHOLDS["medium"],
        }

    def _suggest_strategy(self, resistance_level: str, pattern_type: str) -> str:
        """Sugere estratégia baseada no nível de resistência."""
        strategies = {
            "low": "Continuar com fricção padrão - está funcionando",
            "medium": "Ajustar tom para mais suave ou esperar melhor momento",
            "high": "Mudar abordagem: focar em ambiente em vez de comportamento",
            "unknown": "Experimentar fricção leve primeiro",
        }
        
        return strategies.get(resistance_level, "Manter monitoramento")

    def get_resistant_patterns(self) -> List[Dict[str, Any]]:
        """Retorna padrões resistentes a mudança."""
        patterns = self.bank.get_behavioral_patterns(min_confidence=0.5)
        
        resistant = []
        for pattern in patterns:
            assessment = self.assess_pattern_resistance(pattern.get("type"))
            if assessment.get("should_try_different_approach"):
                resistant.append(assessment)
        
        return sorted(resistant, key=lambda x: x["resistance_score"], reverse=True)
