import pytest
from unittest.mock import patch, MagicMock
from shared.database.causal_bank import CausalBank
from shared.intent.intent_engine import IntentEngine

@pytest.fixture
def test_bank():
    return CausalBank(database_url="sqlite:///:memory:", origin="test")

@pytest.fixture
def engine(test_bank):
    e = IntentEngine(causal_bank=test_bank, origin="test")
    e.initialize()
    return e

@patch('shared.intent.conversation_analyzer.ConversationAnalyzer.analyze_and_update_patterns')
def test_on_user_message(mock_analyze, engine):
    mock_analyze.return_value = {
        "status": "success",
        "extracted": {
            "emotional_state": {"primary": "calm", "intensity": 0.5},
            "intentions": [],
            "behavioral_cues": [],
            "receptivity_score": 0.8
        }
    }
    
    response = engine.on_user_message("Tudo tranquilo hoje.", "conv_1")
    
    assert response is not None
    assert response["status"] == "processed"
    assert "extracted_signals" in response

def test_declare_onboarding(engine):
    answers = {
        "relationship_with_risk": "arriscar_perder",
        "autonomy_preference": "autonomo",
        "horizon_temporal": "longo",
        "biggest_pain_point": "tempo",
        "regret_definition": "nao agir"
    }
    
    profile_id = engine.declare_onboarding(answers)
    assert profile_id is not None
    
    summary = engine.get_profile_summary()
    assert summary is not None
    
    declared = summary.get("declared", {})
    assert declared.get("relationship_with_risk") == "arriscar_perder"

def test_update_growth_progress(engine):
    # Setup a target first
    engine.declare_onboarding({
        "biggest_pain_point": "trading",
        "growth_horizon": "ser trader profissional"
    })
    
    result = engine.update_growth_progress({
        "percentual_com_stop": 0.8
    })
    
    assert result is not None
    assert result["status"] == "updated"

@patch('shared.intent.intentional_friction.IntentionalFriction.check_pending_friction_candidates')
@patch('shared.intent.intentional_friction.IntentionalFriction.apply_friction')
def test_get_next_action(mock_apply, mock_check, engine):
    # Mock friction system to say we have a candidate
    mock_check.return_value = [{
        "pattern_id": "pat_123",
        "confidence": 0.9,
        "confirmation_count": 6
    }]
    
    mock_apply.return_value = {
        "id": "fric_1",
        "message": "Fricção teste",
        "level": "moderada"
    }
    
    action = engine.get_next_action()
    
    assert action is not None
    assert action["type"] == "friction"
    assert "message" in action["data"]
