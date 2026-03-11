import pytest
import json
from memory.causal_bank import CausalBank
from intelligence.conversation_analyzer import ConversationAnalyzer
from unittest.mock import patch, MagicMock

@pytest.fixture
def test_bank():
    return CausalBank(database_url="sqlite:///:memory:", origin="test")

@pytest.fixture
def analyzer(test_bank):
    return ConversationAnalyzer(causal_bank=test_bank, model="test-model")

@patch('shared.intent.conversation_analyzer.litellm.completion')
def test_analyze_conversation(mock_completion, analyzer):
    # Mock litellm response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "emotional_state": {"primary": "ansioso", "intensity": 0.8, "triggers": ["mercado"]},
        "intentions": [{"type": "trade", "confidence": 0.9, "target": "BTC"}],
        "behavioral_cues": [{"type": "fomo", "confidence": 0.85, "evidence": "quero comprar antes que suba mais"}],
        "receptivity_score": 0.5
    })
    mock_completion.return_value = mock_response

    result = analyzer.analyze_conversation("O mercado tá subindo muito, preciso comprar BTC agora!", "conv_123")
    
    assert result is not None
    assert result.get("emotional_state", {}).get("primary") == "ansioso"
    assert len(result.get("behavioral_cues", [])) == 1
    assert result["behavioral_cues"][0]["type"] == "fomo"

def test_detect_emotional_trends(analyzer, test_bank):
    # Insert some fake extracted signals into the causal bank
    test_bank.insert_signal({
        "domain": "intent_engine",
        "type": "conversation_extraction",
        "source": "ConversationAnalyzer",
        "title": "Análise 1",
        "content": "análise 1",
        "relevance_score": 1.0,
        "emotional": "ansioso",
        "metadata": {
            "intensity": 0.8
        }
    })
    test_bank.insert_signal({
        "domain": "intent_engine",
        "type": "conversation_extraction",
        "source": "ConversationAnalyzer",
        "title": "Análise 2",
        "content": "análise 2",
        "relevance_score": 1.0,
        "emotional": "ansioso",
        "metadata": {
            "intensity": 0.9
        }
    })
    
    trends = analyzer.detect_emotional_trends(days=7)
    assert trends is not None
    assert "ansioso" in trends.get("dominant_emotions", {})
    assert trends["dominant_emotions"]["ansioso"]["count"] == 2

