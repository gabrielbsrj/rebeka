# agent/vps/monitors/survival_monitor.py
import logging
from typing import Dict, Any, List, Optional
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class SurvivalMonitor(BaseMonitor):
    def __init__(self, causal_bank, poll_interval: int = 3600):
        super().__init__(causal_bank, poll_interval=poll_interval)
        self.threshold_low = 0.20
        self.threshold_critical = 0.05

    def fetch_data(self) -> List[Dict[str, Any]]:
        # Simulação
        return [{
            "api_credits": 0.03,
            "wallet_balance": 10.0,
            "system_health": "stable"
        }]

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        api_credits = raw_item.get("api_credits", 1.0)
        if api_credits >= self.threshold_low:
            return None
            
        relevance = 0.85 if api_credits > self.threshold_critical else 1.0
        title = "ALERTA DE SOBREVIVÊNCIA"
        content = f"Créditos baixos ({api_credits*100}%)."
        
        if relevance == 1.0:
            title = "CRISE EXISTENCIAL"
            content = "Menos de 5% de créditos!"

        return {
            "domain": "survival",
            "source": "survival_monitor",
            "title": title,
            "content": content,
            "relevance_score": relevance,
            "metadata": raw_item
        }
