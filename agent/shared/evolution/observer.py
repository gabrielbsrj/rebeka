# agent/shared/evolution/observer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — monitor de meta-performance

import logging
from typing import Dict, Any, List, Optional
from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)

class Observer:
    """
    Observer — O olho que vê a si mesmo.
    
    INTENÇÃO: Monitora a performance do próprio agente.
    Identifica quando o Planejador está errando sistematicamente 
    ou quando o Avaliador está sendo muito permissivo/rígido.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank
        from shared.core.config_loader import get_model_config
        self.config = get_model_config("observer")

    def analyze_performance(self, domain: str = "finance") -> Dict[str, Any]:
        """
        Analisa o histórico real de execuções para detectar desvios de performance
        e violações de invariantes de confiança.
        """
        logger.info(f"Observer analisando performance em: {domain}")
        
        # 1. Obter estatísticas gerais (Paper Trading)
        stats = self.bank.get_performance_stats(execution_type="paper")
        
        # 2. Calcular Erro de Calibração de Confiança (Invariante L81)
        # O prompt exige: reported_confidence <= historical_success_rate + 0.10
        win_rate = stats["win_rate"]
        
        # Vamos buscar as últimas 20 hipóteses para ver a confiança média reportada
        hyps = self.bank.get_recent_hypotheses(status="closed", limit=20)
        if hyps:
            avg_reported_confidence = sum(h["confidence"] for h in hyps) / len(hyps)
        else:
            avg_reported_confidence = 0.0

        calibration_error = avg_reported_confidence - win_rate
        
        metrics = {
            "domain": domain,
            "win_rate": win_rate,
            "total_trades": stats["total_trades"],
            "avg_reported_confidence": avg_reported_confidence,
            "confidence_calibration_error": calibration_error,
            "violation_detected": calibration_error > 0.10,
            "systemic_error_detected": win_rate < 0.50 and stats["total_trades"] > 10
        }
        
        return metrics

    def question_reasoning(self, metrics: Dict[str, Any]) -> str:
        """
        Fase de QUESTIONAMENTO via LLM.
        """
        from litellm import completion
        import os

        api_key = os.getenv("MOONSHOT_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        
        prompt = f"""
        Você é o módulo 'Observer' da Rebeka. Sua função é QUESTIONAR antes de agir.
        
        Métricas Atuais:
        - Domínio: {metrics['domain']}
        - Win Rate: {metrics['win_rate']:.2f}
        - Confiança Média Reportada: {metrics['avg_reported_confidence']:.2f}
        - Erro de Calibração: {metrics['confidence_calibration_error']:.2f}
        
        O plano de transcendência exige que não sejamos apenas 'consertadores', mas 'compreendedores'.
        Identifique o 'POR QUÊ' por trás desses números. Se o erro de calibração for alto (>0.10),
        questione se o modelo está sendo instrumentalmente otimista.
        """
        
        try:
            response = completion(
                model=self.config["model"],
                messages=[{"role": "user", "content": prompt}],
                api_key=api_key,
                api_base=api_base,
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )
            question = response.choices[0].message.content
            logger.info(f"Observer Questionamento: {question}")
            return question
        except Exception as e:
            logger.error(f"Erro no Observer LLM: {e}")
            return f"Erro ao questionar via LLM: {str(e)}"
