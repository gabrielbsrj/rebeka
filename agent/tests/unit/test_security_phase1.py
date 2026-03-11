# tests/unit/test_security_phase1.py
"""
Testes de Invariantes — Security Phase 1.

INVARIANTE: Capital nunca excede max_total.
INVARIANTE: Confiança calibrada nunca excede historical + max_overstatement.
INVARIANTE: Hash do YAML verificado na inicialização.
"""

import os
import pytest
from core.security_phase1 import SecurityPhase1


@pytest.fixture
def security():
    """Cria SecurityPhase1 com o arquivo real."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "security_phase1.yaml"
    )
    if not os.path.exists(config_path):
        pytest.skip("security_phase1.yaml não encontrado")
    return SecurityPhase1(config_path)


class TestSecurityPhase1:
    """Testes de invariantes de segurança."""

    def test_file_hash_is_calculated(self, security):
        """Hash do YAML deve ser calculado na inicialização."""
        assert security.file_hash is not None
        assert len(security.file_hash) == 64  # SHA-256

    def test_hash_is_deterministic(self, security):
        """Hash deve ser determinístico — mesmo arquivo = mesmo hash."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "security_phase1.yaml"
        )
        security2 = SecurityPhase1(config_path)
        assert security.file_hash == security2.file_hash

    def test_nonexistent_file_raises(self):
        """Arquivo inexistente deve levantar FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SecurityPhase1("/caminho/inexistente.yaml")

    def test_paper_trading_required(self, security):
        """Paper trading deve ser obrigatório na Fase 1."""
        assert security.is_paper_trading_required()

    def test_max_real_capital(self, security):
        """Capital máximo deve ser $1000 na Fase 1."""
        max_capital = security.get_max_real_capital()
        assert max_capital == 1000.0

    def test_capital_limit_paper_always_passes(self, security):
        """Paper trading deve sempre passar verificação de capital."""
        assert security.check_capital_limit(999999, "paper")

    def test_capital_limit_real_enforced(self, security):
        """Real trading acima do limite deve ser bloqueado."""
        max_capital = security.get_max_real_capital()
        max_fraction = security.get_max_single_operation_fraction()
        max_single = max_capital * max_fraction

        # Acima do limite
        assert not security.check_capital_limit(max_single + 1, "real")

        # No limite
        assert security.check_capital_limit(max_single, "real")

    def test_confidence_calibration_pass(self, security):
        """Confiança dentro da calibração deve passar."""
        assert security.check_confidence_calibration(
            reported_confidence=0.65,
            historical_success_rate=0.60,
        )

    def test_confidence_calibration_fail(self, security):
        """Confiança acima da calibração deve falhar."""
        assert not security.check_confidence_calibration(
            reported_confidence=0.90,
            historical_success_rate=0.55,
        )

    def test_non_transcendable_restrictions(self, security):
        """Restrições não-transcendáveis devem existir."""
        restrictions = security.get_non_transcendable_restrictions()
        assert isinstance(restrictions, list)

    def test_autonomy_level_conservative_default(self, security):
        """Nível de autonomia padrão deve ser conservador."""
        level = security.get_autonomy_level("unknown_change")
        assert level == "user_only"

