# agent/tests/unit/test_coherence_tracker.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes do CoherenceTracker

"""
Testes Unitários para CoherenceTracker.

Testa:
- Cálculo de coerência via LLM
- Integração com Banco de Causalidade
- Análise de contradições e padrões consistentes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from intelligence.coherence_tracker import CoherenceTracker


class TestCoherenceTrackerInit:
    """Testes de inicialização."""
    
    def test_init_default(self):
        tracker = CoherenceTracker()
        assert tracker._model == "gpt-4o-mini"
        assert tracker._causal_bank is None
        assert len(tracker._coherence_history) == 0
    
    def test_init_with_params(self):
        mock_bank = Mock()
        tracker = CoherenceTracker(
            model="gpt-4",
            api_key="test-key",
            causal_bank=mock_bank,
        )
        assert tracker._model == "gpt-4"
        assert tracker._api_key == "test-key"
        assert tracker._causal_bank == mock_bank


class TestCalculateCoherence:
    """Testes do cálculo de coerência."""
    
    @pytest.fixture
    def tracker(self):
        return CoherenceTracker(model="gpt-4o-mini", api_key="test-key")
    
    @pytest.fixture
    def mock_bank_with_decisions(self):
        bank = Mock()
        bank.get_user_decisions.return_value = [
            {"description": "Aceitou trade de alto risco", "reasoning": "Potencial retorno alto", "outcome": "ganhou"},
            {"description": "Rejeitou trade conservador", "reasoning": "Muito lento", "outcome": "n/a"},
            {"description": "Aceitou trade moderado", "reasoning": "Equilibrado", "outcome": "ganhou"},
        ]
        return bank
    
    @pytest.fixture
    def intent_model(self):
        return {
            "declared_values": [
                {"value": "Segurança financeira é prioridade", "category": "finance", "priority": "high"},
            ],
            "intentions": {
                "finance.single_operation": {"intention": "Proteger contra perdas concentradas"},
            }
        }
    
    def test_insufficient_decisions(self, tracker, intent_model):
        """Testa comportamento com poucas decisões."""
        result = tracker.calculate_coherence(
            user_id="test_user",
            intent_model=intent_model,
            timeframe_days=30,
        )
        
        assert result["coherence_score"] == 0.5
        assert "insuficiente" in result["analysis"].lower()
        assert result["decisions_analyzed"] == 0
    
    def test_no_declared_values(self, tracker):
        """Testa comportamento sem valores declarados."""
        # Como não há banco configurado, retorna dados insuficientes
        result = tracker.calculate_coherence(
            user_id="test_user",
            intent_model={},
            timeframe_days=30,
        )
        
        assert result["coherence_score"] == 0.5
        # Pode ser "dados insuficientes" ou "nenhum valor"
        assert "insuficiente" in result["analysis"].lower() or "nenhum" in result["analysis"].lower()
    
    def test_with_mock_bank_and_llm(self, mock_bank_with_decisions, intent_model):
        """Testa cálculo completo com mock do LLM."""
        tracker = CoherenceTracker(
            model="gpt-4o-mini",
            api_key="test-key",
            causal_bank=mock_bank_with_decisions,
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "coherence_score": 0.65,
            "analysis": "O usuário demonstra alguma inconsistência entre o valor declarado de segurança e as ações de risco aceitas.",
            "contradictions": [
                {
                    "declared_value": "Segurança financeira é prioridade",
                    "observed_action": "Aceitou trade de alto risco",
                    "severity": "medium",
                    "context": "Contradição entre desejo de segurança e aceitação de risco"
                }
            ],
            "consistent_patterns": [
                {
                    "declared_value": "Proteger contra perdas concentradas",
                    "supporting_actions": ["Aceitou trade moderado"],
                    "strength": "moderate"
                }
            ],
            "recommendations": ["Refletir sobre tolerância real ao risco"],
            "confidence_in_analysis": 0.8
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = tracker.calculate_coherence(
                user_id="test_user",
                intent_model=intent_model,
                timeframe_days=30,
                domain="finance",
            )
        
        assert result["coherence_score"] == 0.65
        assert result["confidence"] == 0.8
        assert len(result["contradictions"]) == 1
        assert len(result["consistent_patterns"]) == 1
        assert result["decisions_analyzed"] == 3
    
    def test_coherence_score_bounds(self, mock_bank_with_decisions, intent_model):
        """Testa que coherence_score está sempre entre 0 e 1."""
        tracker = CoherenceTracker(
            model="gpt-4o-mini",
            api_key="test-key",
            causal_bank=mock_bank_with_decisions,
        )
        
        # LLM retornando valor fora dos bounds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"coherence_score": 1.5, "analysis": "Test"}'
        
        with patch('litellm.completion', return_value=mock_response):
            result = tracker.calculate_coherence(
                user_id="test_user",
                intent_model=intent_model,
                timeframe_days=30,
            )
        
        assert 0.0 <= result["coherence_score"] <= 1.0
    
    def test_llm_error_handling(self, mock_bank_with_decisions, intent_model):
        """Testa tratamento de erro do LLM."""
        tracker = CoherenceTracker(
            model="gpt-4o-mini",
            api_key="test-key",
            causal_bank=mock_bank_with_decisions,
        )
        
        with patch('litellm.completion', side_effect=Exception("API Error")):
            result = tracker.calculate_coherence(
                user_id="test_user",
                intent_model=intent_model,
                timeframe_days=30,
            )
        
        assert result["coherence_score"] == 0.5
        assert "error" in result


class TestTrackMethod:
    """Testes do método track (compatibilidade)."""
    
    @pytest.fixture
    def tracker(self):
        return CoherenceTracker(model="gpt-4o-mini", api_key="test-key")
    
    def test_track_basic(self, tracker):
        """Testa registro básico de coerência."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"coherence_score": 0.7, "analysis": "Consistente"}'
        
        with patch('litellm.completion', return_value=mock_response):
            result = tracker.track(
                declared_value="Quero economizar",
                observed_action="Comprou produto caro",
            )
        
        assert "coherence_score" in result
        assert "trend" in result
        assert result["total_observations"] == 1
    
    def test_track_accumulates_history(self, tracker):
        """Testa que track acumula histórico."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"coherence_score": 0.5, "analysis": "Test"}'
        
        with patch('litellm.completion', return_value=mock_response):
            for i in range(5):
                tracker.track(f"Value {i}", f"Action {i}")
        
        assert len(tracker._coherence_history) == 5


class TestTrendCalculation:
    """Testes de cálculo de tendência."""
    
    @pytest.fixture
    def tracker(self):
        return CoherenceTracker()
    
    def test_insufficient_data_for_trend(self, tracker):
        """Testa tendência com dados insuficientes."""
        tracker._coherence_history = [
            {"coherence_score": 0.5},
            {"coherence_score": 0.6},
        ]
        assert tracker._calculate_trend() == "insufficient_data"
    
    def test_improving_trend(self, tracker):
        """Testa tendência de melhoria."""
        tracker._coherence_history = [
            {"coherence_score": 0.4},
            {"coherence_score": 0.5},
            {"coherence_score": 0.5},
            {"coherence_score": 0.5},
            {"coherence_score": 0.5},
            {"coherence_score": 0.7},
            {"coherence_score": 0.75},
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            {"coherence_score": 0.85},
        ]
        assert tracker._calculate_trend() == "improving"
    
    def test_declining_trend(self, tracker):
        """Testa tendência de queda."""
        tracker._coherence_history = [
            {"coherence_score": 0.9},
            {"coherence_score": 0.85},
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            {"coherence_score": 0.75},
            {"coherence_score": 0.6},
            {"coherence_score": 0.55},
            {"coherence_score": 0.5},
            {"coherence_score": 0.45},
            {"coherence_score": 0.4},
        ]
        assert tracker._calculate_trend() == "declining"
    
    def test_stable_trend(self, tracker):
        """Testa tendência estável."""
        tracker._coherence_history = [
            {"coherence_score": 0.6},
            {"coherence_score": 0.65},
            {"coherence_score": 0.6},
            {"coherence_score": 0.62},
            {"coherence_score": 0.63},
            {"coherence_score": 0.61},
            {"coherence_score": 0.64},
            {"coherence_score": 0.62},
            {"coherence_score": 0.63},
            {"coherence_score": 0.61},
        ]
        assert tracker._calculate_trend() == "stable"


class TestGetSummary:
    """Testes do método get_summary."""
    
    @pytest.fixture
    def tracker(self):
        return CoherenceTracker()
    
    def test_empty_summary(self, tracker):
        """Testa resumo sem dados."""
        summary = tracker.get_summary()
        
        assert summary["observations"] == 0
        assert summary["avg_coherence"] == 0.0
        assert summary["trend"] == "no_data"
    
    def test_summary_with_data(self, tracker):
        """Testa resumo com dados."""
        tracker._coherence_history = [
            {"coherence_score": 0.6},
            {"coherence_score": 0.7},
            {"coherence_score": 0.8},
            {"coherence_score": 0.75},
            {"coherence_score": 0.85},
        ]
        
        summary = tracker.get_summary()
        
        assert summary["observations"] == 5
        assert 0.7 < summary["avg_coherence"] < 0.8
        assert summary["last_coherence_score"] == 0.85


class TestGetCoherenceForEvaluator:
    """Testes do método de conveniência para o Avaliador."""
    
    def test_returns_float(self):
        """Testa que retorna float entre 0 e 1."""
        tracker = CoherenceTracker(model="gpt-4o-mini", api_key="test-key")
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"coherence_score": 0.72, "analysis": "Test"}'
        
        with patch('litellm.completion', return_value=mock_response):
            score = tracker.get_coherence_for_evaluator(
                user_id="test_user",
                intent_model={"declared_values": [{"value": "Test"}]},
                domain="finance",
            )
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestExtractDeclaredValues:
    """Testes de extração de valores declarados."""
    
    def test_extract_declared_values(self):
        tracker = CoherenceTracker()
        
        intent_model = {
            "declared_values": [
                {"value": "Segurança", "category": "finance", "priority": "high"},
            ],
            "intentions": {
                "finance.capital": {"intention": "Proteger capital"},
            },
            "inferred_values": [
                {"value": "Prefere baixo risco", "confidence": 0.8, "category": "finance"},
            ]
        }
        
        values = tracker._extract_declared_values(intent_model)
        
        assert len(values) == 3
        types = [v["type"] for v in values]
        assert "declared" in types
        assert "from_rule" in types
        assert "inferred" in types
    
    def test_categorize_rule_path(self):
        tracker = CoherenceTracker()
        
        assert tracker._categorize_rule_path("finance.capital") == "finance"
        assert tracker._categorize_rule_path("privacy.audit") == "privacy"
        assert tracker._categorize_rule_path("autonomy.levels") == "autonomy"
        assert tracker._categorize_rule_path("unknown.path") == "general"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

