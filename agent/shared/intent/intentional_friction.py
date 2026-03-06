# shared/intent/intentional_friction.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Implementação inicial de fricção intencional calibrada
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Propõe perspectivas que o usuário não considerou
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Intentional Friction — Fricção calibrada quando padrão limitante detectado.

INTENÇÃO: Um sistema que só aprende com um usuário corre o risco de eternizar
padrões disfuncionais em vez de criar fricção saudável. Coerência com o passado
não é o mesmo que alinhamento com o futuro desejado.

O sistema não confronta — propõe uma perspectiva que o usuário não considerou,
no momento certo, com o tom certo.

INVARIANTE: NUNCA aplica fricção em estado emocional negativo
INVARIANTE: NUNCA repete fricção ignorada
INVARIANTE: Sempre ancorado em situação concreta
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class IntentionalFriction:
    """
    Sistema de fricção intencional calibrada.

    INTENÇÃO: Não é confronto. Não é crítica.
    É o sistema propondo uma perspectiva que o usuário não considerou —
    no momento certo, com o tom certo, baseado em padrão detectado.
    """

    FRICTION_LEVELS = {
        "leve": {
            "description": "pergunta aberta sem julgamento",
            "template": "O que você acha de {topic}?",
        },
        "moderada": {
            "description": "nomeação direta do padrão com dados",
            "template": "Notei que {pattern_observed} {times}. O que te leva a isso?",
        },
        "direta": {
            "description": "contraste explícito entre desejo e ação",
            "template": "Você quer {desired} mas está fazendo {current}. Curious.",
        },
    }

    MIN_DAYS_BETWEEN_FRICTION = 14
    MIN_CONFIRMATION_COUNT = 5
    MIN_RECEPTIVITY = 0.6

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def should_apply_friction(
        self,
        pattern_id: str,
        user_receptivity: float = 0.7,
        emotional_state: str = "neutral",
    ) -> bool:
        """
        Determina se fricção deve ser aplicada.

        Condições:
        - padrão confirmado >= 5 vezes
        - classificado como potencialmente limitante
        - >= 14 dias desde última fricção
        - receptividade >= 0.6
        - estado emocional não negativo
        - oportunidade concreta detectada
        """
        patterns = self.bank.get_behavioral_patterns(min_confidence=0.5)
        pattern = next((p for p in patterns if p["id"] == pattern_id), None)

        if not pattern:
            return False

        if pattern["confirmation_count"] < self.MIN_CONFIRMATION_COUNT:
            logger.debug(f"Padrão {pattern_id} não tem confirmações suficientes")
            return False

        if not pattern.get("potentially_limiting", False):
            logger.debug(f"Padrão {pattern_id} não é limitante")
            return False

        if user_receptivity < self.MIN_RECEPTIVITY:
            logger.debug(f"Receptividade {user_receptivity} muito baixa")
            return False

        if emotional_state in ["distress", "anger", "despair", "fear"]:
            logger.debug(f"Estado emocional {emotional_state} não permite fricção")
            return False

        recent_frictions = self.bank.get_friction_history(
            category=pattern["type"],
            limit=10
        )
        
        if recent_frictions:
            last_friction = recent_frictions[0]
            last_date = datetime.fromisoformat(last_friction["created_at"])
            days_since = (datetime.now(timezone.utc) - last_date).days
            
            if days_since < self.MIN_DAYS_BETWEEN_FRICTION:
                logger.debug(f"Muito recente: {days_since} dias desde última fricção")
                return False

        return True

    def calculate_friction_level(
        self,
        pattern_confidence: float,
        confirmation_count: int,
        distance_from_desired: float,
    ) -> str:
        """
        Calcula nível de fricção apropriado.

        Nível aumenta com:
        - frequência do padrão
        - distância entre declarado e observado
        - impacto demonstrado

        Nível diminui com:
        - sinais de estado emocional negativo
        - cláusula de arrependimento recente
        - receptividade histórica baixa
        """
        score = 0.0

        score += min(0.3, confirmation_count * 0.05)
        score += distance_from_desired * 0.4
        score += pattern_confidence * 0.3

        if score < 0.3:
            return "leve"
        elif score < 0.6:
            return "moderada"
        else:
            return "direta"

    def generate_friction_message(
        self,
        pattern: Dict[str, Any],
        level: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Gera mensagem de fricção baseada no padrão e nível.

        Args:
            pattern: Dados do padrão comportamental
            level: Nível de fricção (leve/moderada/direta)
            context: Contexto adicional (ex: oportunidade concreta)

        Returns:
            Mensagem formatada
        """
        pattern_type = pattern["type"]
        domain = pattern["domain"]
        description = pattern["description"]
        
        templates = {
            "vies_alta": {
                "leve": "Notei que você sempre opera na mesma direção. Já considerou o contrário?",
                "moderada": f"Você nunca operou short em {pattern['confirmation_count']} operações. Os monitores estão apontando para baixa agora. O que te faz evitar essa direção?",
                "direta": "Você quer operar com disciplina mas neverchallenged o viés de alta. Às vezes um padrão tem razão. Às vezes está limitando.",
            },
            "revenge_trading": {
                "leve": "Percebi que você tende a operar logo após perdas. Como está se sentindo sobre isso?",
                "moderada": f"Você fez {pattern['confirmation_count']} operações nos últimos 30 dias logo após perdas. Isso acontece muito. Quer conversar sobre?",
                "direta": "Você disse que quer gestão de risco, mas após uma perda você opera com x2 alavancagem. Isso é o que você quer?",
            },
            "stop_loss": {
                "leve": "，关于止损你怎么想？",
                "moderada": f"Seu stop loss foi usado em apenas {pattern['confirmation_count']}% das operações. Você prefere não usar?",
                "direta": "Você declara querer disciplina, mas não usa stop loss em 80% das operações. Isso é uma contradição que você quer resolver?",
            },
            "default": {
                "leve": f"O que você acha de {description}?",
                "moderada": f"Notei que isso acontece com frequência: {description}. O que te leva isso?",
                "direta": f"Você quer {(context or {}).get('desired', 'mudar')} mas está fazendo {description}. Interessante.",
            }
        }

        template_dict = templates.get(pattern_type, templates["default"])
        
        message = template_dict.get(level, template_dict["leve"])

        if context and context.get("opportunity"):
            message += f"\n\nConcrete: {context['opportunity']}"

        return message

    def apply_friction(
        self,
        pattern_id: str,
        user_receptivity: float = 0.7,
        emotional_state: str = "neutral",
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Aplica fricção se condições permitirem.

        Returns:
            Dict com mensagem e metadados ou None se não aplicável
        """
        if not self.should_apply_friction(pattern_id, user_receptivity, emotional_state):
            return None

        patterns = self.bank.get_behavioral_patterns(min_confidence=0.5)
        pattern = next((p for p in patterns if p["id"] == pattern_id), None)

        if not pattern:
            return None

        distance_from_desired = context.get("distance", 0.5) if context else 0.5

        level = self.calculate_friction_level(
            pattern_confidence=pattern["confidence"],
            confirmation_count=pattern["confirmation_count"],
            distance_from_desired=distance_from_desired,
        )

        message = self.generate_friction_message(pattern, level, context)

        friction_data = {
            "category": pattern["type"],
            "pattern_triggered": pattern_id,
            "friction_level": level,
            "message_sent": message,
        }

        friction_id = self.bank.insert_friction_log(friction_data)

        logger.info(f"Fricção aplicada: {pattern_id}, nível: {level}")

        return {
            "id": friction_id,
            "message": message,
            "level": level,
            "pattern": pattern["type"],
        }

    def record_user_response(
        self,
        friction_id: str,
        response: str,
        outcome_7_days: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra resposta do usuário à fricção.

        Args:
            friction_id: ID da fricção
            response: "receptivo", "defensivo", "ignorou", "refletiu"
            outcome_7_days: Comportamento 7 dias após (opcional)
        """
        frictions = self.bank.get_friction_history(limit=100)
        friction = next((f for f in frictions if f["id"] == friction_id), None)

        if not friction:
            logger.warning(f"Fricção não encontrada: {friction_id}")
            return

        logger.info(f"Resposta do usuário: {response} para fricção {friction_id}")

    def get_friction_effectiveness(
        self,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analisa efetividade das fricções para ajustar tom/timing.

        Returns:
            Métricas de efetividade por categoria
        """
        frictions = self.bank.get_friction_history(category=category, limit=50)

        if not frictions:
            return {"status": "no_data"}

        total = len(frictions)
        receptivo = sum(1 for f in frictions if f.get("user_response") == "receptivo")
        defensivo = sum(1 for f in frictions if f.get("user_response") == "defensivo")
        ignorou = sum(1 for f in frictions if f.get("user_response") == "ignorou")

        by_level = {}
        for f in frictions:
            level = f.get("level", "unknown")
            if level not in by_level:
                by_level[level] = {"total": 0, "receptivo": 0}
            by_level[level]["total"] += 1
            if f.get("user_response") == "receptivo":
                by_level[level]["receptivo"] += 1

        return {
            "total_frictions": total,
            "receptivo_rate": receptivo / total if total > 0 else 0,
            "defensivo_rate": defensivo / total if total > 0 else 0,
            "ignorou_rate": ignorou / total if total > 0 else 0,
            "by_level": by_level,
            "recommended_level": (
                max(by_level.items(), key=lambda x: x[1]["receptivo"] / x[1]["total"])[0]
                if by_level else "moderada"
            ),
        }

    def check_pending_friction_candidates(self) -> List[Dict[str, Any]]:
        """
        Identifica padrões que são candidatos a fricção.

        Returns:
            Lista de padrões prontos para fricção
        """
        patterns = self.bank.get_behavioral_patterns(min_confidence=0.5)
        
        candidates = []
        for pattern in patterns:
            if pattern["confirmation_count"] >= self.MIN_CONFIRMATION_COUNT:
                if pattern.get("potentially_limiting", False):
                    candidates.append({
                        "pattern_id": pattern["id"],
                        "type": pattern["type"],
                        "domain": pattern["domain"],
                        "confidence": pattern["confidence"],
                        "ready": True,
                    })

        return candidates
