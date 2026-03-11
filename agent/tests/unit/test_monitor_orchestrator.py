# agent/tests/unit/test_monitor_orchestrator.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — testes para MonitorOrchestrator v2.0

"""
Testes unitários para MonitorOrchestrator.

INTENÇÃO: Garantir que a orquestração dinâmica de monitores funciona
corretamente, incluindo criação/pausa por relevância e integração
com o Banco de Causalidade.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch


class TestMonitorOrchestratorInit:
    """Testes de inicialização."""

    def test_init_without_bank(self):
        """Deve inicializar sem causal_bank."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        assert orchestrator._causal_bank is None
        assert orchestrator._active_monitors == {}
        assert orchestrator._paused_monitors == {}

    def test_init_with_bank(self):
        """Deve aceitar causal_bank opcional."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        mock_bank = Mock()
        orchestrator = MonitorOrchestrator(causal_bank=mock_bank)
        assert orchestrator._causal_bank is mock_bank


class TestSetDomainRelevance:
    """Testes para set_domain_relevance."""

    def test_set_relevance_basic(self):
        """Deve definir relevância de um domínio."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.set_domain_relevance("finance", 0.8)
        
        assert orchestrator.get_domain_relevance("finance") == 0.8

    def test_set_relevance_invalid_high(self):
        """Deve rejeitar relevância > 1.0."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        
        with pytest.raises(ValueError):
            orchestrator.set_domain_relevance("finance", 1.5)

    def test_set_relevance_invalid_low(self):
        """Deve rejeitar relevância < 0.0."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        
        with pytest.raises(ValueError):
            orchestrator.set_domain_relevance("finance", -0.1)

    def test_set_relevance_boundary_zero(self):
        """Deve aceitar relevância 0.0."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.set_domain_relevance("finance", 0.0)
        
        assert orchestrator.get_domain_relevance("finance") == 0.0

    def test_set_relevance_boundary_one(self):
        """Deve aceitar relevância 1.0."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.set_domain_relevance("finance", 1.0)
        
        assert orchestrator.get_domain_relevance("finance") == 1.0


class TestCreateMonitor:
    """Testes para create_monitor."""

    def test_create_basic(self):
        """Deve criar um monitor ativo."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        result = orchestrator.create_monitor(
            name="financial",
            domain="finance",
            config={"interval": 300},
        )
        
        assert result["status"] == "created"
        assert result["name"] == "financial"
        assert len(orchestrator.get_active_monitors()) == 1

    def test_create_duplicate(self):
        """Deve retornar already_active se já existe."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        result = orchestrator.create_monitor("financial", "finance", {})
        
        assert result["status"] == "already_active"

    def test_create_resumes_paused(self):
        """Deve resumir se monitor está pausado."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        result = orchestrator.create_monitor("financial", "finance", {})
        
        assert result["status"] == "resumed"
        assert "financial" in orchestrator._active_monitors

    def test_create_logs_to_bank(self):
        """Deve logar evento no banco se disponível."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        mock_bank = Mock()
        orchestrator = MonitorOrchestrator(causal_bank=mock_bank)
        
        orchestrator.create_monitor("financial", "finance", {})
        
        mock_bank.insert_monitor_lifecycle.assert_called_once()
        call_args = mock_bank.insert_monitor_lifecycle.call_args[0][0]
        assert call_args["action"] == "created"
        assert call_args["monitor_name"] == "financial"


class TestPauseMonitor:
    """Testes para pause_monitor."""

    def test_pause_basic(self):
        """Deve pausar um monitor ativo."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        
        result = orchestrator.pause_monitor("financial", "test reason")
        
        assert result["status"] == "paused"
        assert "financial" in orchestrator._paused_monitors
        assert "financial" not in orchestrator._active_monitors

    def test_pause_not_found(self):
        """Deve retornar not_found se não existe."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        result = orchestrator.pause_monitor("nonexistent", "test")
        
        assert result["status"] == "not_found"

    def test_pause_already_paused(self):
        """Deve retornar already_paused."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "first")
        
        result = orchestrator.pause_monitor("financial", "second")
        
        assert result["status"] == "already_paused"

    def test_pause_logs_to_bank(self):
        """Deve logar evento de pausa no banco."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        mock_bank = Mock()
        orchestrator = MonitorOrchestrator(causal_bank=mock_bank)
        orchestrator.create_monitor("financial", "finance", {})
        
        mock_bank.reset_mock()
        orchestrator.pause_monitor("financial", "test reason")
        
        mock_bank.insert_monitor_lifecycle.assert_called_once()
        call_args = mock_bank.insert_monitor_lifecycle.call_args[0][0]
        assert call_args["action"] == "paused"


class TestResumeMonitor:
    """Testes para resume_monitor."""

    def test_resume_basic(self):
        """Deve resumir um monitor pausado."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        result = orchestrator.resume_monitor("financial")
        
        assert result["status"] == "resumed"
        assert "financial" in orchestrator._active_monitors

    def test_resume_not_found(self):
        """Deve retornar not_found se não está pausado."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        result = orchestrator.resume_monitor("nonexistent")
        
        assert result["status"] == "not_found"

    def test_resume_active_monitor(self):
        """Deve retornar not_found para monitor já ativo."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        
        result = orchestrator.resume_monitor("financial")
        
        assert result["status"] == "not_found"


class TestDestroyMonitor:
    """Testes para destroy_monitor."""

    def test_destroy_active(self):
        """Deve destruir um monitor ativo."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        
        result = orchestrator.destroy_monitor("financial", "cleanup")
        
        assert result["status"] == "destroyed"
        assert "financial" not in orchestrator._active_monitors

    def test_destroy_paused(self):
        """Deve destruir um monitor pausado."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        result = orchestrator.destroy_monitor("financial", "cleanup")
        
        assert result["status"] == "destroyed"
        assert "financial" not in orchestrator._paused_monitors

    def test_destroy_not_found(self):
        """Deve retornar not_found."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        result = orchestrator.destroy_monitor("nonexistent", "cleanup")
        
        assert result["status"] == "not_found"


