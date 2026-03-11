# agent/tests/test_proactive_chat.py
from memory.causal_bank import CausalBank
import time

def test_proactive_insight():
    bank = CausalBank(database_url="sqlite:///:memory:", origin="test")
    
    print("Injetando sinal de alta relevância no CausalBank...")
    
    # Criar um sinal de "Guerra Cibernética" ou algo impactante
    bank.insert_signal({
        "domain": "finance",
        "type": "critical_event",
        "source": "TestScript",
        "title": "ALERTA: Queda Súbita no S&P 500",
        "content": "O mercado futuro do S&P 500 caiu 3% em 10 minutos após rumores de instabilidade bancária global. Recomenda-se cautela extrema.",
        "relevance_score": 0.95,
        "metadata": {"ticker": "^GSPC", "change": -3.0}
    })
    
    print("Sinal injetado. Aguarde 5-10 segundos e verifique o Dashboard da Rebeka.")
    print("O Chat deve mostrar o Insight automaticamente.")

if __name__ == "__main__":
    test_proactive_insight()

