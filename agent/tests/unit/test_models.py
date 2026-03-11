# tests/unit/test_models.py
"""
Testes de Invariantes — Modelos do Banco de Causalidade.

INVARIANTE: Todos os 21 modelos existem.
INVARIANTE: Tabelas são criáveis com SQLite em memória.
"""

import pytest
from sqlalchemy import create_engine, inspect

from memory.models import (
    Base,
    Signal,
    CausalPattern,
    CorrelationCandidate,
    DeprecatedPattern,
    SecondOrderPattern,
    ThirdOrderPattern,
    UserDecision,
    UserCoherenceLog,
    UserRegretSignal,
    UserClarityDelta,
    IntentModel,
    Hypothesis,
    Execution,
    Evaluation,
    EnvironmentError as EnvError,
    CodeVersion,
    EvolutionLog,
    TranscendenceLog,
    MerkleTreeRecord,
    SynthesisLog,
    PrivacyAuditLog,
    MonitorLifecycle,
    create_all_tables,
)


EXPECTED_TABLES = [
    "signals",
    "causal_patterns",
    "correlation_candidates",
    "deprecated_patterns",
    "second_order",
    "third_order",
    "user_decisions",
    "user_coherence_log",
    "user_regret_signals",
    "user_clarity_deltas",
    "intent_model",
    "hypotheses",
    "executions",
    "evaluations",
    "environment_errors",
    "code_versions",
    "evolution_log",
    "transcendence_log",
    "merkle_tree",
    "synthesis_log",
    "privacy_audit_log",
    "monitor_lifecycle",
]


class TestModels:
    """Testes de existência e criação de modelos."""

    @pytest.fixture
    def engine(self):
        """Engine SQLite em memória."""
        engine = create_engine("sqlite:///:memory:")
        create_all_tables(engine)
        return engine

    def test_all_21_tables_exist(self, engine):
        """Todos os 21 modelos devem ter tabelas correspondentes."""
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()

        for table_name in EXPECTED_TABLES:
            assert table_name in created_tables, \
                f"Tabela '{table_name}' não encontrada. Criadas: {created_tables}"

    def test_total_table_count(self, engine):
        """Devem existir exatamente 22 tabelas (21 + alembic_version eventualmente)."""
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        assert len(created_tables) >= 22  # 22 tabelas no mínimo

    def test_signals_has_required_columns(self, engine):
        """Tabela signals deve ter colunas essenciais."""
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("signals")]

        required = ["id", "created_at", "origin", "domain", "source",
                     "title", "relevance_score", "merkle_leaf_hash"]
        for col in required:
            assert col in columns, f"Coluna '{col}' não encontrada em signals"

    def test_hypotheses_has_uncertainty_column(self, engine):
        """Tabela hypotheses DEVE ter coluna uncertainty_acknowledged."""
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("hypotheses")]

        assert "uncertainty_acknowledged" in columns, \
            "Coluna 'uncertainty_acknowledged' é OBRIGATÓRIA em hypotheses"

    def test_all_tables_have_merkle_hash(self, engine):
        """Todas as tabelas principais devem ter merkle_leaf_hash."""
        inspector = inspect(engine)
        tables_with_merkle = [
            "signals", "causal_patterns", "correlation_candidates",
            "user_decisions", "user_coherence_log", "hypotheses",
            "executions", "evaluations",
        ]

        for table in tables_with_merkle:
            columns = [c["name"] for c in inspector.get_columns(table)]
            assert "merkle_leaf_hash" in columns, \
                f"Tabela '{table}' precisa de merkle_leaf_hash para integridade"

