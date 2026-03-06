# agent/tests/unit/test_decision_learner.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes do DecisionLearner

"""
Testes Unitários para DecisionLearner.

Testa:
- Registro de decisões
- Extração de valores via LLM
- Predição de decisões
- Análise de estilo
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.intent.decision_learner import DecisionLearner


class TestDecisionLearnerInit:
    """Testes de inicialização."""
    
    def test_init_default(self):
        learner = DecisionLearner()
        assert learner._min_decisions == 10
        assert learner._causal_bank is None
        assert len(learner._decisions) == 0
    
    def test_init_with_params(self):
        mock_bank = Mock()
        learner = DecisionLearner(
            model="gpt-4",
            api_key="test-key",
            causal_bank=mock_bank,
            min_decisions_for_prediction=5,
        )
        assert learner._model == "gpt-4"
        assert learner._api_key == "test-key"
        assert learner._causal_bank == mock_bank
        assert learner._min_decisions == 5


class TestRecordDecision:
    """Testes do método record_decision."""
    
    @pytest.fixture
    def learner(self):
        return DecisionLearner(model="gpt-4o-mini", api_key="test-key")
    
    def test_record_basic_decision(self, learner):
        """Testa registro básico de decisão."""
        decision = {
            "decision_type": "accept",
            "domain": "finance",
            "chosen_option": "trade_a",
        }
        
        result = learner.record_decision(decision, extract_values=False)
        
        assert result["registered"] is True
        assert result["total_decisions"] == 1
        assert result["can_predict"] is False
    
    def test_record_with_extraction(self, learner):
        """Testa registro com extração de valores."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "values": [
                {"value": "Prefere segurança", "confidence": 0.8, "evidence": "Escolheu opção conservadora", "category": "security"}
            ],
            "decision_style": "conservative",
            "context_sensitivity": "high"
        }
        '''
        
        decision = {
            "decision_type": "accept",
            "domain": "finance",
            "chosen_option": "conservador",
            "reasoning": "Menos risco",
        }
        
        with patch('litellm.completion', return_value=mock_response):
            result = learner.record_decision(decision, extract_values=True)
        
        assert result["registered"] is True
        assert result["extracted_values"] is not None
        assert len(learner._inferred_values) == 1
    
    def test_record_updates_patterns(self, learner):
        """Testa que registro atualiza padrões."""
        learner.record_decision({"decision_type": "accept", "domain": "finance"}, extract_values=False)
        learner.record_decision({"decision_type": "accept", "domain": "finance"}, extract_values=False)
        learner.record_decision({"decision_type": "reject", "domain": "finance"}, extract_values=False)
        
        assert learner._value_patterns["tendency_accept"] == 2
        assert learner._value_patterns["tendency_reject"] == 1
        assert learner._value_patterns["domain_finance"] == 3
    
    def test_record_with_bank(self):
        """Testa persistência no banco."""
        mock_bank = Mock()
        learner = DecisionLearner(causal_bank=mock_bank)
        
        decision = {"decision_type": "test", "domain": "test"}
        learner.record_decision(decision, extract_values=False)
        
        mock_bank.insert_user_decision.assert_called_once()


class TestCanPredict:
    """Testes de verificação de capacidade de predição."""
    
    def test_cannot_predict_with_few_decisions(self):
        learner = DecisionLearner(min_decisions_for_prediction=10)
        
        for i in range(5):
            learner.record_decision({"decision_type": "test"}, extract_values=False)
        
        assert learner.can_predict() is False
    
    def test_can_predict_with_enough_decisions(self):
        learner = DecisionLearner(min_decisions_for_prediction=5)
        
        for i in range(5):
            learner.record_decision({"decision_type": "test"}, extract_values=False)
        
        assert learner.can_predict() is True


class TestGetValueProfile:
    """Testes do método get_value_profile."""
    
    @pytest.fixture
    def learner(self):
        return DecisionLearner()
    
    def test_empty_profile(self, learner):
        """Testa perfil vazio."""
        profile = learner.get_value_profile()
        
        assert profile["total_decisions_observed"] == 0
        assert profile["can_predict"] is False
        assert profile["accept_rate"] == 0.0
    
    def test_profile_with_decisions(self, learner):
        """Testa perfil com decisões."""
        learner.record_decision({"decision_type": "accept"}, extract_values=False)
        learner.record_decision({"decision_type": "accept"}, extract_values=False)
        learner.record_decision({"decision_type": "reject"}, extract_values=False)
        
        profile = learner.get_value_profile()
        
        assert profile["total_decisions_observed"] == 3
        assert profile["accept_rate"] == pytest.approx(2/3)
        assert profile["reject_rate"] == pytest.approx(1/3)


class TestPredictDecision:
    """Testes do método predict_decision."""
    
    @pytest.fixture
    def learner(self):
        return DecisionLearner(model="gpt-4o-mini", api_key="test-key", min_decisions_for_prediction=3)
    
    def test_cannot_predict_without_data(self, learner):
        """Testa que não prevê sem dados."""
        result = learner.predict_decision({"domain": "finance"})
        assert result is None
    
    def test_predict_from_context(self, learner):
        """Testa predição baseada em contexto similar."""
        # Registrar decisões similares
        for i in range(5):
            learner.record_decision({
                "decision_type": "accept",
                "domain": "finance",
                "context": {"risk_level": "low", "urgency": "normal"},
                "chosen_option": "conservador",
            }, extract_values=False)
        
        result = learner.predict_decision({
            "domain": "finance",
            "risk_level": "low",
            "urgency": "normal",
        })
        
        assert result is not None
        assert result["predicted_action"] == "conservador"
        assert result["confidence"] > 0.5
        assert result["source"] == "context_pattern"
    
    def test_predict_from_profile(self, learner):
        """Testa predição baseada em perfil."""
        # Registrar muitas aceitações
        for i in range(8):
            learner.record_decision({
                "decision_type": "accept",
                "domain": "test",
                "context": {},
            }, extract_values=False)
        
        # Registrar poucas rejeições
        for i in range(2):
            learner.record_decision({
                "decision_type": "reject",
                "domain": "test",
                "context": {},
            }, extract_values=False)
        
        result = learner.predict_decision({"domain": "new_domain"})
        
        assert result is not None
        assert result["predicted_action"] == "accept"


class TestPredictWithLLM:
    """Testes da predição via LLM."""
    
    @pytest.fixture
    def learner(self):
        return DecisionLearner(model="gpt-4o-mini", api_key="test-key", min_decisions_for_prediction=2)
    
    def test_llm_predicts_accept(self, learner):
        """Testa LLM prevendo aceitação."""
        # Dados insuficientes para contexto
        learner.record_decision({"decision_type": "test", "context": {}}, extract_values=False)
        learner.record_decision({"decision_type": "test", "context": {}}, extract_values=False)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "predicted_action": "accept",
            "confidence": 0.75,
            "reasoning": "Perfil mostra tendência à aceitação",
            "alternative": "reject"
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = learner._predict_with_llm({"domain": "test"}, learner.get_value_profile())
        
        assert result["predicted_action"] == "accept"
        assert result["confidence"] == 0.75
    
    def test_llm_asks_user(self, learner):
        """Testa LLM recomendando perguntar ao usuário."""
        learner.record_decision({"decision_type": "test"}, extract_values=False)
        learner.record_decision({"decision_type": "test"}, extract_values=False)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "predicted_action": "ask_user",
            "confidence": 0.3,
            "reasoning": "Dados insuficientes para prever",
            "alternative": null
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = learner._predict_with_llm({"domain": "test"}, learner.get_value_profile())
        
        assert result["predicted_action"] == "ask_user"


class TestExtractValues:
    """Testes da extração de valores via LLM."""
    
    @pytest.fixture
    def learner(self):
        return DecisionLearner(model="gpt-4o-mini", api_key="test-key")
    
    def test_extract_values_success(self, learner):
        """Testa extração bem-sucedida."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "values": [
                {"value": "Segurança primeiro", "confidence": 0.9, "evidence": "Evitou risco alto", "category": "security"},
                {"value": "Cautela em decisões financeiras", "confidence": 0.7, "evidence": "Preferiu esperar", "category": "risk"}
            ],
            "decision_style": "conservative",
            "context_sensitivity": "high"
        }
        '''
        
        decision = {
            "decision_type": "reject",
            "chosen_option": None,
            "rejected_options": ["trade_risky"],
            "reasoning": "Risco muito alto",
        }
        
        with patch('litellm.completion', return_value=mock_response):
            result = learner._extract_values_from_decision(decision)
        
        assert result is not None
        assert len(result["values"]) == 2
        assert result["decision_style"] == "conservative"
    
    def test_extract_values_error(self, learner):
        """Testa tratamento de erro na extração."""
        with patch('litellm.completion', side_effect=Exception("API Error")):
            result = learner._extract_values_from_decision({"decision_type": "test"})
        
        assert result is None