class TestAutoAdjustMonitors:
    """Testes para ajuste automático por relevância."""

    def test_create_on_high_relevance(self):
        """Deve criar monitores quando relevância sobe."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            RELEVANCE_THRESHOLD_CREATE,
        )
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_CREATE + 0.1)
        
        active = orchestrator.get_active_monitors()
        domains = [m["domain"] for m in active]
        assert "finance" in domains

    def test_pause_on_low_relevance(self):
        """Deve pausar monitores quando relevância cai."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            RELEVANCE_THRESHOLD_CREATE,
            RELEVANCE_THRESHOLD_PAUSE,
        )
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_CREATE + 0.1)
        assert len(orchestrator.get_active_monitors()) > 0
        
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_PAUSE - 0.1)
        
        assert len(orchestrator.get_active_monitors()) == 0
        assert len(orchestrator.get_paused_monitors()) > 0

    def test_no_adjust_unknown_domain(self):
        """Não deve ajustar monitores para domínio sem mapeamento."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.set_domain_relevance("unknown_domain_xyz", 0.9)
        
        assert len(orchestrator.get_active_monitors()) == 0

    def test_no_duplicate_create(self):
        """Não deve criar duplicatas ao ajustar relevância."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            RELEVANCE_THRESHOLD_CREATE,
        )
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_CREATE + 0.1)
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_CREATE + 0.2)
        
        active_names = [m["name"] for m in orchestrator.get_active_monitors()]
        assert len(set(active_names)) == len(active_names)


class TestCleanupStaleMonitors:
    """Testes para cleanup de monitores velhos."""

    def test_cleanup_destroys_old_paused(self):
        """Deve destruir monitores pausados há muito tempo."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            PAUSE_DAYS_BEFORE_DESTROY,
        )
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        old_time = datetime.now(timezone.utc) - timedelta(days=PAUSE_DAYS_BEFORE_DESTROY + 5)
        orchestrator._paused_monitors["financial"]["paused_at"] = old_time.isoformat()
        
        destroyed = orchestrator.cleanup_stale_monitors()
        
        assert "financial" in destroyed

    def test_cleanup_keeps_recent_paused(self):
        """Não deve destruir monitores pausados recentemente."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        destroyed = orchestrator.cleanup_stale_monitors()
        
        assert "financial" not in destroyed

    def test_cleanup_keeps_high_relevance(self):
        """Não deve destruir mesmo velhos se relevância é alta."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            PAUSE_DAYS_BEFORE_DESTROY,
            RELEVANCE_THRESHOLD_PAUSE,
        )
        
        orchestrator = MonitorOrchestrator()
        
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        
        old_time = datetime.now(timezone.utc) - timedelta(days=PAUSE_DAYS_BEFORE_DESTROY + 5)
        orchestrator._paused_monitors["financial"]["paused_at"] = old_time.isoformat()
        
        orchestrator.set_domain_relevance("finance", RELEVANCE_THRESHOLD_PAUSE + 0.5)
        
        destroyed = orchestrator.cleanup_stale_monitors()
        
        assert "financial" not in destroyed


class TestGetStats:
    """Testes para get_stats."""

    def test_stats_empty(self):
        """Deve retornar stats vazios."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        stats = orchestrator.get_stats()
        
        assert stats["active_count"] == 0
        assert stats["paused_count"] == 0
        assert stats["total_lifecycle_events"] == 0

    def test_stats_with_monitors(self):
        """Deve retornar stats corretos."""
        from intelligence.monitor_orchestrator import (
            MonitorOrchestrator,
            RELEVANCE_THRESHOLD_CREATE,
        )
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("m1", "finance", {})
        orchestrator.create_monitor("m2", "finance", {})
        orchestrator.pause_monitor("m2", "test")
        
        stats = orchestrator.get_stats()
        
        assert stats["active_count"] == 1
        assert stats["paused_count"] == 1
        assert stats["total_lifecycle_events"] >= 3


class TestLifecycleLog:
    """Testes para log de ciclo de vida."""

    def test_log_creates_entry(self):
        """Deve criar entrada no log ao criar monitor."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        
        log = orchestrator.get_lifecycle_log()
        assert len(log) == 1
        assert log[0]["action"] == "created"

    def test_log_multiple_events(self):
        """Deve registrar múltiplos eventos."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        orchestrator.pause_monitor("financial", "test")
        orchestrator.resume_monitor("financial")
        
        log = orchestrator.get_lifecycle_log()
        actions = [e["action"] for e in log]
        
        assert actions == ["created", "paused", "resumed"]

    def test_log_is_copy(self):
        """Deve retornar cópia do log, não referência."""
        from intelligence.monitor_orchestrator import MonitorOrchestrator
        
        orchestrator = MonitorOrchestrator()
        orchestrator.create_monitor("financial", "finance", {})
        
        log1 = orchestrator.get_lifecycle_log()
        log2 = orchestrator.get_lifecycle_log()
        
        log1.append({"fake": "entry"})
        
        assert len(log2) == 1

