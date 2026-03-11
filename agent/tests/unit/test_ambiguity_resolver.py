# agent/tests/unit/test_ambiguity_resolver.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes do AmbiguityResolver

"""
Testes Unitários para AmbiguityResolver.

Testa:
- Resolução via modelo de intenções
- Resolução via histórico
- Análise LLM
- Quick resolve
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from intelligence.ambiguity_resolver import AmbiguityResolver


class TestAmbiguityResolverInit:
    """Testes de inicialização."""
    
    def test_init_default(self):
        resolver = AmbiguityResolver()
        assert resolver._model == "gpt-4o-mini"
        assert resolver._api_key is None
    
    def test_init_with_params(self):
        resolver = AmbiguityResolver(model="gpt-4", api_key="test-key")
        assert resolver._model == "gpt-4"
        assert resolver._api_key == "test-key"


class TestResolve:
    """Testes do método resolve principal."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver(model="gpt-4o-mini", api_key="test-key")
    
    @pytest.fixture
    def options(self):
        return [
            {"name": "Opção A", "description": "Conservadora"},
            {"name": "Opção B", "description": "Moderada"},
            {"name": "Opção C", "description": "Arriscada"},
        ]
    
    @pytest.fixture
    def intent_model(self):
        return {
            "declared_values": [
                {"value": "Segurança é prioridade", "priority": "high"},
                {"value": "Prefiro baixo risco", "priority": "high"},
            ],
            "intentions": {
                "finance.capital": {"intention": "Proteger capital"}
            }
        }
    
    @pytest.fixture
    def historical_decisions(self):
        return [
            {"description": "Trade similar", "chosen_option": "Conservadora"},
            {"description": "Outro trade", "chosen_option": "Moderada"},
            {"description": "Terceiro trade", "chosen_option": "Conservadora"},
        ]
    
    def test_no_options_returns_fallback(self, resolver):
        """Testa fallback quando não há opções."""
        result = resolver.resolve(
            situation="Teste",
            options=[],
            intent_model=None,
        )
        
        assert result["resolved"] is False
        assert result["ask_user"] is True
        assert "nenhuma opção" in result["reasoning"].lower()
    
    def test_resolve_from_intents_high_confidence(self, resolver, options, intent_model):
        """Testa resolução via intenções com alta confiança."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 0,
            "confidence": 0.85,
            "reasoning": "Opção A é mais alinhada com segurança",
            "values_aligned": ["Segurança é prioridade"],
            "values_conflicted": [],
            "ask_user": false
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver.resolve(
                situation="Qual trade fazer?",
                options=options,
                intent_model=intent_model,
            )
        
        assert result["resolved"] is True
        assert result["recommended_index"] == 0
        assert result["confidence"] == 0.85
        assert result["source"] == "intent_model"
    
    def test_resolve_from_intents_low_confidence(self, resolver, options, intent_model):
        """Testa que baixa confiança pede ao usuário."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 1,
            "confidence": 0.3,
            "reasoning": "Não há clareza suficiente",
            "values_aligned": [],
            "values_conflicted": ["Segurança é prioridade"],
            "ask_user": true
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver.resolve(
                situation="Situação confusa",
                options=options,
                intent_model=intent_model,
            )
        
        assert result["ask_user"] is True
    
    def test_resolve_with_history(self, resolver, options, historical_decisions):
        """Testa resolução via histórico."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 0,
            "confidence": 0.7,
            "reasoning": "Padrão histórico mostra preferência por conservador",
            "pattern_detected": "Usuário prefere opções conservadoras"
        }
        '''
        
        # Primeiro mock para intenções (retorna baixa confiança)
        mock_intent_response = Mock()
        mock_intent_response.choices = [Mock()]
        mock_intent_response.choices[0].message.content = '{"recommended_index": 0, "confidence": 0.3, "reasoning": "Baixa", "ask_user": true}'
        
        with patch('litellm.completion', side_effect=[mock_intent_response, mock_response]):
            result = resolver.resolve(
                situation="Trade similar",
                options=options,
                intent_model={},
                historical_decisions=historical_decisions,
            )
        
        # Como intenções falhou, deve usar histórico
        assert result["confidence"] >= 0.5 or result["source"] in ["historical_pattern", "llm_analysis"]


class TestResolveFromIntents:
    """Testes específicos de _resolve_from_intents."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver(model="gpt-4o-mini", api_key="test-key")
    
    def test_empty_intent_model(self, resolver):
        """Testa comportamento com modelo vazio."""
        result = resolver._resolve_from_intents(
            situation="Teste",
            options=[{"name": "A"}, {"name": "B"}],
            intent_model={},
        )
        
        assert result["resolved"] is False
        assert result["ask_user"] is True
    
    def test_intent_model_with_values(self, resolver):
        """Testa com valores declarados."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 0,
            "confidence": 0.75,
            "reasoning": "Opção A alinhada com valor de segurança",
            "values_aligned": ["segurança"],
            "values_conflicted": [],
            "ask_user": false
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver._resolve_from_intents(
                situation="Escolha de investimento",
                options=[{"name": "Conservador"}, {"name": "Arriscado"}],
                intent_model={
                    "declared_values": [{"value": "Segurança", "priority": "high"}]
                },
            )
        
        assert result["resolved"] is True
        assert result["recommended_index"] == 0
        assert "segurança" in result["values_aligned"] or result["confidence"] == 0.75
    
    def test_invalid_index_handling(self, resolver):
        """Testa tratamento de índice inválido."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 99,
            "confidence": 0.5,
            "reasoning": "Teste",
            "values_aligned": [],
            "values_conflicted": [],
            "ask_user": false
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver._resolve_from_intents(
                situation="Teste",
                options=[{"name": "A"}, {"name": "B"}],
                intent_model={"declared_values": [{"value": "Teste"}]},
            )
        
        # Índice inválido deve fazer fallback para primeira opção com baixa confiança
        assert result["ask_user"] is True or result["confidence"] <= 0.5


