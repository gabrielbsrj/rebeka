# sync/friction_synthesizer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Síntese de fricção entre perspectivas VPS e Local
#
# IMPACTO GÊMEO VPS: Fornece sinais globais para síntese
# IMPACTO GÊMEO LOCAL: Fornece contexto pessoal para síntese
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — síntese é idempotente

"""
Friction Synthesizer — Combina perspectivas VPS + Local para fricção ideal.

INTENÇÃO: A fricção mais eficaz é aquela que combina:
- Sinais globais do VPS (oportunidades de mercado, padrões macro)
- Contexto local do usuário (padrões comportamentais, histórico)

Este módulo:
1. Coleta contexto de ambos os gêmeos
2. Sintetiza em proposta de fricção otimizada
3. Aprende com resultados para ajustar tom/timing

INVARIANTE: Fricção sintetizada sempre inclui âncora concreta
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import litellm
from memory.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class FrictionSynthesizer:
    """
    Síntetiza fricção a partir de perspectivas gêmeas.

    INTENÇÃO: Quando VPS detecta oportunidade e Local detecta padrão,
    a fricção é mais eficaz porque tem âncora concreta.
    """

    SYNTHESIS_PROMPT = """Você é o Friction Synthesizer de um sistema de Gêmeos Idênticos.

Sua tarefa é criar uma proposta de FRICÇÃO INTENCIONAL que combine:
1. PERSPECTIVA GLOBAL (VPS) — Sinais de mercado, oportunidades, padrões macro
2. PERSPECTIVA LOCAL (Local) — Padrões comportamentais do usuário, histórico

A FRICÇÃO é diferente de crítica:
- Não diz "você está errado"
- Propõe uma perspectiva que o usuário não considerou
- Sempre ancorada em situação concreta
- Pergunta, não afirma

Contexto VPS:
{vps_context}

Contexto Local:
{local_context}

TAREFA:
Analise ambos os contextos e gere uma proposta de fricção otimizada.

