# shared/intent/behavioral_pattern_detector.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v1 — Implementação inicial de detecção de padrões comportamentais
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Detecta padrões recorrentes
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

"""
Behavioral Pattern Detector — Detecção de padrões recorrentes com confidence crescente.

INTENÇÃO: Detecta padrões comportamentais recorrentes e os classifica
com confiança que aumenta a cada confirmação.

Padrões de exemplo:
- Revenge trading: operar logo após perda
- Viés de alta estrutural: nunca operar short
- Stop loss avoidance: nunca usar stop
- Overtrading: operar demais
- Size escalation: aumentar tamanho após ganhos

INVARIANTE: Confidence aumenta com confirmações, nunca diminui
INVARIANTE: Padrões potencialmente limitantes são marcados para fricção
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class BehavioralPatternDetector:
    """
    Detector de padrões comportamentais.

    INTENÇÃO: Identifica padrões recorrentes no comportamento do usuário
    e os classifica com confiança crescente.
    """

    KNOWN_PATTERNS = {
        "revenge_trading": {
            "domain": "trading",
            "description": "Operar emocionalmente após perda",
            "detection_rule": "operou_dentro_de_X_minutos_após_perda",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 3,
        },
        "vies_alta": {
            "domain": "trading",
            "description": "Viés estrutural para comprar/long",
            "detection_rule": "zero_operacoes_short_em_X_dias",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 5,
        },
        "stop_loss_avoidance": {
            "domain": "trading",
            "description": "Evitar uso de stop loss",
            "detection_rule": "taxa_stop_loss_abaixo_de_X",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 5,
        },
        "overtrading": {
            "domain": "trading",
            "description": "Operar acima do optimal",
            "detection_rule": "trades_por_semana_maior_que_X",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 3,
        },
        "size_escalation": {
            "domain": "trading",
            "description": "Aumentar tamanho após ganhos",
            "detection_rule": "tamanho_posicao_aumentou_após_ganho",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 3,
        },
        "fomo_entry": {
            "domain": "trading",
            "description": "Entrar por FOMO após movimento",
            "detection_rule": "entrada_após_movimento_strong",
            "potentially_limiting": True,
            "min_confirmations_for_limiting": 3,
        },
        "delay_after_loss": {
            "domain": "trading",
            "description": "Esperar entre perdas",
            "detection_rule": "tempo_entre_trades_apos_perda",
            "potentially_limiting": False,
            "min_confirmations_for_limiting": 3,
        },
    }

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def detect_from_execution(self, execution_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detecta padrões a partir de uma execução.

        Args:
            execution_data: Dados da execução (trade)

        Returns:
            Lista de padrões detectados
        """
        detected = []
        
        result = execution_data.get("result", 0)
        
        if result is not None and result < 0:
            revenge_detected = self._check_revenge_trading(execution_data)
            if revenge_detected:
                detected.append(revenge_detected)

        direction = execution_data.get("direction", "")
        if direction.lower() != "sell" and direction.lower() != "short":
            vies_alta = self._check_vies_alta()
            if vies_alta:
                detected.append(vies_alta)

        self._check_stop_loss_usage(execution_data)
        self._check_overtrading(execution_data)

        return detected

    def detect_from_conversation(self, text: str) -> List[Dict[str, Any]]:
        """
        Detecta padrões mencionados em conversas.

        Args:
            text: Texto da conversa

        Returns:
            Lista de padrões detectados
        """
        detected = []
        text_lower = text.lower()

        if any(word in text_lower for word in ["arrependido", "queria ter esperado", "agiu rápido"]):
            detected.append({
                "type": "fomo_entry",
                "confidence": 0.6,
                "evidence": {"source": "conversation", "text": text[:100]},
            })

        if any(word in text_lower for word in ["nunca curto", "só compro", "sempre long"]):
            detected.append({
                "type": "vies_alta",
                "confidence": 0.7,
                "evidence": {"source": "conversation", "text": text[:100]},
            })

        if any(word in text_lower for word in ["sem stop", "não coloco stop", "stop não funciona"]):
            detected.append({
                "type": "stop_loss_avoidance",
                "confidence": 0.7,
                "evidence": {"source": "conversation", "text": text[:100]},
            })

        for pattern in detected:
            self._record_pattern_detection(pattern["type"], pattern["confidence"], pattern["evidence"])

        return detected

    def _check_revenge_trading(self, execution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Verifica se houve revenge trading (operar logo após perda).
        
        Critério: nova execução em < 30 minutos após uma perda.
        """
        from datetime import timedelta
        
        # Buscar execuções recentes do banco
        stats = self.bank.get_performance_stats()
        recent_trades = stats.get("recent_trades", [])
        
        if len(recent_trades) < 2:
            return None
        
        # Verificar se a última trade antes desta foi uma perda
        last_trade = recent_trades[-1] if recent_trades else None
        if not last_trade:
            return None
        
        last_result = last_trade.get("result", 0)
        last_timestamp = last_trade.get("timestamp")
        
        if last_result >= 0 or not last_timestamp:
            return None
        
        # Verificar se a execução atual é muito próxima da perda
        try:
            if isinstance(last_timestamp, str):
                last_time = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
            else:
                last_time = last_timestamp
            
            now = datetime.now(timezone.utc)
            time_diff = now - last_time
            
            if time_diff < timedelta(minutes=30):
                evidence = {
                    "source": "execution_timing",
                    "minutes_after_loss": time_diff.total_seconds() / 60,
                    "loss_amount": last_result,
                    "timestamp": now.isoformat(),
                }
                
                self._record_pattern_detection("revenge_trading", 0.6, evidence)
                
                return {
                    "type": "revenge_trading",
                    "confidence": 0.6,
                    "evidence": evidence,
                }
        except Exception as e:
            logger.debug(f"Erro ao verificar revenge trading: {e}")
        
        return None

    def _check_vies_alta(self) -> Optional[Dict[str, Any]]:
        """
        Verifica se usuário tem viés de alta estrutural.
        """
        existing = self.bank.get_behavioral_patterns(domain="trading", min_confidence=0.0)
        
        vies = [p for p in existing if p["type"] == "vies_alta"]
        
        if not vies:
            return {
                "type": "vies_alta",
                "confidence": 0.3,
                "evidence": {"source": "first_observation"},
            }
        
        return None

    def _check_stop_loss_usage(self, execution_data: Dict[str, Any]) -> None:
        """
        Verifica uso de stop loss.
        """
        has_stop = execution_data.get("has_stop_loss", False)
        
        existing = self.bank.get_behavioral_patterns(domain="trading", min_confidence=0.0)
        
        stop_pattern = next((p for p in existing if p["type"] == "stop_loss_avoidance"), None)
        
        if has_stop:
            if stop_pattern:
                logger.debug(f"Padrão stop_loss_avoidance não confirmado nesta execução")
        else:
            if stop_pattern:
                self.bank.update_behavioral_pattern(
                    stop_pattern["id"],
                    {"source": "execution", "execution_id": execution_data.get("id")}
                )
            else:
                self.bank.insert_behavioral_pattern({
                    "domain": "trading",
                    "pattern_type": "stop_loss_avoidance",
                    "description": "Evita usar stop loss",
                    "confidence": 0.3,
                    "confirmation_count": 1,
                    "potentially_limiting": True,
                    "evidence": [{"source": "execution", "execution_id": execution_data.get("id")}],
                })

    def _check_overtrading(self, execution_data: Dict[str, Any]) -> None:
        """
        Verifica se há overtrading (frequência excessiva de operações).
        
        Critério: > 10 operações nas últimas 24h.
        """
        stats = self.bank.get_performance_stats()
        recent_trades = stats.get("recent_trades", [])
        
        now = datetime.now(timezone.utc)
        trades_24h = 0
        
        for trade in recent_trades:
            ts = trade.get("timestamp")
            if not ts:
                continue
            try:
                if isinstance(ts, str):
                    trade_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    trade_time = ts
                
                from datetime import timedelta
                if now - trade_time < timedelta(hours=24):
                    trades_24h += 1
            except Exception:
                continue
        
        threshold = 10
        if trades_24h >= threshold:
            evidence = {
                "source": "frequency_check",
                "trades_in_24h": trades_24h,
                "threshold": threshold,
                "timestamp": now.isoformat(),
            }
            self._record_pattern_detection("overtrading", 0.5, evidence)
            logger.info(f"Overtrading detectado: {trades_24h} trades em 24h (limite: {threshold})")

    def _record_pattern_detection(
        self,
        pattern_type: str,
        confidence: float,
        evidence: Dict[str, Any],
    ) -> str:
        """
        Registra detecção de padrão.
        """
        existing = self.bank.get_behavioral_patterns(
            domain=self.KNOWN_PATTERNS.get(pattern_type, {}).get("domain", "trading"),
            min_confidence=0.0
        )
        
        matching = [p for p in existing if p["type"] == pattern_type]
        
        if matching:
            self.bank.update_behavioral_pattern(
                matching[0]["id"],
                {"source": evidence.get("source", "unknown")}
            )
            return matching[0]["id"]
        else:
            pattern_info = self.KNOWN_PATTERNS.get(pattern_type, {})
            
            return self.bank.insert_behavioral_pattern({
                "domain": pattern_info.get("domain", "trading"),
                "pattern_type": pattern_type,
                "description": pattern_info.get("description", pattern_type),
                "confidence": confidence,
                "confirmation_count": 1,
                "potentially_limiting": pattern_info.get("potentially_limiting", False),
                "evidence": [evidence],
            })

    def get_limiting_patterns(self, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Retorna padrões potencialmente limitantes com alta confiança.
        """
        patterns = self.bank.get_behavioral_patterns(min_confidence=min_confidence)
        
        limiting = [p for p in patterns if p.get("potentially_limiting", False)]
        
        return sorted(limiting, key=lambda x: x["confidence"], reverse=True)

    def get_patterns_ready_for_friction(self) -> List[Dict[str, Any]]:
        """
        Retorna padrões prontos para fricção.

        Condições:
        - potencialmente limitantes
        - confidence >= 0.6
        - confirmação >= 5
        """
        patterns = self.get_limiting_patterns(min_confidence=0.6)
        
        ready = [p for p in patterns if p["confirmation_count"] >= 5]
        
        return ready

    def analyze_pattern_history(
        self,
        pattern_type: str,
    ) -> Dict[str, Any]:
        """
        Analisa histórico de um padrão específico.
        """
        patterns = self.bank.get_behavioral_patterns(min_confidence=0.0)
        
        matching = [p for p in patterns if p["type"] == pattern_type]
        
        if not matching:
            return {"status": "not_found"}

        pattern = matching[0]
        
        return {
            "pattern_type": pattern_type,
            "current_confidence": pattern["confidence"],
            "confirmation_count": pattern["confirmation_count"],
            "last_detected": pattern.get("last_detected"),
            "potentially_limiting": pattern.get("potentially_limiting"),
            "ready_for_friction": (
                pattern["confidence"] >= 0.6 and
                pattern["confirmation_count"] >= 5 and
                pattern.get("potentially_limiting", False)
            ),
        }
