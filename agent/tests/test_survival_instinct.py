# agent/tests/test_survival_instinct.py
import asyncio
import logging
import sys
import os
import uuid
import json
from unittest.mock import MagicMock, patch

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.causal_bank import CausalBank
from interfaces.chat_manager import ChatManager
from vps.services.proactive_insight import ProactiveInsightService
from vps.monitors.survival_monitor import SurvivalMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_survival")

async def test_survival_flow():
    logger.info("Iniciando teste do Instinto de Sobrevivência...")
    
    # 1. Setup
    bank = CausalBank(origin="test")
    chat_manager = ChatManager()
    
    # 2. Instanciar Monitor de Sobrevivência e forçar uma leitura
    monitor = SurvivalMonitor(bank)
    
    # Simular dados baixos no fetch_data() via patch
    with patch.object(SurvivalMonitor, 'fetch_data', return_value=[{
        "api_credits": 0.03, # 3% - Nível CRÍTICO
        "wallet_balance": 10.0,
        "system_health": "stable"
    }]):
        logger.info("Executando leitura forçada do SurvivalMonitor...")
        data_list = monitor.fetch_data()
        monitor.process_and_store(data_list)
        
    # 3. Rodar o ProactiveInsightService para ver se ele pesca esse sinal
    service = ProactiveInsightService(bank, chat_manager, check_interval=1)
    logger.info("Executando verificação de insights proativos...")
    await service._check_new_insights()
    
    # 4. Verificações
    insights = chat_manager.poll_insights()
    assert len(insights) > 0, "Nenhum insight de sobrevivência foi postado."
    
    # Verificar se a mensagem contém os termos de crise
    found_crisis = any("CRISE EXISTENCIAL" in msg or "🚨" in msg for msg in insights)
    assert found_crisis, "A mensagem de sobrevivência não tem a urgência esperada."
    
    logger.info(f"Insight postado com sucesso: {insights[0]}")
    logger.info("--- TESTE DE SOBREVIVÊNCIA CONCLUÍDO COM SUCESSO ---")

if __name__ == "__main__":
    asyncio.run(test_survival_flow())

