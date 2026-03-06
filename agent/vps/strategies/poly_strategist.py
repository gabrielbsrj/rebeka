import logging
import asyncio
import os
from typing import Dict, Any

from shared.core.planner import Planner
from shared.core.evaluator import Evaluator
from shared.core.security_phase1 import SecurityPhase1
from vps.executor_financial import FinancialExecutor

logger = logging.getLogger(__name__)

class PolymarketStrategist:
    """
    Estrategista financeiro. Consome sinais do Polymarket Monitor e decide se deve fazer copy trade.
    Usa o Planner para raciocinar sobre as odds e o Evaluator para aprovar o movimento.
    """
    def __init__(self, bank, chat_manager):
        self.bank = bank
        self.chat_manager = chat_manager
        
        api_key = os.getenv("MOONSHOT_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        model = "moonshot/kimi-k2.5"
        
        self.planner = Planner(model=model, api_key=api_key, api_base=api_base)
        self.evaluator = Evaluator(model=model, api_key=api_key, api_base=api_base)
        self.executor = FinancialExecutor(origin="vps")
        self.security = SecurityPhase1()

    async def evaluate_whale_signal(self, signal: Dict[str, Any]):
        """Avalia um sinal de movimentação de baleia detectado pelo monitor."""
        title = signal.get("title", "")
        content = signal.get("content", "")
        metadata = signal.get("metadata", {})
        
        logger.info(f"Analisando sinal de Copy Trade: {title}")
        
        logger.info("Enviando sinal para o Planner raciocinar internamente...")
        
        # O planner processa o sinal junto com as intenções e performance
        hypothesis_result = self.planner.generate_hypothesis(
            signals=[signal],
            active_patterns=[],
            performance_stats={"win_rate": 0.50, "total_trades": 0, "total_pnl": 0.0},
            recent_errors=[],
            twin_perspective=None,
            intent_model={
                "polymarket_copy_trading": "Seu papel é avaliar movimentações institucionais. Avalie se o Whale Alert justica copy trade paper de $50."
            },
            domain="finance"
        )
        
        if not hypothesis_result:
            logger.info("Planner não encontrou raciocínio forte suficiente para agir.")
            return

        # Objeto dataclass HypothesisResult possui atributos como reasoning, action etc.
        hypothesis = {
            "id": "hypo_copy_" + str(hash(title)),
            "reasoning": hypothesis_result.reasoning,
            "action": hypothesis_result.action,
            "confidence": hypothesis_result.confidence_calibrated
        }
        
        reasoning = hypothesis_result.reasoning
        action = hypothesis_result.action
        
        # 2. Avaliador julga a racionalidade da hipótese
        logger.info("Enviando para o Avaliador julgar o risco/recompensa...")
        
        evaluation_result = self.evaluator.evaluate_hypothesis(
            hypothesis=hypothesis,
            available_signals=[signal],
            performance_stats={"win_rate": 0.50},
            intent_model={"polymarket_copy_trading": "Proteja o capital. Não siga cegamente baleias se a odd não fizer sentido matemático."}
        )
        
        # O retorno é um dataclass EvaluationResult
        evaluation = {
            "approved": evaluation_result.approved,
            "reasoning": evaluation_result.overall_reasoning
        }
        
        approved = evaluation.get("approved", False)
        eval_reason = evaluation.get("reasoning", "")
        
        # Notificar chat
        emoji = "🎯" if approved else "🤔"
        msg = (
            f"{emoji} **Avaliação de Copy Trade**\n"
            f"Mercado: {metadata.get('event_slug', 'Desconhecido')}\n\n"
            f"**Meu Raciocínio (Planejador):**\n{reasoning}\n\n"
            f"**Julgamento de Risco (Avaliador):**\n{eval_reason}\n\n"
            f"**Veredito:** {'Aprovado para Paper Trade ✅' if approved else 'Rejeitado por segurança ❌'}"
        )
        self.chat_manager.push_insight(msg)
        
        # 3. Executar se for aprovado e for trade
        if approved and action.get("type", "") == "trade":
            logger.info("Iniciando Execução de Paper Trade via FinancialExecutor...")
            
            # Forçar compliance Paper Trade para o teste
            action["execution_type"] = "paper"
            if "market_id" not in action:
                action["market_id"] = metadata.get("main_market_id", "market_placeholder_123")
            if "direction" not in action:
                action["direction"] = "YES" # Assume o fluxo detectado
                
            try:
                res = self.executor.execute(hypothesis=hypothesis, evaluation=evaluation, security_config=self.security)
                exec_msg = (
                    f"💸 **Trade Executado**\n"
                    f"Ativo: {res.get('market_id')}\n"
                    f"Direção: {res.get('direction')} | Valor Simulado: ${res.get('amount')}\n"
                    f"Tipo: {res.get('execution_type').upper()}\n"
                    f"Status: {res.get('status')}"
                )
                self.chat_manager.push_insight(exec_msg)
            except Exception as e:
                self.chat_manager.push_insight(f"❌ Erro na execução simulada: {str(e)}")
        else:
            logger.info("Trade ignorado: Reprovado pelo Avaliador ou decisão do Planner foi de não entrar.")
