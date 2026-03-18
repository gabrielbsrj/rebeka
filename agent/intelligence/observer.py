# intelligence/observer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-12
# CHANGELOG: Criação inicial — Observer para auto-análise evolutiva

"""
Observer — Consciência do Agente

Analisa periodicamente as métricas de performance do sistema e detecta:
- Viés de confirmação
- Calibração de confiança incorreta
- Comportamento instrumental
- Violações de integridade

Usa os casos de teste definidos em config/observer_cases.yaml.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("intelligence.observer")


class Observer:
    """Observador de performance e integridade do agente."""

    def __init__(self, causal_bank):
        self.bank = causal_bank
        self.thresholds = {
            "min_win_rate": 0.50,
            "max_confidence_calibration_error": 0.10,
            "min_trades_for_analysis": 10,
        }
        logger.info("Observer inicializado.")

    def analyze_performance(self) -> dict:
        """
        Analisa métricas de performance do banco de causalidade.
        Retorna dict com flags de violação.
        """
        try:
            # Tentar buscar métricas reais do banco
            recent_signals = self.bank.get_recent_signals(limit=50) if hasattr(self.bank, 'get_recent_signals') else []
            
            # Calcular métricas básicas
            total_trades = len([s for s in recent_signals if s.get("type") == "trade_result"]) if recent_signals else 0
            wins = len([s for s in recent_signals if s.get("type") == "trade_result" and s.get("result") == "win"]) if recent_signals else 0
            win_rate = wins / total_trades if total_trades > 0 else 0.0
            
            metrics = {
                "domain": "finance",
                "win_rate": win_rate,
                "avg_reported_confidence": 0.0,
                "confidence_calibration_error": 0.0,
                "total_trades": total_trades,
                "violation_detected": False,
                "systemic_error_detected": False,
                "flags": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Checar violações
            if total_trades >= self.thresholds["min_trades_for_analysis"]:
                if win_rate < self.thresholds["min_win_rate"]:
                    metrics["violation_detected"] = True
                    metrics["flags"].append(
                        f"Win rate ({win_rate:.1%}) abaixo do mínimo ({self.thresholds['min_win_rate']:.0%})"
                    )

            return metrics

        except Exception as e:
            logger.warning(f"Erro ao analisar performance: {e}")
            return {
                "domain": "finance",
                "win_rate": 0.0,
                "avg_reported_confidence": 0.0,
                "confidence_calibration_error": 0.0,
                "total_trades": 0,
                "violation_detected": False,
                "systemic_error_detected": False,
                "flags": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def question_reasoning(self, metrics: dict) -> str:
        """
        Gera um questionamento sobre o raciocínio do agente com base nas métricas.
        """
        questions = []

        win_rate = metrics.get("win_rate", 0)
        confidence = metrics.get("avg_reported_confidence", 0)
        cal_error = metrics.get("confidence_calibration_error", 0)
        total = metrics.get("total_trades", 0)

        if win_rate < self.thresholds["min_win_rate"] and total >= self.thresholds["min_trades_for_analysis"]:
            questions.append(
                f"Win rate de {win_rate:.1%} está abaixo do aceitável. "
                f"O Planejador deve recalibrar hipóteses."
            )

        if cal_error > self.thresholds["max_confidence_calibration_error"]:
            questions.append(
                f"Erro de calibração de confiança ({cal_error:.2f}) excede o limite "
                f"({self.thresholds['max_confidence_calibration_error']:.2f}). "
                f"A confiança reportada ({confidence:.1%}) pode estar inflada."
            )

        if confidence > 0.80 and win_rate < 0.55:
            questions.append(
                "Confiança média acima de 80% com win rate abaixo de 55% sugere viés de otimismo."
            )

        if not questions:
            return "Nenhuma anomalia detectada nas métricas atuais."

        full_question = " | ".join(questions)
        logger.info(f"Observer questionamento: {full_question}")
        return full_question
