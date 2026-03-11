# agent/vps/monitors/macro_monitor.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Criação inicial — monitor macroeconômico com fallback

"""
Monitor Macroeconômico (VPS).

INTENÇÃO: Monitora indicadores fundamentais (FED Interest Rate, CPI, GDP).
Se a FRED_API_KEY estiver ausente, entra em modo SIMULAÇÃO para permitir
testes de correlação sem travar o sistema.
"""

import os
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class MacroMonitor(BaseMonitor):
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 86400):
        # Default de 24h para dados macro (mudam pouco)
        super().__init__(causal_bank, poll_interval)
        self.api_key = os.getenv("FRED_API_KEY")
        self.mode = "PROD" if self.api_key else "SIMULATION"
        
        if self.mode == "SIMULATION":
            logger.warning("FRED_API_KEY não encontrada. Iniciando MacroMonitor em modo SIMULAÇÃO.")

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Busca dados reais do FRED ou simula se não houver chave.
        """
        if self.mode == "PROD":
            return self._fetch_fred_data()
        else:
            return self._fetch_simulated_data()

    def _fetch_fred_data(self) -> List[Dict[str, Any]]:
        try:
            from fredapi import Fred
            fred = Fred(api_key=self.api_key)
            
            # Series de interesse: Fed Funds Rate, CPI, Desemprego
            series = {
                "FEDFUNDS": "Interest Rate",
                "CPIAUCSL": "Inflation (CPI)",
                "UNRATE": "Unemployment Rate"
            }
            
            results = []
            for s_id, label in series.items():
                val = fred.get_series(s_id).iloc[-1]
                results.append({
                    "indicator": label,
                    "series_id": s_id,
                    "value": float(val),
                    "timestamp": datetime.now().isoformat(),
                    "is_simulated": False
                })
            return results
        except Exception as e:
            logger.error(f"Erro ao buscar dados do FRED: {e}")
            return self._fetch_simulated_data()

    def _fetch_simulated_data(self) -> List[Dict[str, Any]]:
        """
        Gera dados realistas para testes.
        """
        logger.info("Gerando dados macro simularizados (Modo Sandbox)...")
        return [
            {
                "indicator": "Interest Rate",
                "series_id": "FEDFUNDS",
                "value": 5.33, # Exemplo de taxa atual
                "timestamp": datetime.now().isoformat(),
                "is_simulated": True
            },
            {
                "indicator": "Inflation (CPI)",
                "series_id": "CPIAUCSL",
                "value": 3.1 + random.uniform(-0.1, 0.1),
                "timestamp": datetime.now().isoformat(),
                "is_simulated": True
            }
        ]

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        indicator = raw_item["indicator"]
        value = raw_item["value"]
        
        return {
            "domain": "macro",
            "type": "economic_indicator",
            "source": "FRED" if not raw_item["is_simulated"] else "Simulation",
            "title": f"Indicador: {indicator}",
            "content": f"O indicador {indicator} ({raw_item['series_id']}) está em {value:.2f}%{' (SIMULADO)' if raw_item['is_simulated'] else ''}.",
            "relevance_score": 0.8, # Macro sempre tem alta relevância
            "raw_data": raw_item,
            "metadata": {
                "series_id": raw_item["series_id"],
                "value": value,
                "is_simulated": raw_item["is_simulated"]
            }
        }

