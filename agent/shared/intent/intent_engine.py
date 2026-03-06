# shared/intent/intent_engine.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Motor de Intenção que coordena todos os módulos
#
# IMPACTO GÊMEO VPS: Coordena módulos de intenção no contexto VPS
# IMPACTO GÊMEO LOCAL: Coordena módulos de intenção no contexto LOCAL
# DIFERENÇA DE COMPORTAMENTO: Injeta contexto diferente (global vs pessoal)

"""
Intent Engine — Motor de Intenção Central.

INTENÇÃO: Este é o cérebro que coordena todos os módulos de intenção:
- GrowthHorizon (monitora distância do futuro desejado)
- IntentionalFriction (propõe perspectivas que o usuário não considerou)
- ProfileBuilder (modelo dual declarado/observado)
- BehavioralPatternDetector (detecta padrões recorrentes)
- ConversationAnalyzer (extrai sinais de conversas)

O Intent Engine:
1. Mantém o modelo de valores do usuário
2. Detecta padrões comportamentais
3. Avalia se fricção é necessária
4. Monitora progresso em horizontes
5. Sintetiza perspectivas VPS + Local para decisões

INVARIANTE: O Intent Engine nunca toma decisões financeiras.
Ele modela valores e propõe contexto — a decisão é sempre do Planner/Avaliador.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank
from shared.intent.growth_horizon import GrowthHorizon
from shared.intent.intentional_friction import IntentionalFriction
from shared.intent.profile_builder import ProfileBuilder
from shared.intent.behavioral_pattern_detector import BehavioralPatternDetector
from shared.intent.conversation_analyzer import ConversationAnalyzer

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from sync.friction_synthesizer import FrictionSynthesizer
    from sync.friction_learner import FrictionLearner
    SYNC_AVAILABLE = True
except ImportError:
    SYNC_AVAILABLE = False
    FrictionSynthesizer = None
    FrictionLearner = None

logger = logging.getLogger(__name__)


class IntentEngine:
    """
    Motor de Intenção — Coordenador de todos os módulos de intenção.

    INTENÇÃO: O único ponto fixo num sistema que pode atravessar qualquer domínio.
    Mantém o modelo de valores do usuário e coordena os módulos que o entendem.
    """

    def __init__(self, causal_bank: CausalBank, origin: str = "local"):
        self.bank = causal_bank
        self.origin = origin
        
        self.growth_horizon = GrowthHorizon(causal_bank)
        self.intentional_friction = IntentionalFriction(causal_bank)
        self.profile_builder = ProfileBuilder(causal_bank)
        self.pattern_detector = BehavioralPatternDetector(causal_bank)
        self.conversation_analyzer = ConversationAnalyzer(causal_bank)
        
        if SYNC_AVAILABLE:
            self.friction_synthesizer = FrictionSynthesizer(causal_bank)
            self.friction_learner = FrictionLearner(causal_bank)
        else:
            self.friction_synthesizer = None
            self.friction_learner = None
        
        self._initialized = False

    def initialize(self) -> None:
        """Inicializa o motor de intenção."""
        if self._initialized:
            return
            
        profile = self.bank.get_latest_declared_profile()
        
        if not profile:
            print(f"[DEBUG] Profile not found! Bank: {self.bank}")
            logger.info("Nenhum perfil declarado encontrado. Usuário precisa fazer onboarding.")
        else:
            print(f"[DEBUG] Profile FOUND: {profile}")
            logger.info(f"Motor de Intenção inicializado para {self.origin} - Perfil: {profile.get('horizon_temporal')}, {profile.get('autonomy_preference')}")
            self._user_profile = profile
            
        self._initialized = True

    def on_user_message(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processa mensagem do usuário e atualiza modelo de intenções.

        Args:
            message: Texto da mensagem
            conversation_id: ID da conversa (opcional)

        Returns:
            Resposta estruturada com sinais extraídos
        """
        self.initialize()
        
        conversation_result = self.conversation_analyzer.analyze_and_update_patterns(message)
        
        extracted = conversation_result.get("extracted", {})
        
        emotional = extracted.get("emotional_state", {})
        if emotional:
            self._update_emotional_context(emotional)
        
        growth_implicit = extracted.get("growth_horizon_implicit", {})
        if growth_implicit.get("desired_state"):
            self._check_growth_implicit(growth_implicit)
        
        friction_potential = extracted.get("friction_potential", {})
        for pattern_type, data in friction_potential.items():
            if data.get("candidato_para_fricao"):
                logger.info(f"Padrão limitante detectado em conversa: {pattern_type}")

        return {
            "status": "processed",
            "conversation_id": conversation_id,
            "extracted_signals": extracted,
            "requires_response": self._should_respond(extracted),
        }

    def check_and_apply_friction(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se fricção deve ser aplicada e a aplica.

        Args:
            context: Contexto adicional (ex: oportunidade concreta)

        Returns:
            Dados da fricção aplicada ou None
        """
        self.initialize()
        
        candidates = self.intentional_friction.check_pending_friction_candidates()
        
        if not candidates:
            return None
        
        user_state = self._get_user_state()
        
        for candidate in candidates:
            result = self.intentional_friction.apply_friction(
                pattern_id=candidate["pattern_id"],
                user_receptivity=user_state.get("receptivity", 0.7),
                emotional_state=user_state.get("emotional", "neutral"),
                context=context,
            )
            
            if result:
                return result
        
        return None

    def update_growth_progress(
        self,
        metrics: Dict[str, Any],
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atualiza progresso em horizontes de crescimento.

        Args:
            metrics: Métricas atuais
            target_id: Alvo específico ou None para todos

        Returns:
            Resultado da atualização
        """
        self.initialize()
        
        targets = self.bank.get_active_growth_targets()
        
        if not targets:
            return {"status": "no_targets"}
        
        results = []
        
        for target in targets:
            if target_id and target["id"] != target_id:
                continue
                
            result = self.growth_horizon.update_progress(target["id"], metrics)
            results.append({
                "target_id": target["id"],
                "domain": target["domain"],
                "result": result,
            })
            
            if result.get("trend") == "stagnant" and result.get("distance", 1.0) > 0.5:
                conversation = self.growth_horizon.propose_growth_conversation(target["id"])
                if conversation:
                    logger.info(f"Mensagem de crescimento proposta: {conversation[:50]}...")
        
        return {
            "status": "updated",
            "targets": results,
        }

    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo do perfil do usuário.
        """
        self.initialize()
        return self.profile_builder.get_profile_summary()

    def get_growth_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de crescimento.
        """
        self.initialize()
        return self.growth_horizon.get_weekly_report()

    def get_limiting_patterns(self) -> List[Dict[str, Any]]:
        """
        Retorna padrões potencialmente limitantes.
        """
        self.initialize()
        return self.pattern_detector.get_limiting_patterns()

    def declare_onboarding(self, answers: Dict[str, str]) -> str:
        """
        Completa onboarding com respostas do usuário.

        Args:
            answers: Respostas às 5 perguntas

        Returns:
            ID do perfil criado
        """
        profile_id = self.profile_builder.complete_onboarding(answers)
        
        growth_answer = answers.get("growth_horizon")
        if growth_answer:
            self.growth_horizon.declare_growth_target(
                domain=answers.get("biggest_pain_point", "trading"),
                current_state="ainda não defini",
                desired_future=growth_answer,
                progress_metrics=["progresso_1", "progresso_2"],
                deadline_days=180,
            )
        
        logger.info(f"Onboarding completado: {profile_id}")
        return profile_id

    def synthesize_perspective(
        self,
        vps_context: Dict[str, Any],
        local_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sintetiza perspectiva global (VPS) + local para fricção.

        Args:
            vps_context: Contexto do gêmeo VPS
            local_context: Contexto do gêmeo Local

        Returns:
            Perspectiva sintetizada
        """
        patterns_vps = vps_context.get("patterns", [])
        patterns_local = local_context.get("patterns", [])
        
        opportunities_vps = vps_context.get("opportunities", [])
        opportunities_local = local_context.get("opportunities", [])
        
        synthesis = {
            "combined_patterns": list(set(patterns_vps + patterns_local)),
            "combined_opportunities": list(set(opportunities_vps + opportunities_local)),
            "vps_signal_strength": len(patterns_vps),
            "local_signal_strength": len(patterns_local),
            "friction_recommended": (
                len(patterns_local) >= 3 and 
                len(opportunities_vps) > 0
            ),
        }
        
        return synthesis

    def synthesize_friction_dual(
        self,
        vps_context: Optional[Dict[str, Any]] = None,
        local_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Sintetiza fricção com contexto dual (VPS + Local).

        Args:
            vps_context: Contexto do gêmeo VPS
            local_context: Contexto do gêmeo Local

        Returns:
            Proposta de fricção sintetizada
        """
        if not SYNC_AVAILABLE or not self.friction_synthesizer:
            return None

        if not vps_context or not local_context:
            context = self.friction_synthesizer.get_context_for_synthesis()
            vps_context = context.get("vps", {})
            local_context = context.get("local", {})

        synthesis = self.friction_synthesizer.synthesize(vps_context, local_context)

        if synthesis.get("friction_recommended"):
            optimization = self.friction_learner.suggest_friction_parameters(
                pattern_type=synthesis.get("anchor_local", {}).get("type", "general"),
                pattern_confidence=synthesis.get("confidence", 0.5),
            )
            synthesis["optimization"] = optimization

        return synthesis

    def record_friction_outcome(
        self,
        synthesis_result: Dict[str, Any],
        user_response: str,
        outcome_7_days: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra resultado de fricção para meta-aprendizado.

        Args:
            synthesis_result: Resultado da síntese
            user_response: Resposta do usuário
            outcome_7_days: Comportamento após 7 dias
        """
        if not SYNC_AVAILABLE or not self.friction_learner:
            return

        self.friction_learner.analyze_effectiveness()

    def get_friction_effectiveness_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de efetividade das fricções.

        Returns:
            Análise de efetividade
        """
        if not SYNC_AVAILABLE or not self.friction_learner:
            return {"status": "unavailable"}

        effectiveness = self.friction_learner.analyze_effectiveness()
        patterns = self.friction_learner.detect_receptivity_patterns()
        suggestions = self.friction_learner.get_optimization_suggestions()

        return {
            "effectiveness": effectiveness,
            "patterns": patterns,
            "suggestions": suggestions,
        }

    def get_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Determina próxima ação do Intent Engine.

        Returns:
            Ação recomendada ou None
        """
        self.initialize()
        
        friction = self.check_and_apply_friction()
        if friction:
            return {
                "type": "friction",
                "data": friction,
            }
        
        limiting = self.get_limiting_patterns()
        if limiting:
            return {
                "type": "pattern_alert",
                "patterns": limiting[:3],
            }
        
        growth_report = self.get_growth_report()
        if growth_report.get("targets"):
            for target in growth_report["targets"]:
                if target.get("trend") == "stagnant":
                    return {
                        "type": "growth_checkin",
                        "target": target,
                    }
        
        return None

    def _update_emotional_context(self, emotional: Dict[str, Any]) -> None:
        """Atualiza contexto emocional do usuário."""
        logger.debug(f"Contexto emocional atualizado: {emotional}")

    def _check_growth_implicit(self, growth_implicit: Dict[str, Any]) -> None:
        """Verifica se horizonte implícito deve ser registrado."""
        current = growth_implicit.get("current_state")
        desired = growth_implicit.get("desired_state")
        
        if not desired:
            return
        
        targets = self.bank.get_active_growth_targets()
        
        for target in targets:
            if target.get("desired_state") != desired:
                logger.info(f"Novo horizonte implícito detectado: {desired}")

    def _should_respond(self, extracted: Dict[str, Any]) -> bool:
        """Determina se o sistema deve responder imediatamente."""
        emotional = extracted.get("emotional_state", {})
        if emotional.get("inferred") in ["desesperado", "ansioso"]:
            return True
        
        friction = extracted.get("friction_potential", {})
        for data in friction.values():
            if data.get("candidato_para_fricao") and data.get("timing_sugerido") == "agora":
                return True
        
        return False

    def _get_user_state(self) -> Dict[str, Any]:
        """Retorna estado atual do usuário."""
        profile = self.profile_builder.get_profile_summary()
        
        recent_signals = self.bank.get_recent_conversation_signals(days=7, limit=10)
        
        emotional = None
        if recent_signals:
            latest = recent_signals[0]
            emotional = latest.get("emotional")
        
        return {
            "receptivity": 0.7,
            "emotional": emotional or "neutral",
            "has_declared_profile": profile.get("declared") is not None,
        }
