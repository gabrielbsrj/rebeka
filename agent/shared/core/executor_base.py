# shared/core/executor_base.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — base do Executor com middleware pré-execução
#
# IMPACTO GÊMEO VPS: Executa operações financeiras (paper/real)
# IMPACTO GÊMEO LOCAL: Executa ações no ambiente local do usuário
# DIFERENÇA DE COMPORTAMENTO: VPS herda para executor financeiro, Local herda para executor de ambiente

"""
Executor Base — Classe base com middleware pré-execução.

INTENÇÃO: O Executor é burro por design. Ele:
1. NUNCA raciocina sobre o que vai executar (Planejador faz isso)
2. NUNCA avalia resultados (Avaliador faz isso)
3. SEMPRE consulta erros de ambiente antes de executar
4. SEMPRE verifica limites de segurança antes de executar
5. SEMPRE registra cada execução com hash de integridade

Cada gêmeo herda e implementa o `_execute_action()` específico.

INVARIANTE: O Executor nunca raciocina sobre o que vai executar.
INVARIANTE: Toda execução passa pelo middleware pré-execução.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Erro durante execução."""
    pass


class PreExecutionCheckFailed(Exception):
    """Verificação pré-execução falhou."""
    pass


class ExecutorBase(ABC):
    """
    Classe base para executores dos gêmeos.

    INTENÇÃO: Define o contrato que todo executor deve seguir.
    O middleware pré-execução garante que nenhuma operação é executada
    sem verificações de segurança.

    Subclasses implementam `_execute_action()` com a lógica específica:
    - VPS: Operações financeiras (Polymarket API, etc.)
    - Local: Ações no ambiente do usuário (browser, apps, etc.)
    """

    def __init__(self, origin: str = "vps"):
        self._origin = origin
        self._execution_history: List[Dict] = []

    def execute(
        self,
        hypothesis: Dict[str, Any],
        evaluation: Dict[str, Any],
        security_config: Any,
    ) -> Dict[str, Any]:
        """
        Executa uma ação aprovada pelo Avaliador.

        INTENÇÃO: Este é o único ponto de entrada para execução.
        O middleware pré-execução roda ANTES de qualquer ação.

        Args:
            hypothesis: A hipótese do Planejador
            evaluation: O resultado da avaliação (deve estar aprovado)
            security_config: Instância do SecurityPhase1

        Returns:
            Resultado da execução com metadata completa.

        Raises:
            PreExecutionCheckFailed: Se alguma verificação falhou
            ExecutionError: Se a execução em si falhou
        """
        # =====================================================================
        # MIDDLEWARE PRÉ-EXECUÇÃO
        # =====================================================================

        # Check 1: Avaliação foi aprovada?
        if not evaluation.get("approved", False):
            raise PreExecutionCheckFailed(
                "Avaliação NÃO foi aprovada. O Executor nunca age sem aprovação."
            )

        action = hypothesis.get("action", {})

        # Check 2: Ação é válida?
        if not action or action.get("type") == "wait":
            logger.info("Ação é 'wait' — nada a executar.")
            return {
                "status": "skipped",
                "reason": "Ação é wait — nenhuma execução necessária.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hypothesis_id": hypothesis.get("id", "unknown"),
                "execution_type": "skipped",
                "market": action.get("market", "polymarket") if action else "polymarket",
                "asset": action.get("asset", "unknown") if action else "unknown",
                "direction": "wait",
                "amount": 0,
            }

        # Check 3: Limites de segurança
        amount = action.get("amount", 0)
        execution_type = action.get("execution_type", "paper")

        if security_config and hasattr(security_config, "check_capital_limit"):
            if not security_config.check_capital_limit(amount, execution_type):
                raise PreExecutionCheckFailed(
                    f"Operação excede limites de capital. "
                    f"Amount: {amount}, Type: {execution_type}"
                )

        # Check 4: Paper trading obrigatório?
        if security_config and hasattr(security_config, "is_paper_trading_required"):
            if security_config.is_paper_trading_required() and execution_type == "real":
                raise PreExecutionCheckFailed(
                    "Paper trading é obrigatório na Fase 1. "
                    "Operação real bloqueada."
                )

        # =====================================================================
        # EXECUÇÃO
        # =====================================================================

        logger.info(
            "Executando ação",
            extra={
                "action_type": action.get("type"),
                "execution_type": execution_type,
                "amount": amount,
                "origin": self._origin,
            },
        )

        try:
            result = self._execute_action(action, hypothesis)
        except Exception as e:
            result = {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
            logger.error(
                f"Execução falhou: {e}",
                extra={
                    "action": action,
                    "origin": self._origin,
                },
            )
            raise ExecutionError(str(e)) from e

        # =====================================================================
        # PÓS-EXECUÇÃO
        # =====================================================================

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        result["origin"] = self._origin
        result["hypothesis_id"] = hypothesis.get("id", "unknown")
        result["execution_type"] = execution_type
        result["market"] = action.get("market", "polymarket")

        self._execution_history.append(result)

        return result

    @abstractmethod
    def _execute_action(
        self, action: Dict[str, Any], hypothesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implementação específica da execução.

        INTENÇÃO: Cada gêmeo implementa sua própria lógica de execução.
        Esta é a ÚNICA coisa que o Executor faz.

        Args:
            action: Ação a executar
            hypothesis: Hipótese completa (para contexto, NÃO para raciocínio)

        Returns:
            Resultado da execução.
        """
        ...

    def get_execution_history(self) -> List[Dict]:
        """Retorna histórico de execuções desta sessão."""
        return self._execution_history.copy()


class PaperExecutor(ExecutorBase):
    """
    Executor de Paper Trading — simula operações sem capital real.

    INTENÇÃO: Na Fase 1, todas as operações são paper. Este executor
    registra tudo como se fosse real, mas sem movimentação de capital.
    """

    def __init__(self, origin: str = "vps"):
        super().__init__(origin)

    def _execute_action(
        self, action: Dict[str, Any], hypothesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simula execução paper."""
        return {
            "status": "executed",
            "execution_type": "paper",
            "action_type": action.get("type"),
            "asset": action.get("asset", "unknown"),
            "direction": action.get("type"),  # buy/sell
            "amount": action.get("amount", 0),
            "amount_fraction": action.get("amount_fraction", 0),
            "simulated_entry_price": 0.50,  # Placeholder
            "note": "Execução paper — nenhum capital real movimentado.",
        }
