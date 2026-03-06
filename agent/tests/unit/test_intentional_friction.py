import pytest
from datetime import datetime, timezone
from shared.database.causal_bank import CausalBank
from shared.intent.intentional_friction import IntentionalFriction

@pytest.fixture
def test_bank():
    return CausalBank(database_url="sqlite:///:memory:", origin="test")

@pytest.fixture
def friction(test_bank):
    return IntentionalFriction(causal_bank=test_bank)

def test_should_apply_friction(friction, test_bank):
    # Setup - need a pattern with high confidence and confirmations
    pattern_id = test_bank.insert_behavioral_pattern({
        "domain": "intent_engine",
        "pattern_type": "vies_alta",
        "description": "Operando demais",
        "confidence": 0.9,
        "confirmation_count": 6,
        "potentially_limiting": True,
        "evidence": []
    })
    
    # Needs to be receptive and neutral emotional state
    should_apply = friction.should_apply_friction(
        pattern_id=pattern_id,
        user_receptivity=0.8,
        emotional_state="neutral"
    )
    
    assert should_apply is True

def test_calculate_friction_level(friction):
    # High stats -> "direta"
    level = friction.calculate_friction_level(
        pattern_confidence=0.9,
        confirmation_count=10,
        distance_from_desired=0.8
    )
    assert level == "direta"
    
    # Lower stats -> "leve" or "moderada"
    level = friction.calculate_friction_level(
        pattern_confidence=0.4,
        confirmation_count=1,
        distance_from_desired=0.1
    )
    assert level in ["leve", "moderada"]

def test_apply_friction(friction, test_bank):
    pattern_id = test_bank.insert_behavioral_pattern({
        "domain": "intent_engine",
        "pattern_type": "vies_alta",
        "description": "Operando demais",
        "confidence": 0.9,
        "confirmation_count": 6,
        "potentially_limiting": True,
        "evidence": []
    })
    
    result = friction.apply_friction(
        pattern_id=pattern_id,
        user_receptivity=0.8,
        emotional_state="neutral"
    )
    
    assert result is not None
    assert "message" in result
    assert "level" in result
    assert "id" in result

def test_record_user_response(friction, test_bank):
    # We'll just verify no crashes as the implementation is simple logging for now
    friction.record_user_response(
        friction_id="fric_123",
        response="receptivo"
    )
    assert True