class TestGetDecisionStyle:
    """Testes do método get_decision_style."""
    
    def test_style_unknown_with_few_decisions(self):
        learner = DecisionLearner()
        style = learner.get_decision_style()
        
        assert style["style"] == "unknown"
        assert style["confidence"] == 0.0
    
    def test_style_trusting(self):
        learner = DecisionLearner()
        
        for i in range(10):
            learner.record_decision({"decision_type": "accept", "context": {}}, extract_values=False)
        
        style = learner.get_decision_style()
        
        assert style["style"] == "trusting"
        assert style["accept_rate"] > 0.6
    
    def test_style_conservative(self):
        learner = DecisionLearner()
        
        for i in range(10):
            learner.record_decision({"decision_type": "reject", "context": {}}, extract_values=False)
        
        style = learner.get_decision_style()
        
        assert style["style"] == "conservative"
        assert style["reject_rate"] > 0.6
    
    def test_style_deliberative(self):
        learner = DecisionLearner()
        
        for i in range(5):
            learner.record_decision({"decision_type": "accept", "context": {}}, extract_values=False)
        for i in range(4):
            learner.record_decision({"decision_type": "modify", "context": {}}, extract_values=False)
        
        style = learner.get_decision_style()
        
        assert style["style"] == "deliberative"
        assert style["modify_rate"] > 0.3


