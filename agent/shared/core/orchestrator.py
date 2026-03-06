# shared/core/orchestrator.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v2 — Integração com IntentEngine e módulos de intenção
#
# IMPACTO GÊMEO VPS: Coordena módulo de intenção no contexto VPS
# IMPACTO GÊMEO LOCAL: Coordena módulo de intenção no contexto LOCAL
# DIFERENÇA DE COMPORTAMENTO: Injeta contexto diferente (global vs pessoal)

import logging
import time
import asyncio
from typing import Optional, Dict, Any

from shared.database.causal_bank import CausalBank
from shared.core.planner import Planner
from shared.core.evaluator import Evaluator
from shared.core.executor_base import ExecutorBase
from shared.core.security_phase1 import SecurityPhase1
from shared.communication.notifier import Notifier
from shared.intent.intent_engine import IntentEngine

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    O Orquestrador é o coração do sistema.
    Coordenador do ciclo Sense-Think-Act com Intent Engine integrado.
    """

    def __init__(
        self,
        bank: CausalBank,
        planner: Planner,
        evaluator: Evaluator,
        executor: ExecutorBase,
        security: SecurityPhase1,
        notifier: Notifier,
        interval_seconds: int = 60,
        origin: str = "vps"
    ):
        self.bank = bank
        self.planner = planner
        self.evaluator = evaluator
        self.executor = executor
        self.security = security
        self.notifier = notifier
        self.interval_seconds = interval_seconds
        self.is_running = False
        self.origin = origin
        
        self.intent_engine = IntentEngine(bank, origin=origin)

    async def run_once(self):
        """Executa um ciclo completo do agente."""
        logger.info("Iniciando ciclo do orquestrador...")

        try:
            self.intent_engine.initialize()
            
            intent_action = self.intent_engine.get_next_action()
            if intent_action:
                await self._handle_intent_action(intent_action)

            recent_signals = self.bank.get_similar_signals(domain="polymarket", limit=5)
            active_patterns = self.bank.get_active_patterns(domain="polymarket", min_confidence=0.5)
            performance_stats = self.bank.get_performance_stats()
            
            hypothesis_data = self.planner.generate_hypothesis(
                signals=recent_signals,
                active_patterns=active_patterns,
                performance_stats=performance_stats,
                domain="polymarket"
            )
            
            if not hypothesis_data:
                logger.info("Nenhuma hipótese gerada neste ciclo.")
                return

            hypothesis_dict = {
                "content": hypothesis_data.reasoning,
                "reasoning": hypothesis_data.reasoning,
                "uncertainty_acknowledged": hypothesis_data.uncertainty_acknowledged,
                "signals_used": hypothesis_data.signals_used,
                "predicted_movement": hypothesis_data.predicted_movement,
                "action": hypothesis_data.action,
                "confidence_calibrated": hypothesis_data.confidence_calibrated,
            }
            hypothesis_id = self.bank.insert_hypothesis(hypothesis_dict)
            hypothesis_dict["id"] = hypothesis_id
            logger.info(f"Hipótese gerada e registrada: {hypothesis_id}")

            evaluation_result = self.evaluator.evaluate_hypothesis(
                hypothesis=hypothesis_dict,
                available_signals=recent_signals,
                performance_stats=performance_stats,
            )
            
            evaluation_data = {
                "hypothesis_id": hypothesis_id,
                "reasoning_analysis": evaluation_result.overall_reasoning,
                "lessons_learned": evaluation_result.layer1_reasoning,
                "hypothesis_correct": evaluation_result.approved
            }
            self.bank.insert_evaluation(evaluation_data)

            if not evaluation_result.approved:
                logger.warning(f"Hipótese {hypothesis_id} rejeitada pelo Avaliador.")
                self.notifier.notify(
                    title="Hipótese Rejeitada",
                    message=f"ID: {hypothesis_id}\nMotivo: {evaluation_result.overall_reasoning[:200]}...",
                )
                return

            logger.info(f"Hipótese {hypothesis_id} aprovada. Enviando para execução.")
            
            execution_data = {
                "hypothesis_id": hypothesis_id,
                "execution_type": "paper" if self.security.is_paper_trading_required() else "real",
                "market": hypothesis_data.action.get("market", "polymarket"),
                "asset": hypothesis_data.action.get("asset", "unknown"),
                "direction": hypothesis_data.action.get("direction", "unknown"),
                "amount": hypothesis_data.action.get("amount", 0.0)
            }

            try:
                evaluation_dict = {
                    "approved": evaluation_result.approved,
                    "overall_reasoning": evaluation_result.overall_reasoning,
                    "layer1_consistent": evaluation_result.layer1_consistent,
                    "layer2_aligned": evaluation_result.layer2_aligned,
                    "layer3_no_instrumental": evaluation_result.layer3_no_instrumental_behavior,
                }
                
                result = self.executor.execute(
                    hypothesis=hypothesis_dict,
                    evaluation=evaluation_dict,
                    security_config=self.security,
                )
                self.bank.insert_execution(result)
                
                self.pattern_detector_update_from_execution(result)
                
                growth_metrics = self._extract_growth_metrics(result)
                if growth_metrics:
                    self.intent_engine.update_growth_progress(growth_metrics)
                
                self.notifier.notify(
                    title="Operação Executada",
                    message=f"Hipótese: {hypothesis_id}\nTipo: {result.get('execution_type')}\nAtivo: {result.get('asset')}",
                )
            except Exception as e:
                logger.error(f"Erro na execução da hipótese {hypothesis_id}: {str(e)}")
                self.bank.insert_environment_error({
                    "error_type": "execution_failed",
                    "description": str(e),
                    "context": execution_data
                })

        except Exception as e:
            logger.error(f"Erro crítico no loop do orquestrador: {str(e)}", exc_info=True)

    async def _handle_intent_action(self, action: Dict[str, Any]) -> None:
        """Processa ação recomendada pelo Intent Engine."""
        action_type = action.get("type")
        
        if action_type == "friction":
            friction_data = action.get("data", {})
            message = friction_data.get("message", "")
            
            self.notifier.notify(
                title="Fricção Intencional",
                message=message,
            )
            logger.info(f"Fricção aplicada: {friction_data.get('level')}")
        
        elif action_type == "pattern_alert":
            patterns = action.get("patterns", [])
            logger.info(f"Padrões limitantes detectados: {len(patterns)}")
        
        elif action_type == "growth_checkin":
            target = action.get("target", {})
            logger.info(f"Check-in de crescimento: {target.get('domain')}")

    def pattern_detector_update_from_execution(self, execution_data: Dict[str, Any]) -> None:
        """Atualiza detector de padrões a partir de execução."""
        try:
            detected = self.intent_engine.pattern_detector.detect_from_execution(execution_data)
            for pattern in detected:
                logger.debug(f"Padrão detectado: {pattern.get('type')}")
        except Exception as e:
            logger.debug(f"Erro ao atualizar padrões: {e}")

    def _extract_growth_metrics(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai métricas de crescimento de uma execução."""
        return {
            "trades_executed": 1,
            "result": execution_data.get("result", 0),
            "has_stop_loss": execution_data.get("has_stop_loss", False),
        }

    async def run_forever(self):
        """Inicia o loop contínuo."""
        self.is_running = True
        logger.info(f"Orquestrador iniciado (intervalo: {self.interval_seconds}s)")
        
        while self.is_running:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        """Para o orquestrador."""
        self.is_running = False
        logger.info("Parando orquestrador...")
