# vps/executor_financial.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — executor financeiro focado em Polymarket
#
# IMPACTO GÊMEO VPS: Ponto focal financeiro. Lê odds reais e opera no mercado
# IMPACTO GÊMEO LOCAL: Nenhum direto (mas resultados sincronizam para o banco local)

"""
Financial Executor — Braço direito da Rebeka no mercado financeiro (Polymarket).

INTENÇÃO: O Executor Financeiro herda as restrições base (ExecutorBase) e 
implementa a interação com o mundo cripto (Polymarket).
Na Fase 1, opera majoritariamente no papel (paper trading) mas os dados vêm 
de mercados abertos reais.
"""

import logging
import httpx
from typing import Dict, Any, Optional

from shared.core.executor_base import ExecutorBase, ExecutionError

logger = logging.getLogger(__name__)

class FinancialExecutor(ExecutorBase):
    """
    Executor Financeiro para o Gêmeo VPS.
    
    INTENÇÃO: Interagir com Polymarket (e no futuro Hyperliquid/Crypto).
    Todas as ações reais de trade passam obrigatoriamente pelo middleware de segurança
    implementado em ExecutorBase (ex: cheque de limite de capital, paper vs real).
    """
    
    def __init__(self, origin: str = "vps"):
        super().__init__(origin)
        # Polymarket APIs
        self.gamma_api_url = "https://gamma-api.polymarket.com"
        # Clients HTTP assíncronos/síncronos
        self.client = httpx.Client(timeout=10.0)

    def _execute_action(self, action: Dict[str, Any], hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementação específica para finanças. 
        Recebe a intenção de ação vinda do Planner e aprovada pelo Evaluator.
        """
        action_type = action.get("type")
        
        if action_type == "read_odds":
            return self._fetch_polymarket_event(action.get("event_slug", ""))
        elif action_type == "trade":
            return self._execute_trade(action)
        else:
            raise ExecutionError(f"Ação financeira não reconhecida: {action_type}")

    def _fetch_polymarket_event(self, event_slug: str) -> Dict[str, Any]:
        """Busca odds e informações de um evento na Polymarket pelo slug."""
        if not event_slug:
            raise ExecutionError("event_slug obrigatório para ler odds.")
            
        try:
            url = f"{self.gamma_api_url}/events?slug={event_slug}"
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {"status": "error", "message": f"Evento {event_slug} não encontrado."}
                
            event = data[0] if isinstance(data, list) else data
            return {
                "status": "success",
                "action_type": "read_odds",
                "event_id": event.get("id"),
                "title": event.get("title"),
                "active": event.get("active"),
                "markets": event.get("markets", [])
            }
        except httpx.HTTPError as e:
            logger.error(f"Erro ao buscar Polymarket event: {str(e)}")
            raise ExecutionError(f"Polymarket API error: {str(e)}")

    def _execute_trade(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa um trade na Polymarket.
        Na Fase 1, o middleware do ExecutorBase reverte type='real' se paper for obrigatório.
        """
        execution_type = action.get("execution_type", "paper")
        market_id = action.get("market_id")
        direction = action.get("direction") # YES ou NO
        amount = action.get("amount", 0)
        
        if not market_id or not direction:
            raise ExecutionError("market_id e direction são obrigatórios para trade.")

        # Exemplo Simples de Paper Trading
        if execution_type == "paper":
            logger.info(f"Simulando ordem Paper: {direction} em {market_id} valor ${amount}")
            return {
                "status": "executed",
                "action_type": "trade",
                "execution_type": "paper",
                "market_id": market_id,
                "asset": "polymarket_share",
                "direction": direction,
                "amount": amount,
                "simulated_entry_price": 0.50, # Placeholder, idealmente viria do _fetch_polymarket_event
                "note": "Execução Paper concluída. Nenhuma transação Polygon disparada."
            }
        else:
            # Integração Real (Fase 3+) iria aqui usando bibliotecas web3
            logger.warning("Execução real solicitada. Requer integração com chaves Polygon.")
            return {
                "status": "failed",
                "reason": "Execução Real pendente de injeção de chaves privadas (Polygon).",
                "action_type": "trade",
                "execution_type": "real"
            }

    def close(self):
        """Fecha as conexões HTTP do executor."""
        self.client.close()
