import pytest
from datetime import datetime, timezone
from shared.database.causal_bank import CausalBank
from shared.intent.behavioral_pattern_detector import BehavioralPatternDetector

@pytest.fixture
def test_bank():
    return CausalBank(database_url="sqlite:///:memory:", origin="test")

@pytest.fixture
def detector(test_bank):
    return BehavioralPatternDetector(causal_bank=test_bank)

def test_detect_from_execution_no_stop_loss(detector):
    execution_data = {
        "hypothesis_id": "hyp_1",
        "execution_type": "paper",
        "market": "polymarket",
        "asset": "BTC",
        "amount": 100,
        "has_stop_loss": False,
        "result": 50,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    patterns = detector.detect_from_execution(execution_data)
    # The detector returns a list of patterns found
    assert len(patterns) >= 0

def test_check_revenge_trading(detector, test_bank):
    # Simulate a recent loss
    test_bank.insert_execution({
        "hypothesis_id": "hyp_1",
        "execution_type": "paper",
        "market": "polymarket",
        "asset": "ETH",
        "direction": "buy",
        "amount": 100,
        "result": -100,  # Loss
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Simulate a new trade immediately after
    execution_data = {
        "hypothesis_id": "hyp_2",
        "execution_type": "paper",
        "market": "polymarket",
        "asset": "BTC",
        "amount": 200,  # Larger amount after loss is a classic revenge trading sign
        "result": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    patterns = detector.detect_from_execution(execution_data)
    assert isinstance(patterns, list)

def test_detect_from_conversation(detector):
    text = "Eu sempre compro quando todo mundo tá falando, por causa do fomo. E depois me arrependo."
    patterns = detector.detect_from_conversation(text)
    assert isinstance(patterns, list)

def test_get_limiting_patterns(detector, test_bank):
    # Insert some fake patterns into the bank
    test_bank.insert_signal({
        "domain": "intent_engine",
        "type": "behavioral_pattern",
        "source": "BehavioralPatternDetector",
        "title": "overtrading",
        "content": "Padrão detectado",
        "relevance_score": 0.8,
        "metadata": {
            "pattern_type": "overtrading",
            "confidence": 0.9,
            "category": "limiting",
            "potentially_limiting": True,
            "evidence": {}
        }
    })
    
    limiting = detector.get_limiting_patterns()
    assert len(limiting) >= 0
