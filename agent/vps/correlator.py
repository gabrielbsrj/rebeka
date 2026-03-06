# agent/vps/correlator.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — motor de correlação global

import logging
import time
from typing import List, Dict, Any
from shared.database.causal_bank import CausalBank
from shared.database.causal_validator import CausalValidator

logger = logging.getLogger(__name__)

class GlobalCorrelator:
    """
    Motor de Correlação Global (VPS).
    
    INTENÇÃO: Agrega sinais de múltiplos domínios e busca 
    correlações que possam indicar mecanismos causais.
    """

    def __init__(self, causal_bank: CausalBank, validator: CausalValidator):
        self.bank = causal_bank
        self.validator = validator

    def scan_for_patterns(self, window_hours: int = 24):
        """
        Busca sinais recentes de domínios diferentes e tenta identificar 
        correlações temporais que possam indicar causalidade.
        """
        from datetime import datetime, timedelta, timezone
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=window_hours)
        
        logger.info(f"Escaneando correlações nas últimas {window_hours} horas...")
        
        # 1. Buscar sinais de múltiplos domínios
        domains = ["geopolitics", "macro", "commodities", "finance"]
        signals = self.bank.get_signals_in_window(start_time, end_time, domains)
        
        if len(signals) < 2:
            logger.info("Sinais insuficientes para análise de correlação.")
            return

        # 2. Agrupar sinais por domínio para cruzamento
        by_domain = {}
        for s in signals:
            d = s["domain"]
            if d not in by_domain:
                by_domain[d] = []
            by_domain[d].append(s)

        # 3. Cruzamento Geopolítica -> Finanças (Exemplo clássico)
        if "geopolitics" in by_domain and "finance" in by_domain:
            for geo in by_domain["geopolitics"]:
                for fin in by_domain["finance"]:
                    # Se geo ocorreu ANTES de fin
                    geo_time = datetime.fromisoformat(geo["created_at"])
                    fin_time = datetime.fromisoformat(fin["created_at"])
                    
                    if geo_time < fin_time:
                        # Candidato encontrado!
                        self._analyze_candidate(geo, fin)

    def _analyze_candidate(self, cause_signal: Dict, effect_signal: Dict):
        """Analisa um par de sinais como candidato causal."""
        candidate_data = {
            "domain": "cross_domain",
            "variable_a": f"Signal:{cause_signal['id']} ({cause_signal['title']})",
            "variable_b": f"Signal:{effect_signal['id']} ({effect_signal['title']})",
            "correlation_strength": 0.5, # Inicial
            "metadata": {
                "cause_id": cause_signal["id"],
                "effect_id": effect_signal["id"]
            }
        }
        
        logger.info(f"Candidato à correlação detectado: {cause_signal['title']} -> {effect_signal['title']}")
        
        # Consultar o validador causal (LLM)
        validation = self.validator.validate_pattern(
            cause=cause_signal["title"],
            effect=effect_signal["title"],
            domain="geopolitcs_to_finance"
        )
        
        if validation.get("is_plausible"):
            pattern_data = {
                "domain": "geopolitics_to_finance",
                "cause_description": cause_signal["title"],
                "effect_description": effect_signal["title"],
                "causal_mechanism": validation["mechanism"],
                "confidence": validation["confidence"],
                "signal_ids": [cause_signal["id"], effect_signal["id"]],
            }
            # Promover a padrão causal definitivo
            pattern_id = self.bank.insert_causal_pattern(pattern_data)
            logger.info(f"NOVO PADRÃO CAUSAL VALIDADO: {pattern_id}")
        else:
            # Apenas registra como candidato se não for bizarro
            self.bank.insert_correlation_candidate(candidate_data)

    def promote_candidate(self, candidate_id: str):
        """
        Promove um candidato a padrão causal após validação manual ou estatística.
        """
        logger.info(f"Promovendo candidato {candidate_id} para Causal Pattern.")
        # Lógica de promoção manual via Dashboard
        pass
