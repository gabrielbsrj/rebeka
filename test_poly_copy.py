import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), 'agent', '.env')
load_dotenv(env_path)

os.environ["OPENAI_API_KEY"] = os.getenv("MOONSHOT_API_KEY") or os.environ.get("MOONSHOT_API_KEY", "")
if not os.environ.get("OPENAI_API_BASE"):
    os.environ["OPENAI_API_BASE"] = "https://api.moonshot.cn/v1"

# Adjust path to find modules inside 'agent'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'agent')))

from shared.database.causal_bank import CausalBank
from vps.monitors.polymarket_monitor import PolymarketWhaleMonitor
from vps.strategies.poly_strategist import PolymarketStrategist

logging.basicConfig(level=logging.INFO, format="%(message)s")

class MockChatManager:
    """Mock do ChatManager apenas para exibir as notificações no terminal"""
    def push_insight(self, text: str):
        print("\n" + "="*50)
        print("🤖 [REBEKA CHAT]:")
        print(text)
        print("="*50 + "\n")

async def test_copy_trading():
    print("="*60)
    print("Iniciando Teste do Pipeline de Copy Trading - Polymarket")
    print("1. Buscando Sinais (Monitor)")
    print("2. Planejador Raciocinando sobre o Trade")
    print("3. Avaliador Julgando o Risco")
    print("4. Execução Financeira Simulata (Paper)")
    print("="*60 + "\n")

    bank = CausalBank(origin="vps")
    chat_mock = MockChatManager()
    
    # Init Monitor e Estrategista
    monitor = PolymarketWhaleMonitor()
    strategist = PolymarketStrategist(bank, chat_mock)
    
    # 1. Obter Sinais do Mercado
    raw_signals = monitor.fetch_data()
    
    if not raw_signals:
        print("Nenhum grande movimento detectado momento.")
        return
        
    print(f"Baleias Detectadas: {len(raw_signals)}")
    
    # Processar o primeiro sinal para teste
    sig = raw_signals[0]
    mapped_sig = monitor.map_to_signal(sig)
    print(f"\n[SINAL DETECTADO]: {mapped_sig['title']}")
    
    # 2. Enviar para a Analista (Rebeka)
    print("\n[ENVIANDO SINAL AO CÉREBRO DA REBEKA PARA RACIOCÍNIO...]")
    await strategist.evaluate_whale_signal(mapped_sig)

if __name__ == "__main__":
    asyncio.run(test_copy_trading())
