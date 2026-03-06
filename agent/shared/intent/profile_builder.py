# shared/intent/profile_builder.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2022023
# CHANGELOG: v1 — Implementação inicial do modelo dual declarado/observado
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Mantém perfil dual do usuário
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Profile Builder — Modelo dual Declarado/Observado do usuário.

INTENÇÃO: Duas camadas separadas:
- DECLARADO: Editável pelo usuário, ponto de partida, versão aspiracional
- OBSERVADO: Atualizado só pelo sistema, dado primário quando diverge

Este módulo:
1. Gerencia perfil declarado
2. Atualiza perfil observado via comportamento
3. Detecta e notifica divergências
4. Gera relatório de perfil para o usuário
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """
    Construtor de perfil dual.

    INTENÇÃO: Mantém duas visões do usuário:
    - O que ele diz que é (declarado)
    - O que seu comportamento revela (observado)
    """

    ONBOARDING_QUESTIONS = {
        "relationship_with_risk": {
            "question": "Você prefere perder uma oportunidade certa ou arriscar e perder?",
            "options": {
                "perder_oportunidade": "Prefiro perder oportunidade do que arriscar",
                "arriscar_perder": "Prefiro arriscar e talvez perder",
                "depende": "Depende da situação"
            }
        },
        "regret_definition": {
            "question": "O que te incomoda mais: ter agido e errado, ou não ter agido?",
            "options": {
                "acao": "Agir e errado",
                "omissao": "Não ter agido",
                "indiferente": "Não me importa"
            }
        },
        "horizon_temporal": {
            "question": "Quando você pensa em 'futuro', quanto tempo você visualiza?",
            "options": {
                "curto": "Próximas semanas/meses",
                "medio": "Próximos 1-3 anos",
                "longo": "5+ anos",
                "vago": "Não sei dizer"
            }
        },
        "autonomy_preference": {
            "question": "Você quer ser consultado em cada decisão ou prefere ser avisado depois?",
            "options": {
                "consultado": "Sempre me consulte antes",
                "avisado_depois": "Me avise depois do que fez",
                "autonomo": "Decida sozinho, me avise depois"
            }
        },
        "biggest_pain_point": {
            "question": "Onde você mais sente que toma decisões sem informação suficiente?",
            "options": {
                "trading": "Trading/Investimentos",
                "saude": "Saúde",
                "carreira": "Carreira",
                "relacionamentos": "Relacionamentos",
                "financas": "Finanças pessoais"
            }
        }
    }

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def declare_profile(
        self,
        risk_profile: Optional[str] = None,
        autonomy_preference: Optional[str] = None,
        horizon_temporal: Optional[str] = None,
        biggest_pain_point: Optional[str] = None,
        regret_definition: Optional[str] = None,
        relationship_with_risk: Optional[str] = None,
        additional_values: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Declara perfil do usuário.

        Args:
            risk_profile: conservador, moderado, arrojado
            autonomy_preference: consultado, avisado_depois, autonomo
            horizon_temporal: curto, medio, longo
            biggest_pain_point: domínio de maior dor
            regret_definition: o que incomoda mais
            relationship_with_risk: resposta à pergunta 1
            additional_values: valores adicionais

        Returns:
            ID do perfil criado
        """
        profile_data = {
            "risk_profile": risk_profile,
            "autonomy_preference": autonomy_preference,
            "horizon_temporal": horizon_temporal,
            "biggest_pain_point": biggest_pain_point,
            "regret_definition": regret_definition,
            "relationship_with_risk": relationship_with_risk,
            "additional_values": additional_values or {},
        }

        profile_id = self.bank.insert_user_profile_declared(profile_data)
        
        logger.info(f"Perfil declarado criado: {profile_id}")
        
        self._check_initial_divergences(profile_data)

        return profile_id

    def update_observed_profile(
        self,
        domain: str,
        observed_value: str,
        evidence: Dict[str, Any],
        confidence: float = 0.6,
    ) -> str:
        """
        Atualiza perfil observado pelo sistema.

        Args:
            domain: Domínio (trading, saude, etc)
            observed_value: Valor observado
            evidence: Evidência da observação
            confidence: Confiança da observação

        Returns:
            ID do registro criado
        """
        declared = self.bank.get_latest_declared_profile()
        
        diverges = False
        if declared:
            declared_value = declared.get(domain)
            if declared_value and declared_value != observed_value:
                diverges = True

        profile_data = {
            "domain": domain,
            "observed_value": observed_value,
            "observation_count": 1,
            "confidence": confidence,
            "evidence": [evidence],
            "diverges_from_declared": diverges,
        }

        profile_id = self.bank.insert_user_profile_observed(profile_data)

        if diverges:
            logger.info(f"Divergência detectada: {domain} - declarado={declared.get(domain)}, observado={observed_value}")

        return profile_id

    def increment_observation(
        self,
        domain: str,
        observed_value: str,
        evidence: Dict[str, Any],
    ) -> None:
        """
        Incrementa contagem de observação para valor já existente.
        """
        observed = self.bank.get_observed_profiles(domain=domain)
        
        matching = [o for o in observed if o["value"] == observed_value]
        
        if matching:
            existing_id = matching[0]["id"]
            new_count = matching[0]["observation_count"] + 1
            new_confidence = min(1.0, 0.5 + (new_count * 0.05))
            
            profile_data = {
                "domain": domain,
                "observed_value": observed_value,
                "observation_count": new_count,
                "confidence": new_confidence,
                "evidence": matching[0].get("evidence", []) + [evidence],
                "diverges_from_declared": matching[0]["diverges"],
            }
            
            self.bank.insert_user_profile_observed(profile_data)
        else:
            self.update_observed_profile(domain, observed_value, evidence)

    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Gera resumo do perfil para exibição ao usuário.

        Returns:
            Perfil declarado + observado com divergências
        """
        declared = self.bank.get_latest_declared_profile()
        observed = self.bank.get_observed_profiles()

        divergencies = []
        
        if declared:
            for domain, declared_value in declared.items():
                if domain in ["additional_values"]:
                    continue
                    
                observed_match = next(
                    (o for o in observed if o["domain"] == domain),
                    None
                )
                
                if observed_match and declared_value:
                    if declared_value != observed_match["value"]:
                        divergencies.append({
                            "domain": domain,
                            "declared": declared_value,
                            "observed": observed_match["value"],
                            "confidence": observed_match["confidence"],
                        })

        return {
            "declared": declared or {},
            "observed": observed,
            "divergencies": divergencies,
            "has_divergencies": len(divergencies) > 0,
        }

    def check_divergence_and_notify(
        self,
        domain: str,
        new_observed_value: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se há nova divergência e gera notificação.

        Returns:
            Mensagem de notificação ou None
        """
        declared = self.bank.get_latest_declared_profile()
        
        if not declared:
            return None

        declared_value = declared.get(domain)
        
        if not declared_value:
            return None

        if declared_value != new_observed_value:
            divergence_message = self._generate_divergence_message(
                domain,
                declared_value,
                new_observed_value
            )
            
            return {
                "domain": domain,
                "declared": declared_value,
                "observed": new_observed_value,
                "message": divergence_message,
            }

        return None

    def get_onboarding_questions(self) -> Dict[str, Any]:
        """
        Retorna perguntas de onboarding.

        Returns:
            Dicionário de perguntas para o usuário
        """
        return self.ONBOARDING_QUESTIONS

    def complete_onboarding(
        self,
        answers: Dict[str, str],
    ) -> str:
        """
        Completa onboarding com respostas do usuário.

        Args:
            answers: Respostas às 5 perguntas

        Returns:
            ID do perfil criado
        """
        return self.declare_profile(
            relationship_with_risk=answers.get("relationship_with_risk"),
            regret_definition=answers.get("regret_definition"),
            horizon_temporal=answers.get("horizon_temporal"),
            autonomy_preference=answers.get("autonomy_preference"),
            biggest_pain_point=answers.get("biggest_pain_point"),
        )

    def _check_initial_divergences(self, declared: Dict[str, Any]) -> None:
        """
        Verifica divergências iniciais ao declarar perfil.
        """
        observed = self.bank.get_observed_profiles()
        
        for domain, declared_value in declared.items():
            if domain in ["additional_values"] or not declared_value:
                continue
                
            observed_match = next(
                (o for o in observed if o["domain"] == domain),
                None
            )
            
            if observed_match and observed_match["value"] != declared_value:
                logger.info(f"Divergência inicial: {domain} - declarado={declared_value}, observado={observed_match['value']}")

    def _generate_divergence_message(
        self,
        domain: str,
        declared: str,
        observed: str,
    ) -> str:
        """Gera mensagem de notificação de divergência."""
        
        messages = {
            "autonomy_preference": (
                f"Percebi que você tende a revisar decisões que pediu para eu "
                f"tomar autonomamente. Você prefere ser consultado antes?"
            ),
            "risk_profile": (
                f"Seu perfil de risco declarado é '{declared}', mas seu "
                f"comportamento recente indica '{observed}'. Quer atualizar?"
            ),
        }

        default = (
            f"Você disse que prefere {declared}, mas notei que "
            f"seu comportamento recente indica {observed}."
        )

        return messages.get(domain, default)