class TestGetDecisionsByDomain:
    """Testes do filtro por domínio."""
    
    def test_filter_by_domain(self):
        learner = DecisionLearner()
        
        learner.record_decision({"decision_type": "test", "domain": "finance"}, extract_values=False)
        learner.record_decision({"decision_type": "test", "domain": "finance"}, extract_values=False)
        learner.record_decision({"decision_type": "test", "domain": "health"}, extract_values=False)
        
        finance_decisions = learner.get_decisions_by_domain("finance")
        
        assert len(finance_decisions) == 2
        assert all(d["domain"] == "finance" for d in finance_decisions)


class TestGetRecentDecisions:
    """Testes do filtro temporal."""
    
    def test_recent_decisions(self):
        learner = DecisionLearner()
        
        # Decisões recentes
        for i in range(5):
            learner.record_decision({"decision_type": "test"}, extract_values=False)
        
        recent = learner.get_recent_decisions(days=30)
        
        assert len(recent) == 5


class TestClearOldDecisions:
    """Testes da limpeza de decisões antigas."""
    
    def test_clear_removes_old(self):
        learner = DecisionLearner()
        
        # Adicionar decisões
        for i in range(10):
            learner.record_decision({"decision_type": "test"}, extract_values=False)
        
        # Simular decisões antigas
        old_decision = {
            "timestamp": "2020-01-01T00:00:00+00:00",
            "decision_type": "old",
        }
        learner._decisions.insert(0, old_decision)
        
        removed = learner.clear_old_decisions(days=365)
        
        assert removed == 1
        assert len(learner._decisions) == 10


class TestContextKey:
    """Testes da geração de chave de contexto."""
    
    def test_context_key_generation(self):
        learner = DecisionLearner()
        
        key1 = learner._get_context_key({
            "domain": "finance",
            "context": {"risk_level": "high", "urgency": "normal"}
        })
        
        key2 = learner._get_context_key({
            "domain": "finance",
            "context": {"risk_level": "high", "urgency": "normal"}
        })
        
        key3 = learner._get_context_key({
            "domain": "finance",
            "context": {"risk_level": "low", "urgency": "normal"}
        })
        
        assert key1 == key2
        assert key1 != key3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
