# shared/intent/conversation_analyzer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Implementação inicial de extração de sinais em tempo real
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Extrai sinais durante conversas
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Conversation Analyzer — Extração de sinais em tempo real durante conversas.

INTENÇÃO: A capacidade de "ver" o usuário enquanto ele fala.
Não transcrever — extrair sinais estruturados em paralelo, sem interromper o fluxo.

O que extrai:
1. PADRÕES COMPORTAMENTAIS mencionados
2. ESTADO EMOCIONAL revelado (inferido, não declarado)
3. EVENTOS EXTERNOS citados
4. ATRIBUIÇÃO DE CAUSA (erros próprios vs externos)
5. CONTRADIÇÕES com perfil conhecido
6. VALORES REVELADOS
7. FRICÇÃO POTENCIAL
8. HORIZONTE IMPLÍCITO

INVARIANTE: Inferências emocionais têm decay automático de 7 dias
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import litellm
from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class ConversationAnalyzer:
    """
    Analisador de conversas em tempo real.

    INTENÇÃO: Extrai sinais estruturados de conversas sem interromper o fluxo.
    """

    EXTRACTION_PROMPT = """Analise este trecho de conversa e extraia sinais estruturados.

Você deve analisar e retornar APENAS um JSON válido (sem markdown, sem explicações).

O formato de saída deve ser:

{{
  "behavioral_patterns": {{
    "risk_management": {{
      "stop_loss": "padrão detectado ou 'nenhum'",
      "position_sizing": "padrão detectado",
      "leverage": "padrão detectado"
    }},
    "trading_psychology": {{
      "bias": "viés detectado",
      "overtrade": "padrão detectado",
      "emotional_trigger": "gatilho detectado"
    }}
  }},
  "emotional_state": {{
    "inferred": "estado emocional inferido pelo tom (neutro/otimista/ansioso/frustrado/desesperado)",
    "confidence": 0.0-1.0,
    "reasoning": "por que inferiu isso"
  }},
  "external_events": [
    {{"event": "evento descrito", "date": "data se mencionada", "impact": "impacto descrito"}}
  ],
  "self_attribution": {{
    "owns_errors": true/false,
    "distinguishes_external": true/false,
    "insight_level": "baixo/medio/alto"
  }},
  "friction_potential": {{
    "padrão_detectado": {{
      "confirmado_por": "narrativa_explícita/inferido",
      "candidato_para_fricao": true/false,
      "timing_sugerido": "agora/mais_tarde/nunca"
    }}
  }},
  "growth_horizon_implicit": {{
    "current_state": "estado atual implícito na fala",
    "desired_state": "futuro desejado implícito",
    "awareness_gap": "alta/baixa"
  }},
  "values_revealed": ["valor 1", "valor 2"]
}}

Trecho da conversa:
{conversation_text}

Perfil atual do usuário:
{user_profile}

Horizontes de crescimento ativos:
{growth_targets}

Retorne APENAS o JSON, sem texto adicional."""

    def __init__(self, causal_bank: CausalBank, model: str = "claude"):
        self.bank = causal_bank
        self.model = model

    def analyze_conversation(
        self,
        conversation_text: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analisa trecho de conversa e extrai sinais.

        Args:
            conversation_text: Texto da conversa
            conversation_id: ID da conversa (opcional)

        Returns:
            Sinais extraídos estruturados
        """
        user_profile = self._get_user_profile()
        growth_targets = self._get_growth_targets()

        prompt = self.EXTRACTION_PROMPT.format(
            conversation_text=conversation_text[:2000],
            user_profile=json.dumps(user_profile, indent=2) if user_profile else "Nenhum perfil declarado",
            growth_targets=json.dumps(growth_targets, indent=2) if growth_targets else "Nenhum horizonte declarado",
        )

        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            
            extracted = json.loads(content)

            signal_data = {
                "conversation_id": conversation_id,
                "behavioral_patterns": extracted.get("behavioral_patterns", {}),
                "emotional_state_inferred": extracted.get("emotional_state", {}).get("inferred"),
                "emotional_confidence": extracted.get("emotional_state", {}).get("confidence", 0.5),
                "emotional_decay_date": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat() if extracted.get("emotional_state", {}).get("inferred") else None,
                "external_events": extracted.get("external_events", []),
                "self_attribution": extracted.get("self_attribution", {}),
                "values_revealed": extracted.get("values_revealed", []),
                "friction_potential": extracted.get("friction_potential", {}),
                "growth_horizon_implicit": extracted.get("growth_horizon_implicit", {}),
            }

            signal_id = self.bank.insert_conversation_signal(signal_data)

            logger.info(f"Sinais de conversa extraídos: {signal_id}")

            return {
                "signal_id": signal_id,
                "extracted": extracted,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}")
            return {"error": "parse_error", "raw": content if 'content' in locals() else None}
        except Exception as e:
            logger.error(f"Erro ao analisar conversa: {e}")
            return {"error": str(e)}

    def analyze_and_update_patterns(
        self,
        conversation_text: str,
    ) -> Dict[str, Any]:
        """
        Analisa conversa e atualiza padrões comportamentais.

        Returns:
            Sinais extraídos + padrões atualizados
        """
        result = self.analyze_conversation(conversation_text)

        if "error" in result:
            return result

        extracted = result.get("extracted", {})

        behavioral = extracted.get("behavioral_patterns", {})
        
        if behavioral:
            self._update_patterns_from_extraction(behavioral)

        friction_potential = extracted.get("friction_potential", {})
        
        for pattern_type, data in friction_potential.items():
            if data.get("candidato_para_fricao"):
                logger.info(f"Padrão limitante detectado: {pattern_type}")

        return result

    def get_recent_signals(
        self,
        days: int = 7,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Busca sinais de conversas recentes.

        Args:
            days: Dias de retrospectiva
            include_expired: Se True, inclui inferências emocionais expiradas
        """
        signals = self.bank.get_recent_conversation_signals(days=days)

        now = datetime.now(timezone.utc)
        
        filtered = []
        for signal in signals:
            if signal.get("emotional") and not include_expired:
                continue
            
            filtered.append(signal)

        return filtered

    def detect_emotional_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Detecta tendências emocionais ao longo do tempo.

        Returns:
            Análise de tendências emocionais
        """
        signals = self.bank.get_recent_conversation_signals(days=days, limit=100)

        emotional_counts = {}
        
        for signal in signals:
            emotion = signal.get("emotional")
            if emotion:
                emotional_counts[emotion] = emotional_counts.get(emotion, 0) + 1

        total = sum(emotional_counts.values())
        
        if total == 0:
            return {"status": "no_data"}

        trend = "stable"
        
        if len(signals) >= 14:
            first_half = signals[len(signals)//2:]
            second_half = signals[:len(signals)//2]
            
            neg_first = sum(1 for s in first_half if s.get("emotional") in ["frustrado", "desesperado", "ansioso"])
            neg_second = sum(1 for s in second_half if s.get("emotional") in ["frustrado", "desesperado", "ansioso"])
            
            if neg_second > neg_first * 1.5:
                trend = "worsening"
            elif neg_first > neg_second * 1.5:
                trend = "improving"

        return {
            "total_signals": total,
            "emotional_distribution": {
                k: v / total for k, v in emotional_counts.items()
            },
            "trend": trend,
        }

    def _get_user_profile(self) -> Dict[str, Any]:
        """Busca perfil declarado do usuário."""
        profile = self.bank.get_latest_declared_profile()
        return profile or {}

    def _get_growth_targets(self) -> List[Dict[str, Any]]:
        """Busca horizontes de crescimento ativos."""
        return self.bank.get_active_growth_targets()

    def _update_patterns_from_extraction(self, behavioral: Dict[str, Any]) -> None:
        """Atualiza padrões comportamentais com dados extraídos."""
        
        pattern_map = {
            "stop_loss": {
                "domain": "trading",
                "type": "stop_loss",
                "description_template": "uso de stop loss",
            },
            "position_sizing": {
                "domain": "trading", 
                "type": "position_sizing",
                "description_template": "gestão de tamanho de posição",
            },
            "leverage": {
                "domain": "trading",
                "type": "leverage",
                "description_template": "uso de alavancagem",
            },
            "bias": {
                "domain": "trading",
                "type": "vies_comportamental",
                "description_template": "viés comportamental",
            },
            "overtrade": {
                "domain": "trading",
                "type": "overtrade",
                "description_template": "operação excessiva",
            },
            "emotional_trigger": {
                "domain": "trading",
                "type": "emotional_trading",
                "description_template": "operação emocional",
            },
        }

        for category, patterns in behavioral.items():
            if not isinstance(patterns, dict):
                continue
                
            for pattern_type, value in patterns.items():
                if not value or value == "nenhum":
                    continue

                key = pattern_type
                if key not in pattern_map:
                    continue

                mapping = pattern_map[key]
                
                existing = self.bank.get_behavioral_patterns(
                    domain=mapping["domain"],
                    min_confidence=0.0,
                )
                
                matching = [p for p in existing if p["type"] == mapping["type"]]
                
                if matching:
                    self.bank.update_behavioral_pattern(
                        matching[0]["id"],
                        {
                            "source": "conversation",
                            "value": value,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                else:
                    self.bank.insert_behavioral_pattern({
                        "domain": mapping["domain"],
                        "pattern_type": mapping["type"],
                        "description": f"{mapping['description_template']}: {value}",
                        "confidence": 0.3,
                        "confirmation_count": 1,
                        "potentially_limiting": pattern_type in ["vies_comportamental", "overtrade", "emotional_trading"],
                        "evidence": [{
                            "source": "conversation",
                            "value": value,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }],
                    })
