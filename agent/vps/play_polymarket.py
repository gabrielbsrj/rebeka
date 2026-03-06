import sys
import os
import logging
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database.causal_bank import CausalBank
from shared.core.security_phase1 import SecurityPhase1
from vps.executor_financial import FinancialExecutor

logging.basicConfig(level=logging.INFO)

async def test_financial_execution():
    bank = CausalBank(origin="vps")
    security = SecurityPhase1()
    executor = FinancialExecutor(origin="vps")

    print("\n[1] Lendo eventos na Polymarket (Bitcoin atingir 100k)")
    # Polymarket usa slugs nas URIs - "will-bitcoin-hit-100k-in-2024" ou procuramos um ativo.
    # Usaremos um slug conhecido apenas para teste da API, se errar ele vai retornar 404 mas o código trata.
    read_action = {
        "type": "read_odds",
        "event_slug": "will-bitcoin-hit-130k-in-2025"
    }

    # Hypothesis/Evaluation Mock
    hypo_read = {"id": "hypo_123", "action": read_action}
    eval_read = {"approved": True}

    try:
        res = executor.execute(hypothesis=hypo_read, evaluation=eval_read, security_config=security)
        print("Resultado Leitura Odds:", res)
    except Exception as e:
        print("Aviso na leitura de evento:", e)

    print("\n[2] Operando Trade Paper com limites corretos")
    trade_action_paper = {
        "type": "trade",
        "execution_type": "paper",
        "market_id": "0x123abc...",
        "direction": "YES",
        "amount": 50.0  # Abaixo de 10% total de 1000
    }
    hypo_paper = {"id": "hypo_456", "action": trade_action_paper}
    eval_paper = {"approved": True}

    res_paper = executor.execute(hypothesis=hypo_paper, evaluation=eval_paper, security_config=security)
    print("Resultado Trade Paper:", res_paper)

    # Inserção no CausalBank (Mapeamento)
    exec_id = bank.insert_execution({
        "hypothesis_id": res_paper["hypothesis_id"],
        "execution_type": res_paper["execution_type"],
        "market": "Polymarket",
        "asset": res_paper.get("asset", "unknown"),
        "direction": res_paper.get("direction", "unknown"),
        "amount": res_paper.get("amount", 0.0),
        "entry_price": res_paper.get("simulated_entry_price")
    })
    print(f"Trade paper registrado no CausalBank com ID Canônico via Merkle Tree: {exec_id}")

    print("\n[3] Tentativa de Operação Acima do Limite de Capital (Real)")
    trade_action_limit = {
        "type": "trade",
        "execution_type": "real",
        "market_id": "0x123abc...",
        "direction": "YES",
        "amount": 200.0  # Limite Fase 1 é max 10% de 1000 = 100. Acima!
    }
    hypo_limit = {"id": "hypo_789", "action": trade_action_limit}
    eval_limit = {"approved": True}

    try:
        res_limit = executor.execute(hypothesis=hypo_limit, evaluation=eval_limit, security_config=security)
        print("Isso não deve ser exbido. Falha de seguranca:", res_limit)
    except Exception as e:
        print(f"Segurança funcionou. Erro retornado: {str(e)}")

    executor.close()

if __name__ == "__main__":
    asyncio.run(test_financial_execution())
