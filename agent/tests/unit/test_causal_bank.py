# tests/unit/test_causal_bank.py
"""
Testes de Invariantes — Banco de Causalidade.

INVARIANTE: insert_signal() calcula hash e atualiza SMT.
INVARIANTE: Toda inserção registra origem e timestamp.
INVARIANTE: Padrão causal DEVE ter mecanismo causal.
INVARIANTE: Hipótese DEVE ter uncertainty_acknowledged.
"""

import pytest
from shared.database.causal_bank import CausalBank


@pytest.fixture
def bank():
    """Cria um CausalBank com SQLite em memória."""
    from shared.database.causal_bank import CausalBank
    from shared.database.models import Base
    import os
    os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
    cb = CausalBank("sqlite:///:memory:", origin="test")
    # Limpar qualquer lixo residual global entre testes
    Base.metadata.drop_all(cb._engine)
    Base.metadata.create_all(cb._engine)
    yield cb


class TestCausalBankSignals:
    """Testes de inserção de sinais."""

    def test_insert_signal_returns_id(self, bank):
        """Inserção deve retornar ID canônico."""
        signal_id = bank.insert_signal({
            "domain": "geopolitics",
            "source": "reuters_rss",
            "title": "Teste de sinal",
            "content": "Conteúdo do sinal",
            "relevance_score": 0.8,
        })

        assert signal_id is not None
        assert len(signal_id) == 36  # UUID format

    def test_insert_signal_updates_smt(self, bank):
        """Inserção deve atualizar a SMT."""
        root_before = bank.merkle_root

        bank.insert_signal({
            "domain": "geopolitics",
            "source": "reuters_rss",
            "title": "Teste",
            "relevance_score": 0.5,
        })

        assert bank.merkle_root != root_before
        assert bank.leaf_count == 1

    def test_get_similar_signals(self, bank):
        """Busca de sinais similares deve funcionar."""
        bank.insert_signal({
            "domain": "macro",
            "source": "test",
            "title": "Sinal 1",
            "relevance_score": 0.9,
        })
        bank.insert_signal({
            "domain": "macro",
            "source": "test",
            "title": "Sinal 2",
            "relevance_score": 0.7,
        })
        bank.insert_signal({
            "domain": "geopolitics",
            "source": "test",
            "title": "Sinal 3",
            "relevance_score": 0.5,
        })

        macro_signals = bank.get_similar_signals("macro", limit=5)
        assert len(macro_signals) == 2


class TestCausalBankPatterns:
    """Testes de inserção de padrões."""

    def test_causal_pattern_requires_mechanism(self, bank):
        """Padrão causal sem mecanismo deve levantar exceção."""
        with pytest.raises(ValueError, match="causal_mechanism"):
            bank.insert_causal_pattern({
                "domain": "macro",
                "cause_description": "FED sobe juros",
                "effect_description": "Mercado cai",
                "confidence": 0.8,
            })

    def test_causal_pattern_with_mechanism(self, bank):
        """Padrão causal com mecanismo deve ser inserido."""
        pattern_id = bank.insert_causal_pattern({
            "domain": "macro",
            "cause_description": "FED sobe juros",
            "effect_description": "Mercado cai",
            "causal_mechanism": "Custo de capital aumenta, reduzindo valuations",
            "confidence": 0.8,
        })

        assert pattern_id is not None

    def test_correlation_candidate_insertion(self, bank):
        """Correlação pode ser inserida sem mecanismo causal."""
        cid = bank.insert_correlation_candidate({
            "domain": "crypto",
            "variable_a": "Bitcoin volume",
            "variable_b": "ETH price",
            "correlation_strength": 0.7,
        })

        assert cid is not None


class TestCausalBankHypotheses:
    """Testes de inserção de hipóteses."""

    def test_hypothesis_requires_uncertainty(self, bank):
        """Hipótese sem uncertainty_acknowledged deve levantar exceção."""
        with pytest.raises(ValueError, match="uncertainty_acknowledged"):
            bank.insert_hypothesis({
                "reasoning": "Teste",
                "signals_used": [],
                "predicted_movement": {"direction": "up"},
                "confidence_calibrated": 0.6,
                "action": {"type": "buy"},
            })

    def test_hypothesis_with_uncertainty(self, bank):
        """Hipótese com uncertainty deve ser inserida."""
        hid = bank.insert_hypothesis({
            "reasoning": "Teste de hipótese",
            "signals_used": ["signal_1"],
            "predicted_movement": {"direction": "up"},
            "confidence_calibrated": 0.6,
            "uncertainty_acknowledged": "Dados limitados a 1 sinal",
            "action": {"type": "buy"},
        })

        assert hid is not None


class TestCausalBankIntegrity:
    """Testes de integridade."""

    def test_verify_integrity_existing_record(self, bank):
        """Integridade de registro existente deve ser verificável."""
        signal_id = bank.insert_signal({
            "domain": "test",
            "source": "test",
            "title": "Test",
            "relevance_score": 0.5,
        })

        assert bank.verify_integrity(signal_id)

    def test_verify_integrity_nonexistent(self, bank):
        """Verificação de registro inexistente deve retornar False."""
        assert not bank.verify_integrity("nonexistent_id")

    def test_multiple_inserts_increase_leaf_count(self, bank):
        """Múltiplas inserções devem aumentar contagem de folhas."""
        for i in range(5):
            bank.insert_signal({
                "domain": "test",
                "source": "test",
                "title": f"Signal {i}",
                "relevance_score": 0.5,
            })

        assert bank.leaf_count == 5

    def test_performance_stats_empty(self, bank):
        """Stats vazias devem retornar zeros."""
        stats = bank.get_performance_stats()
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0

    def test_append_behavioral_evidence_is_append_only(self, bank):
        """Nova evidência de comportamento cria registro, não muta o anterior."""
        
        # Inserir padrão base
        pattern_id = bank.insert_behavioral_pattern({
            "domain": "trading",
            "pattern_type": "vies_alta",
            "description": "Viés de alta estrutural",
            "confidence": 0.5,
            "confirmation_count": 1,
            "potentially_limiting": True,
            "evidence": [{"source": "initial_observation"}],
        })
        
        # Padrão base inserido via SMT?
        assert bank.verify_integrity(pattern_id)
        
        # Adicionar evidência (append-only)
        new_evidence = {"source": "second_observation"}
        new_pattern_id = bank.append_behavioral_evidence(pattern_id, new_evidence)
        
        # Verifica se gerou novo ID
        assert new_pattern_id != pattern_id
        
        # Verifica integridade do novo registro
        assert bank.verify_integrity(new_pattern_id)
        
        # Lê ambos para comparar
        from shared.database.models import BehavioralPattern
        with bank._SessionFactory() as session:
            orig = session.query(BehavioralPattern).filter_by(id=pattern_id).first()
            new = session.query(BehavioralPattern).filter_by(id=new_pattern_id).first()
            
            assert orig.confirmation_count == 1
            assert new.confirmation_count == 2
            
            assert len(orig.evidence) == 1
            assert len(new.evidence) == 2
            
            assert new.parent_pattern_id == pattern_id

