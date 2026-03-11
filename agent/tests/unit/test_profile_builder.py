import pytest
from memory.causal_bank import CausalBank
from intelligence.profile_builder import ProfileBuilder

@pytest.fixture
def test_bank():
    # Use in-memory SQLite for fast, isolated tests
    bank = CausalBank(database_url="sqlite:///:memory:", origin="test")
    return bank

@pytest.fixture
def profile_builder(test_bank):
    return ProfileBuilder(causal_bank=test_bank)

def test_declare_profile(profile_builder):
    profile_id = profile_builder.declare_profile(
        risk_profile="arrojado",
        autonomy_preference="autonomo",
        horizon_temporal="longo",
        biggest_pain_point="falta de tempo",
        regret_definition="nao ter comecado antes",
        relationship_with_risk="gosta de risco calculado"
    )
    assert profile_id is not None
    
    summary = profile_builder.get_profile_summary()
    assert summary is not None
    assert summary["declared"]["risk_profile"] == "arrojado"
    assert summary["declared"]["autonomy_preference"] == "autonomo"
    assert summary["declared"]["horizon_temporal"] == "longo"

def test_update_observed_profile(profile_builder):
    profile_builder.declare_profile(
        risk_profile="moderado",
        autonomy_preference="consultado",
        horizon_temporal="medio"
    )
    
    record_id = profile_builder.update_observed_profile(
        domain="risk_profile",
        observed_value="arrojado",
        evidence={"trade_id": "123", "leverage": "50x"},
        confidence=0.8
    )
    
    assert record_id is not None
    
    summary = profile_builder.get_profile_summary()
    assert any(o["domain"] == "risk_profile" for o in summary["observed"])
    observed_trading = next(o for o in summary["observed"] if o["domain"] == "risk_profile")
    assert observed_trading["value"] == "arrojado"
    assert observed_trading["confidence"] == 0.8
    
    # Check divergences
    divergences = summary.get("divergencies", [])
    assert len(divergences) > 0
    assert any(d["domain"] == "risk_profile" for d in divergences)

def test_increment_observation(profile_builder):
    profile_builder.update_observed_profile(
        domain="trading",
        observed_value="arrojado",
        evidence={"trade_id": "123"},
        confidence=0.5
    )
    
    profile_builder.increment_observation(
        domain="trading",
        observed_value="arrojado",
        evidence={"trade_id": "124"}
    )
    
    summary = profile_builder.get_profile_summary()
    assert any(o["domain"] == "trading" for o in summary["observed"])
    observed_trading = next(o for o in summary["observed"] if o["domain"] == "trading")
    assert observed_trading["observation_count"] == 2
    assert observed_trading["confidence"] > 0.5  # Confidence should increase

def test_check_divergence_and_notify(profile_builder):
    profile_builder.declare_profile(
        risk_profile="conservador",
        autonomy_preference="consultado",
        horizon_temporal="longo"
    )
    
    profile_builder.update_observed_profile(
        domain="risk_profile",
        observed_value="arrojado",
        evidence={"action": "all-in crypto"},
        confidence=0.9
    )
    
    msg = profile_builder.check_divergence_and_notify("risk_profile", "arrojado")
    assert msg is not None
    assert "conservador" in msg["message"]
    assert "arrojado" in msg["message"]

