# agent/tests/integration/test_synthesis_flow.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19

import pytest
import asyncio
from sync.synthesis_engine import SynthesisEngine
from sync.meta_synthesis import MetaSynthesis

@pytest.mark.asyncio
async def test_dual_twin_synthesis():
    """
    Simula uma divergência real entre os gêmeos e testa a síntese.
    """
    engine = SynthesisEngine()
    meta = MetaSynthesis()

    # 1. Cenário VPS: Geopolítica tensa sugere venda
    vps_view = {
        "source": "vps_global_monitor",
        "signal": "Escalation in Middle East",
        "recommendation": "SELL high-risk assets",
        "confidence": 0.85
    }

    # 2. Cenário Local: Usuário tem compromisso financeiro inadiável
    local_view = {
        "source": "local_context",
        "signal": "User has 30k USD debt due tomorrow",
        "recommendation": "HOLD to preserve liquidity",
        "confidence": 0.95
    }

    # 3. Executar Síntese
    # Nota: Em testes sem API key real, o mock da SynthesisEngine deve lidar com isso
    result = engine.synthesize(
        vps_view=vps_view,
        local_view=local_view,
        context={"user_id": "main_user"}
    )

    # 4. Registrar no Meta-Synthesis
    meta.record_attempt(result, vps_view, local_view)

    # 5. Verificações
    assert "divergence_root" in result
    assert "emergent_perspective" in result
    assert meta.get_divergence_report()["total_attempts"] == 1
    
    print(f"\n[TEST] Raiz da Divergência: {result['divergence_root']}")
    print(f"[TEST] Perspectiva Emergente: {result['emergent_perspective']}")
