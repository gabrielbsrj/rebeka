import sys
import os
import logging
from datetime import datetime, timedelta, timezone
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.causal_bank import CausalBank
from intelligence.causal_validator import CausalValidator
from vps.correlator import GlobalCorrelator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_correlation_discovery():
    # 1. Setup
    bank = CausalBank(origin="vps")
    
    # Mock do validador para não gastar API em teste unitário
    class MockValidator:
        def validate_pattern(self, cause, effect, domain):
            print(f"  [Mock LLM] Validando: {cause} -> {effect}")
            return {
                "is_plausible": True,
                "mechanism": "O aumento da tensão geopolítica geralmente causa incerteza nos mercados, levando a mudanças nas apostas.",
                "confidence": 0.85
            }
    
    validator = MockValidator()
    correlator = GlobalCorrelator(bank, validator)

    # 2. Inserir Sinais Sintéticos
    now = datetime.now(timezone.utc)
    
    # Sinal A: Geopolítica (Causa)
    signal_a = {
        "domain": "geopolitics",
        "source": "RSS Feed",
        "title": "Aumento de tensões na fronteira leste",
        "content": "Tropas foram vistas se movendo...",
        "relevance_score": 0.9,
    }
    # Inserimos com timestamp manual se possível, ou apenas esperamos o delay
    id_a = bank.insert_signal(signal_a)
    print(f"Sinal A (Geopolítica) inserido: {id_a}")
    
    # Delay pequeno para tempo ser diferente
    time.sleep(1)
    
    # Sinal B: Finanças (Efeito)
    signal_b = {
        "domain": "finance",
        "source": "Polymarket",
        "title": "Odds de 'Paz Duradoura' caem para 10%",
        "content": "Mercado reagindo a movimentos militares.",
        "relevance_score": 0.8,
    }
    id_b = bank.insert_signal(signal_b)
    print(f"Sinal B (Finanças) inserido: {id_b}")

    # 3. Rodar Escaneamento de Correlação
    print("\nExecutando scan_for_patterns...")
    correlator.scan_for_patterns(window_hours=1)

    # 4. Verificar Resultados
    print("\nVerificando se o padrão causal foi salvo...")
    patterns = bank.get_active_patterns("geopolitics_to_finance")
    
    if patterns:
        p = patterns[0]
        print(f"SUCESSO! Padrão detectado e validado:")
        print(f"  Causa: {p['cause']}")
        print(f"  Efeito: {p['effect']}")
        print(f"  Mecanismo: {p['mechanism']}")
        print(f"  Confiança: {p['confidence']}")
    else:
        print("FALHA: Nenhum padrão detectado.")

if __name__ == "__main__":
    test_correlation_discovery()

