# agent/tests/test_hifi_monitors.py
import asyncio
import logging
import sys
import os

# Ajustar PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.monitors.financial_monitor import FinancialMonitor
from vps.monitors.macro_monitor import MacroMonitor
from memory.causal_bank import CausalBank

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_monitors():
    print("\n--- TESTANDO MONITORES DE ALTA FIDELIDADE ---\n")
    
    # Mock do Banco (para não poluir o real)
    bank = CausalBank(origin="test")
    
    # 1. Teste FinancialMonitor
    print("1. Testando FinancialMonitor (Yahoo Finance)...")
    fin_monitor = FinancialMonitor(causal_bank=bank)
    raw_fin = fin_monitor.fetch_data()
    
    if raw_fin:
        print(f"   Sucesso! Buscou {len(raw_fin)} ativos.")
        for item in raw_fin[:2]:
            signal = fin_monitor.map_to_signal(item)
            print(f"   [SINAL] {signal['title']} -> {signal['content']}")
    else:
        print("   Falha ao buscar dados financeiros.")

    # 2. Teste MacroMonitor
    print("\n2. Testando MacroMonitor (FRED/Simulation)...")
    macro_monitor = MacroMonitor(causal_bank=bank)
    raw_macro = macro_monitor.fetch_data()
    
    if raw_macro:
        print(f"   Sucesso! Buscou {len(raw_macro)} indicadores (Modo: {macro_monitor.mode}).")
        for item in raw_macro:
            signal = macro_monitor.map_to_signal(item)
            print(f"   [SINAL] {signal['title']} -> {signal['content']}")
    else:
        print("   Falha ao buscar dados macro.")

    print("\n--- TESTE CONCLUÍDO ---")

if __name__ == "__main__":
    asyncio.run(test_monitors())

