import sys
import os
import logging
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.causal_bank import CausalBank
from vps.monitors.geopolitics import GeopoliticsMonitor
from vps.monitors.macro import MacroMonitor
from vps.monitors.commodities import CommoditiesMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_monitors():
    bank = CausalBank(origin="vps")
    
    geopolitics = GeopoliticsMonitor(causal_bank=bank)
    macro = MacroMonitor(causal_bank=bank)
    commodities = CommoditiesMonitor(causal_bank=bank)

    monitors = [
        ("Geopolitics", geopolitics),
        ("Macro", macro),
        ("Commodities", commodities)
    ]

    for name, monitor in monitors:
        print(f"\n{'='*40}\nTestando Monitor: {name}\n{'='*40}")
        try:
            raw_data = monitor.fetch_data()
            print(f"[{name}] Encontrou {len(raw_data)} itens brutos no RSS.")
            
            signals_generated = 0
            for item in raw_data:
                signal = monitor.map_to_signal(item)
                if signal:
                    signals_generated += 1
                    try:
                        # Test inserting into DB
                        signal_id = bank.insert_signal(signal)
                        print(f"  + Sinal Válido Extraído -> DB ID: {signal_id} | Entities: {signal.get('extracted_entities')}")
                    except Exception as db_err:
                        print(f"  [!] Falha de inserção no banco: {db_err}")
            
            print(f"[{name}] Converteu {signals_generated} itens em Sinais Válidos (com keywords relevantes).")
        except Exception as e:
            logger.error(f"Erro no teste do {name}: {e}")

if __name__ == "__main__":
    test_monitors()