Responda APENAS em JSON:
{{
    "friction_recommended": true/false,
    "confidence": 0.0-1.0,
    "friction_level": "leve/moderada/direta",
    "anchor_vps": "oportunidade concreta do VPS",
    "anchor_local": "padrão comportamental do Local",
    "synthesis_rationale": "por que esta fricção é válida agora",
    "suggested_message": "mensagem de fricção otimizada",
    "timing": "agora/mais_tarde/nunca",
    "requires_opportunity": true/false
}}"""

    def __init__(self, causal_bank: CausalBank, model: str = "claude"):
        self.bank = causal_bank
        self.model = model
        self._history: List[Dict] = []

    def synthesize(
        self,
        vps_context: Dict[str, Any],
        local_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sintetiza proposta de fricção a partir de ambos os contextos.

        Args:
            vps_context: Contexto do gêmeo VPS (sinais globais, oportunidades)
            local_context: Contexto do gêmeo Local (padrões, histórico)

        Returns:
            Proposta de fricção otimizada
        """
        vps_str = self._format_context(vps_context, "VPS")
        local_str = self._format_context(local_context, "Local")

        prompt = self.SYNTHESIS_PROMPT.format(
            vps_context=vps_str,
            local_context=local_str,
        )

        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            synthesis = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "friction_recommended": result.get("friction_recommended", False),
                "confidence": result.get("confidence", 0.0),
                "level": result.get("friction_level", "moderada"),
                "anchor_vps": result.get("anchor_vps"),
                "anchor_local": result.get("anchor_local"),
                "rationale": result.get("synthesis_rationale"),
                "message": result.get("suggested_message"),
                "timing": result.get("timing", "agora"),
            }

            self._history.append(synthesis)
            logger.info(f"Síntese de fricção: recommended={synthesis['friction_recommended']}, level={synthesis['level']}")

            return synthesis

        except Exception as e:
            logger.error(f"Erro na síntese de fricção: {e}")
            return {
                "friction_recommended": False,
                "confidence": 0.0,
                "error": str(e),
            }

    def get_context_for_synthesis(self) -> Dict[str, Any]:
        """
        Coleta contexto atual de ambos os gêmeos para síntese.
        """
        vps_context = self._get_vps_context()
        local_context = self._get_local_context()

        return {
            "vps": vps_context,
            "local": local_context,
        }

    def _get_vps_context(self) -> Dict[str, Any]:
        """Coleta contexto do gêmeo VPS."""
        try:
            recent_signals = self.bank.get_similar_signals(domain="polymarket", limit=10)
            active_patterns = self.bank.get_active_patterns(domain="polymarket", min_confidence=0.5)
            performance = self.bank.get_performance_stats()

            opportunities = []
            for signal in recent_signals:
                if signal.get("relevance_score", 0) > 0.7:
                    opportunities.append({
                        "title": signal.get("title"),
                        "domain": signal.get("domain"),
                        "relevance": signal.get("relevance_score"),
                    })

            return {
                "recent_signals": recent_signals,
                "active_patterns": active_patterns,
                "performance": performance,
                "opportunities": opportunities,
            }
        except Exception as e:
            logger.debug(f"Erro ao coletar contexto VPS: {e}")
            return {"error": str(e)}

    def _get_local_context(self) -> Dict[str, Any]:
        """Coleta contexto do gêmeo Local."""
        try:
            limiting_patterns = self._get_limiting_patterns()
            recent_signals = self.bank.get_recent_conversation_signals(days=7, limit=10)
            growth_targets = self.bank.get_active_growth_targets()
            friction_history = self.bank.get_friction_history(limit=20)

            return {
                "limiting_patterns": limiting_patterns,
                "recent_signals": recent_signals,
                "growth_targets": growth_targets,
                "friction_history": friction_history,
            }
        except Exception as e:
            logger.debug(f"Erro ao coletar contexto Local: {e}")
            return {"error": str(e)}

    def _get_limiting_patterns(self) -> List[Dict[str, Any]]:
        """Busca padrões potencialmente limitantes."""
        try:
            from intelligence.behavioral_pattern_detector import BehavioralPatternDetector
            detector = BehavioralPatternDetector(self.bank)
            return detector.get_limiting_patterns(min_confidence=0.5)
        except Exception:
            return []

    def _format_context(self, context: Dict[str, Any], source: str) -> str:
        """Formata contexto para o prompt."""
        import json
        
        if source == "VPS":
            opportunities = context.get("opportunities", [])
            patterns = context.get("active_patterns", [])
            
            formatted = f"""Sinais Recentes:
{json.dumps(context.get("recent_signals", [])[:3], indent=2)}

Oportunidades de Mercado:
{json.dumps(opportunities[:3], indent=2)}

Padrões Ativos:
{json.dumps(patterns[:3], indent=2)}

Performance:
{json.dumps(context.get("performance", {}), indent=2)}"""
        
        else:
            patterns = context.get("limiting_patterns", [])
            growth = context.get("growth_targets", [])
            frictions = context.get("friction_history", [])
            
            formatted = f"""Padrões Limitantes:
{json.dumps(patterns[:3], indent=2)}

Horizontes de Crescimento:
{json.dumps(growth[:3], indent=2)}

Historico de Friccoes (ultimas 5):
{json.dumps(frictions[:5], indent=2)}

Sinais de Conversa (ultimos 3):
{json.dumps(context.get("recent_signals", [])[:3], indent=2)}"""
        
        return formatted

    def record_outcome(
        self,
        synthesis_result: Dict[str, Any],
        user_response: str,
        outcome_7_days: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra resultado para meta-aprendizado.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "synthesis": synthesis_result,
            "user_response": user_response,
            "outcome": outcome_7_days,
            "effectiveness": self._calculate_effectiveness(user_response, outcome_7_days),
        }
        
        self._history.append(entry)
        
        logger.info(f"Resultado de fricção registrado: response={user_response}, effectiveness={entry['effectiveness']}")

    def _calculate_effectiveness(
        self,
        response: str,
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calcula score de efetividade."""
        score = 0.5
        
        if response in ["receptivo", "refletiu"]:
            score = 0.8
        elif response == "defensivo":
            score = 0.3
        elif response == "ignorou":
            score = 0.1
        
        if outcome:
            if outcome.get("behavior_changed"):
                score += 0.2
            if outcome.get("pattern_weakened"):
                score += 0.2
        
        return min(1.0, score)

    def get_effectiveness_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de efetividade das fricções.
        """
        if not self._history:
            return {"status": "no_data", "total_syntheses": 0}

        total = len(self._history)
        effective = sum(1 for h in self._history if h.get("effectiveness", 0) > 0.5)
        
        by_level = {}
        for h in self._history:
            level = h.get("synthesis", {}).get("level", "unknown")
            if level not in by_level:
                by_level[level] = {"total": 0, "effective": 0}
            by_level[level]["total"] += 1
            if h.get("effectiveness", 0) > 0.5:
                by_level[level]["effective"] += 1

        return {
            "total_syntheses": total,
            "effective_rate": effective / total if total > 0 else 0,
            "by_level": by_level,
            "recommended_approach": (
                max(by_level.items(), key=lambda x: x[1]["effective"] / x[1]["total"])[0]
                if by_level else "moderada"
            ),
        }

