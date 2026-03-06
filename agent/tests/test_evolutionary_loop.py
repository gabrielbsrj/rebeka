# agent/tests/test_evolutionary_loop.py
import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database.causal_bank import CausalBank
from shared.evolution.observer import Observer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_evolution")

async def test_observer_analysis():
    logger.info("Iniciando teste de Auto-Análise Evolutiva (Observer)...")
    
    # 1. Setup
    bank = CausalBank(origin="test")
    
    # 2. Mockar dados de performance no CausalBank
    # Simular win_rate de 40% (Erro sistêmico detectado)
    # Simular confiança média de 80% (Erro de calibração alto)
    with patch.object(CausalBank, 'get_performance_stats', return_value={"win_rate": 0.40, "total_trades": 20}):
        with patch.object(CausalBank, 'get_recent_hypotheses', return_value=[{"confidence": 0.8}] * 20):
            
            observer = Observer(bank)
            metrics = observer.analyze_performance()
            
            logger.info(f"Métricas analisadas: {metrics}")
            
            assert metrics["violation_detected"] == True, "Deveria detectar violação de calibração (80% vs 40%)"
            assert metrics["systemic_error_detected"] == True, "Deveria detectar erro sistêmico (win_rate < 50%)"
            
            # 3. Testar questionamento (LLM Mock)
            with patch('litellm.completion') as mock_completion:
                mock_completion.return_value.choices[0].message.content = "Por que minha confiança excedeu em 40% a taxa de sucesso real? Isso indica um viés otimista perigoso."
                
                question = observer.question_reasoning(metrics)
                logger.info(f"Questionamento gerado pelo Observer: {question}")
                assert "viés otimista" in question
    
    logger.info("--- TESTE EVOLUTIVO CONCLUÍDO COM SUCESSO ---")

if __name__ == "__main__":
    asyncio.run(test_observer_analysis())
