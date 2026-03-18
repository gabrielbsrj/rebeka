import pytest
from agent.infrastructure.system_awareness import SystemAwareness
from agent.infrastructure.system_health_monitor import SystemHealthMonitor
from unittest.mock import patch

def test_system_awareness():
    awareness = SystemAwareness()
    metrics = awareness.collect_metrics()
    
    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "disk_usage" in metrics

@patch("agent.infrastructure.system_awareness.psutil.cpu_percent")
def test_system_awareness_overload(mock_cpu):
    mock_cpu.return_value = 99.9  # Forca sobrecarga
    awareness = SystemAwareness()
    
    assert awareness.is_overloaded() is True

def test_system_health_monitor():
    monitor = SystemHealthMonitor()
    
    # Em nosso stub de teste estrito todas as serves estao saudaveis por default
    assert monitor.check_services() is True
