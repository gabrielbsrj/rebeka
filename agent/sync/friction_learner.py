# sync/friction_learner.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Meta-aprendizado sobre fricções efetivas
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Aprende quais fricções funcionam para este usuário
# DIFERENÇA DE COMPORTAMENTO: Cada usuário tem perfil de fricção único

"""
Friction Learner — Meta-aprendizado sobre fricções efetivas.

INTENÇÃO: O sistema aprende com o histórico de fricções:
- Quais níveis funcionam melhor (leve/moderada/direta)
- Qual timing é mais eficaz
- Quais padrões respondem melhor a fricção
- Quando o usuário está receptivo

Este módulo:
1. Analisa histórico de fricções e respostas
2. Detecta padrões de receptividade
3. Sugere ajustes de tom/timing
4. Prevê receptividade futura
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class FrictionLearner:
    """
    Aprende com resultados de fricção para otimizar futuras abordagens.

    INTENÇÃO: Cada usuário é único. Este módulo constrói um perfil
    de como este usuário específico responde a diferentes tipos de fricção.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def analyze_effectiveness(self) -> Dict[str, Any]:
        """
        Analisa efetividade histórica das fricções.

        Returns:
            Análise completa de efetividade
        """
        frictions = self.bank.get_friction_history(limit=100)

        if not frictions:
            return {
                "status": "no_data",
                "total_frictions": 0,
            }

        total = len(frictions)
        
        by_response = {}
        by_level = {}
        by_category = {}
        
        for f in frictions:
            response = f.get("user_response", "unknown")
            level = f.get("level", "unknown")
            category = f.get("category", "unknown")
            
            if response not in by_response:
                by_response[response] = 0
            by_response[response] += 1
            
            if level not in by_level:
                by_level[level] = {"total": 0, "receptivo": 0}
            by_level[level]["total"] += 1
            if response == "receptivo":
                by_level[level]["receptivo"] += 1
            
            if category not in by_category:
                by_category[category] = {"total": 0, "receptivo": 0}
            by_category[category]["total"] += 1
            if response == "receptivo":
                by_category[category]["receptivo"] += 1

        receptivo_rate = by_response.get("receptivo", 0) / total
        defensivo_rate = by_response.get("defensivo", 0) / total
        
        best_level = None
        best_rate = 0
        for level, data in by_level.items():
            if data["total"] >= 3:
                rate = data["receptivo"] / data["total"]
                if rate > best_rate:
                    best_rate = rate
                    best_level = level

        return {
            "status": "analyzed",
            "total_frictions": total,
            "response_distribution": by_response,
            "receptivo_rate": receptivo_rate,
            "defensivo_rate": defensivo_rate,
            "best_level": best_level,
            "best_level_rate": best_rate,
            "by_level": by_level,
            "by_category": by_category,
        }

    def predict_receptivity(
        self,
        pattern_type: Optional[str] = None,
        time_since_last_friction: Optional[int] = None,
    ) -> float:
        """
        Prediz receptividade do usuário a fricção futura.

        Args:
            pattern_type: Tipo de padrão que motivaria a fricção
            time_since_last_friction: Dias desde última fricção

        Returns:
            Score de receptividade previsto (0.0 a 1.0)
        """
        analysis = self.analyze_effectiveness()
        
        if analysis.get("status") == "no_data":
            return 0.5
        
        base_receptivity = analysis.get("receptivo_rate", 0.5)
        
        adjustment = 0.0
        
        if time_since_last_friction is not None:
            if time_since_last_friction < 14:
                adjustment -= 0.2
            elif time_since_last_friction >= 30:
                adjustment += 0.1
            elif time_since_last_friction >= 60:
                adjustment += 0.2
        
        if pattern_type:
            by_category = analysis.get("by_category", {})
            category_data = by_category.get(pattern_type, {})
            
            if category_data.get("total", 0) >= 2:
                category_rate = category_data["receptivo"] / category_data["total"]
                adjustment += (category_rate - base_receptivity)
        
        receptivity = max(0.0, min(1.0, base_receptivity + adjustment))
        
        return receptivity

    def suggest_friction_parameters(
        self,
        pattern_type: str,
        pattern_confidence: float,
    ) -> Dict[str, Any]:
        """
        Sugere parâmetros otimizados para fricção.

        Args:
            pattern_type: Tipo de padrão
            pattern_confidence: Confiança no padrão

        Returns:
            Parâmetros sugeridos (level, timing, message_style)
        """
        analysis = self.analyze_effectiveness()
        
        if analysis.get("status") == "no_data":
            return {
                "level": "moderada",
                "timing": "agora",
                "message_style": "pergunta",
                "confidence": 0.5,
            }
        
        best_level = analysis.get("best_level", "moderada")
        
        by_category = analysis.get("by_category", {})
        category_data = by_category.get(pattern_type, {})
        
        if category_data.get("total", 0) >= 2:
            category_rate = category_data["receptivo"] / category_data["total"]
            
            if category_rate > 0.7:
                level = best_level
            elif category_rate > 0.4:
                level = "moderada"
            else:
                level = "leve"
        else:
            level = best_level or "moderada"
        
        if pattern_confidence > 0.8 and level == "leve":
            level = "moderada"
        
        receptivity = self.predict_receptivity(pattern_type=pattern_type)
        
        if receptivity < 0.4:
            timing = "mais_tarde"
            message_style = "pergunta_indireta"
        elif receptivity < 0.6:
            timing = "agora"
            message_style = "pergunta"
        else:
            timing = "agora"
            message_style = "observacao"
        
        return {
            "level": level,
            "timing": timing,
            "message_style": message_style,
            "predicted_receptivity": receptivity,
            "confidence": min(0.9, analysis.get("best_level_rate", 0.5) + 0.2),
        }

    def detect_receptivity_patterns(self) -> Dict[str, Any]:
        """
        Detecta padrões de receptividade ao longo do tempo.

        Returns:
            Análise de padrões temporais
        """
        frictions = self.bank.get_friction_history(limit=100)
        
        if len(frictions) < 5:
            return {"status": "insufficient_data"}
        
        recent_frictions = [
            f for f in frictions
            if self._parse_date(f.get("created_at")) > datetime.now(timezone.utc) - timedelta(days=30)
        ]
        
        older_frictions = [
            f for f in frictions
            if self._parse_date(f.get("created_at")) <= datetime.now(timezone.utc) - timedelta(days=30)
        ]
        
        recent_receptivo = sum(1 for f in recent_frictions if f.get("user_response") == "receptivo")
        older_receptivo = sum(1 for f in older_frictions if f.get("user_response") == "receptivo")
        
        recent_rate = recent_receptivo / len(recent_frictions) if recent_frictions else 0
        older_rate = older_receptivo / len(older_frictions) if older_frictions else 0
        
        trend = "stable"
        if recent_rate > older_rate * 1.3:
            trend = "improving"
        elif recent_rate < older_rate * 0.7:
            trend = "declining"
        
        day_of_week_pattern = {}
        for f in frictions:
            created = self._parse_date(f.get("created_at"))
            if created:
                dow = created.weekday()
                response = f.get("user_response")
                
                if dow not in day_of_week_pattern:
                    day_of_week_pattern[dow] = {"total": 0, "receptivo": 0}
                
                day_of_week_pattern[dow]["total"] += 1
                if response == "receptivo":
                    day_of_week_pattern[dow]["receptivo"] += 1
        
        best_day = None
        best_day_rate = 0
        for dow, data in day_of_week_pattern.items():
            if data["total"] >= 2:
                rate = data["receptivo"] / data["total"]
                if rate > best_day_rate:
                    best_day_rate = rate
                    best_day = dow
        
        return {
            "trend": trend,
            "recent_rate": recent_rate,
            "older_rate": older_rate,
            "best_day_of_week": best_day,
            "best_day_rate": best_day_rate,
            "recommendation": self._generate_recommendation(trend, best_day),
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse data ISO para datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except:
            return None

    def _generate_recommendation(self, trend: str, best_day: Optional[int]) -> str:
        """Gera recomendação baseada nos padrões."""
        recommendations = []
        
        if trend == "declining":
            recommendations.append("Considere reduzir frequência de fricção")
        elif trend == "improving":
            recommendations.append("Usuário está mais receptivo — pode manter frequência")
        
        if best_day is not None:
            days = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
            recommendations.append(f"Melhor dia para fricção: {days[best_day]}")
        
        return ". ".join(recommendations) if recommendations else "Manter abordagem atual"

    def get_optimization_suggestions(self) -> Dict[str, Any]:
        """
        Retorna sugestões de otimização para o sistema de fricção.

        Returns:
            Sugestões baseadas em análise completa
        """
        effectiveness = self.analyze_effectiveness()
        patterns = self.detect_receptivity_patterns()
        
        suggestions = []
        
        if effectiveness.get("best_level"):
            suggestions.append({
                "type": "level",
                "current": effectiveness.get("best_level"),
                "reason": "maior taxa de receptividade",
            })
        
        if patterns.get("trend") == "declining":
            suggestions.append({
                "type": "frequency",
                "action": "reduzir",
                "reason": "receptividade em declínio",
            })
        
        if patterns.get("best_day_of_week") is not None:
            suggestions.append({
                "type": "timing",
                "day": patterns["best_day_of_week"],
                "reason": "melhor dia historicamente",
            })
        
        receptivity = self.predict_receptivity()
        if receptivity < 0.4:
            suggestions.append({
                "type": "approach",
                "action": "tom_mais_suave",
                "reason": f"receptividade prevista baixa ({receptivity:.0%})",
            })
        
        return {
            "suggestions": suggestions,
            "current_receptivity": receptivity,
            "effectiveness_summary": {
                "total": effectiveness.get("total_frictions", 0),
                "receptivo_rate": effectiveness.get("receptivo_rate", 0),
            },
        }
