# tests/unit/test_executor.py
import pytest
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.executor_base import ExecutorBase

class DummyExecutor(ExecutorBase):
    def _execute_action(self, action, hypothesis):
        return {"status": "success"}

class DummySecurity:
    def check_capital_limit(self, amount, execution_type):
        return True
    
    def is_paper_trading_required(self):
        return True

def test_executor_wait_action_no_crash():
    """Testa se uma ação do tipo 'wait' retorna imediatamente sem erro e sem usar variáveis não definidas."""
    executor = DummyExecutor(origin="test")
    
    hypothesis = {
        "id": "hyp_123",
        "action": {
            "type": "wait",
        }
    }
    
    evaluation = {"approved": True}
    security = DummySecurity()
    
    # Executa a ação wait
    result = executor.execute(hypothesis, evaluation, security)
    
    # Verifica o resultado
    assert result["status"] == "skipped"
    assert result["reason"] == "Ação é wait — nenhuma execução necessária."
    assert result["execution_type"] == "skipped"
    assert "timestamp" in result
    assert result["hypothesis_id"] == "hyp_123"
    assert result["direction"] == "wait"
    assert result["amount"] == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

