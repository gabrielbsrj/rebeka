"""
System Awareness - Módulo 14 (v6.2)
Consciência operacional do sistema. Monitora recursos locais de servidor/host.
"""
import psutil
import logging

logger = logging.getLogger(__name__)

class SystemAwareness:
    def __init__(self):
        self.thresholds = {
            "cpu_critical": 90.0,
            "memory_critical": 85.0
        }
        
    def collect_metrics(self) -> dict:
        """Coleta métricas atuais do host onde Rebeka está executando."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        metrics = {
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
        return metrics
        
    def is_overloaded(self) -> bool:
        """Retorna True se o sistema/infraestrutura estiver em exaustão."""
        metrics = self.collect_metrics()
        
        if metrics["cpu_usage"] >= self.thresholds["cpu_critical"]:
            logger.warning(f"SISTEMA SOBRECARREGADO (CPU): {metrics['cpu_usage']}%")
            return True
        if metrics["memory_usage"] >= self.thresholds["memory_critical"]:
            logger.warning(f"SISTEMA SOBRECARREGADO (RAM): {metrics['memory_usage']}%")
            return True
            
        return False
