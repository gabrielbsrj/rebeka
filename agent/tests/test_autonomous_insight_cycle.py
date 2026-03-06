# agent/tests/test_autonomous_insight_cycle.py
import asyncio
import logging
import sys
import os
import uuid
import json
from unittest.mock import MagicMock, patch

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database.causal_bank import CausalBank
from shared.communication.chat_manager import ChatManager
from vps.services.proactive_insight import ProactiveInsightService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_autonomous_insight")

async def test_cycle():
    logger.info("Iniciando teste do Ciclo de Insight Autônomo...")
    
    # 1. Setup mocks e componentes
    bank = CausalBank(origin="test")
    # Limpar banco de sinais de teste se possível (opcional, vamos apenas garantir ID único)
    
    chat_manager = ChatManager()
    unique_title = f"CRASH TEST {uuid.uuid4()}: S&P 500 cai 10%"
    
    # Injetar sinal de alta relevância (1.0)
    bank.insert_signal({
        "domain": "finance",
        "title": unique_title,
        "content": "Movimento sem precedentes no mercado financeiro global.",
        "relevance_score": 1.0,
        "source": "test"
    })
    
    # 2. Mock do SyncServer manager para interceptar o dispatch
    from unittest.mock import AsyncMock
    mock_manager = MagicMock()
    mock_manager.dispatch_tool = AsyncMock()
    
    # 3. Inicializar serviço e rodar uma iteração
    service = ProactiveInsightService(bank, chat_manager, check_interval=1)
    
    with patch("vps.sync_server.manager", mock_manager):
        logger.info("Executando verificação de insights...")
        await service._check_new_insights()
        
    # 4. Veras (Asserções)
    # Verificar se o dispatch_tool foi chamado (pode ser mais de uma vez devido a resíduos no DB, mas o nosso deve estar lá)
    found_our_call = False
    for call in mock_manager.dispatch_tool.call_args_list:
        args, kwargs = call
        if args[0] == "perplexity_search" and unique_title in args[1]["query"]:
            found_our_call = True
            break
            
    assert found_our_call, "A ferramenta perplexity_search não foi disparada para o sinal específico."
    logger.info("Sucesso: ferramenta perplexity_search foi disparada pelo serviço de insights.")

    # 5. Testar fluxo de retorno (Tool Result -> Chat)
    from vps.sync_server import websocket_endpoint, _chat_manager
    import vps.sync_server
    vps.sync_server._chat_manager = chat_manager
    
    mock_ws = AsyncMock()
    # Simular recebimento de resultado de ferramenta
    mock_ws.receive_text.side_effect = [
        json.dumps({
            "type": "tool_result",
            "tool_name": "perplexity_search",
            "status": "success",
            "result": {
                "query": unique_title,
                "full_answer": "Este é um relatório detalhado de teste."
            }
        }),
        # Lançar exceção para sair do loop
        Exception("Exit Loop")
    ]
    
    try:
        await websocket_endpoint(mock_ws)
    except:
        pass
        
    # Verificar se o relatório chegou no chat
    insights = chat_manager.poll_insights()
    found_report = any("Relatório de Deep Research" in msg and unique_title in msg for msg in insights)
    assert found_report, "O relatório final não foi postado no chat após o recebimento do resultado."
    
    logger.info("Sucesso: Relatório de pesquisa postado no chat via SyncServer.")
    logger.info("--- TESTE COMPLETO CONCLUÍDO COM SUCESSO ---")

if __name__ == "__main__":
    asyncio.run(test_cycle())
