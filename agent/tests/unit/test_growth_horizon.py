import pytest
from datetime import datetime, timezone
from shared.database.causal_bank import CausalBank
from shared.intent.growth_horizon import GrowthHorizon

@pytest.fixture
def test_bank():
    return CausalBank(database_url="sqlite:///:memory:", origin="test")

@pytest.fixture
def horizon(test_bank):
    return GrowthHorizon(causal_bank=test_bank)

def test_declare_growth_target(horizon):
    target_id = horizon.declare_growth_target(
        domain="trading",
        current_state="Opero por impulso e sem stop loss.",
        desired_future="Opero com plano definido e sempre uso stop loss.",
        progress_metrics=["percentual_com_stop", "trades_por_semana"],
        deadline_days=90
    )
    
    assert target_id is not None
    
    report = horizon.get_weekly_report()
    assert any(t["domain"] == "trading" for t in report["targets"])
    target_report = next(t for t in report["targets"] if t["domain"] == "trading")
    assert "Opero por impulso" in target_report["current_state"]

def test_update_progress(horizon):
    target_id = horizon.declare_growth_target(
        domain="trading",
        current_state="Opero por impulso e sem stop loss.",
        desired_future="Opero com plano definido e sempre uso stop loss.",
        progress_metrics=["percentual_com_stop"],
    )
    
    result = horizon.update_progress(
        target_id=target_id,
        metrics_snapshot={"percentual_com_stop": 0.5}  # 50%
    )
    
    assert result is not None
    assert "distance" in result
    assert "trend" in result
    
    # Need to verify in the report
    report = horizon.get_weekly_report(target_id)
    target_report = report["targets"][0]
    assert target_report["distance"] == 0.5
    assert target_report["trend"] == "iniciando"

def test_propose_growth_conversation(horizon):
    target_id = horizon.declare_growth_target(
        domain="trading",
        current_state="Impulso.",
        desired_future="Plano.",
        progress_metrics=["metric_1"],
    )
    
    horizon.update_progress(
        target_id=target_id,
        metrics_snapshot={"metric_1": 10}
    )
    
    msg = horizon.propose_growth_conversation(target_id)
    assert msg is not None
    assert "trading" in msg