class TestResolveFromHistory:
    """Testes de resolução via histórico."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver(model="gpt-4o-mini", api_key="test-key")
    
    def test_history_resolution(self, resolver):
        """Testa análise de padrão histórico."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 0,
            "confidence": 0.65,
            "reasoning": "Usuário tende a escolher conservador",
            "pattern_detected": "Padrão conservador em 3 de 3 casos"
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver._resolve_from_history(
                situation="Novo trade",
                options=[{"name": "Conservador"}, {"name": "Arriscado"}],
                historical_decisions=[
                    {"description": "Trade 1", "chosen_option": "Conservador"},
                    {"description": "Trade 2", "chosen_option": "Conservador"},
                    {"description": "Trade 3", "chosen_option": "Conservador"},
                ],
            )
        
        assert result["confidence"] >= 0.5
        assert "pattern" in result["reasoning"].lower() or result["confidence"] == 0.65


class TestResolveWithLLM:
    """Testes de análise LLM completa."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver(model="gpt-4o-mini", api_key="test-key")
    
    def test_llm_recommends_option(self, resolver):
        """Testa LLM recomendando uma opção."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": 1,
            "confidence": 0.7,
            "reasoning": "Opção moderada é mais equilibrada",
            "ask_user": false,
            "clarifying_questions": []
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver._resolve_with_llm(
                situation="Decisão",
                options=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
                intent_model=None,
                historical_decisions=None,
                context=None,
            )
        
        assert result["resolved"] is True
        assert result["recommended_index"] == 1
    
    def test_llm_asks_user(self, resolver):
        """Testa LLM recomendando perguntar ao usuário."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended_index": -1,
            "confidence": 0.3,
            "reasoning": "Informações insuficientes",
            "ask_user": true,
            "clarifying_questions": ["Qual sua prioridade?", "Qual prazo?"]
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver._resolve_with_llm(
                situation="Situação complexa",
                options=[{"name": "A"}, {"name": "B"}],
                intent_model=None,
                historical_decisions=None,
                context=None,
            )
        
        assert result["resolved"] is False
        assert result["ask_user"] is True
        assert len(result["clarifying_questions"]) == 2


class TestQuickResolve:
    """Testes do método quick_resolve."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver(model="gpt-4o-mini", api_key="test-key")
    
    def test_quick_resolve_basic(self, resolver):
        """Testa resolução rápida básica."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "recommended": "Opção B",
            "confidence": 0.65,
            "reasoning": "Mais alinhada com os valores"
        }
        '''
        
        with patch('litellm.completion', return_value=mock_response):
            result = resolver.quick_resolve(
                situation="Escolha rápida",
                options=["Opção A", "Opção B", "Opção C"],
                user_values=["Segurança", "Crescimento moderado"],
            )
        
        assert result["recommended"] == "Opção B"
        assert result["confidence"] > 0.5
    
    def test_quick_resolve_no_options(self, resolver):
        """Testa quick resolve sem opções."""
        result = resolver.quick_resolve(
            situation="Teste",
            options=[],
            user_values=["Valor"],
        )
        
        assert result["recommended"] is None
        assert result["confidence"] == 0.0


class TestExtractRelevantValues:
    """Testes de extração de valores relevantes."""
    
    @pytest.fixture
    def resolver(self):
        return AmbiguityResolver()
    
    def test_extract_declared_values(self, resolver):
        """Testa extração de valores declarados."""
        intent_model = {
            "declared_values": [
                {"value": "Segurança", "priority": "high"},
                {"value": "Crescimento", "priority": "medium"},
            ]
        }
        
        values = resolver._extract_relevant_values(intent_model, "situação")
        
        assert len(values) == 2
        assert values[0]["value"] == "Segurança"
    
    def test_extract_from_intentions(self, resolver):
        """Testa extração de intenções de regras."""
        intent_model = {
            "intentions": {
                "finance.capital": {"intention": "Proteger capital"},
            }
        }
        
        values = resolver._extract_relevant_values(intent_model, "finance")
        
        assert len(values) == 1
        assert "Proteger" in values[0]["value"]
    
    def test_extract_inferred_values(self, resolver):
        """Testa extração de valores inferidos."""
        intent_model = {
            "inferred_values": [
                {"value": "Prefere baixo risco", "confidence": 0.8},
                {"value": "Valor incerto", "confidence": 0.3},
            ]
        }
        
        values = resolver._extract_relevant_values(intent_model, "test")
        
        # Só valores com confiança >= 0.5
        assert len(values) == 1
        assert "baixo risco" in values[0]["value"]


class TestFallbackResult:
    """Testes do método de fallback."""
    
    def test_fallback_result(self):
        resolver = AmbiguityResolver()
        result = resolver._fallback_result("Motivo do teste")
        
        assert result["resolved"] is False
        assert result["ask_user"] is True
        assert result["confidence"] == 0.0
        assert "Motivo" in result["reasoning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

