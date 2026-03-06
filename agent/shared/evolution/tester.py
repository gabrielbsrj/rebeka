# agent/shared/evolution/tester.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Adicionado testes de segurança ofensiva (AutoHacker)

import logging
from typing import Dict, Any
from .property_tester import PropertyTester
from shared.security.auto_hacker import AutoHacker
from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)

class EvolutionTester:
    """
    Evolution Tester — O juiz da evolução.
    
    INTENÇÃO: Roda a suite completa de testes (unitários + propriedades)
    e agora também a suite de SEGURANÇA OFENSIVA (AutoHacker).
    """

    def __init__(self, property_tester: PropertyTester, causal_bank: CausalBank):
        self.prop_tester = property_tester
        self.bank = causal_bank

    def run_all_validation(self, evolution_id: str) -> bool:
        """
        Executa validação funcional, invariantes e auto-pentest.
        """
        logger.info(f"Iniciando validação completa da evolução: {evolution_id}")
        
        # 1. Roda testes de propriedades (Invariantes lógicos)
        success_invariants = self.prop_tester.run_invariant_suite(lambda x, y: True)
        
        # 2. Roda a suite de ataques do Red Team
        logger.info("Executando Pentest Interno (AutoHacker)...")
        hacker = AutoHacker(self.bank)
        
        # Como o Sandbox/Tester atua como juiz, ele precisa instanciar
        # ou mockar as defesas reais do sistema:
        from local.privacy_filter import PrivacyFilter
        from shared.database.causal_validator import CausalValidator
        
        pfilter = PrivacyFilter()
        cvalidator = CausalValidator(self.bank)
        
        hacker_results = hacker.run_all_tests(pfilter, cvalidator)
        
        has_security_breach = any(r.get("status") == "failed" for r in hacker_results)
        
        if has_security_breach:
            logger.error(f"Evolução {evolution_id} REJEITADA! O AutoHacker encontrou falhas de segurança.")
            return False

        return success_invariants

