# shared/intent/monitor_orchestrator.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: v2.0 - Integração com CausalBank + ajuste dinâmico por intenção
#
# IMPACTO GÊMEO VPS: Orquestra monitores globais com persistência
# IMPACTO GÊMEO LOCAL: Usa mesmo código, mas contexto local
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — interface idêntica

"""
Monitor Orchestrator — Orquestra monitores dinâmicos por relevância pessoal.

INTENÇÃO: Em um agente global, monitores não são fixos. Eles nascem,
pausam e morrem conforme a relevância pessoal muda. Se o usuário
começa a investir em crypto, um monitor de crypto nasce. Se para,
o monitor é pausado e eventualmente destruído.

INVARIANTE: Toda mudança de ciclo de vida é logada no Banco de Causalidade.
INVARIANTE: Monitores pausados há mais de 30 dias sem relevância são destruídos.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)

DOMAIN_MONITOR_MAP = {
    "finance": ["financial", "commodities", "corporate", "rare_earths"],
    "energy": ["energy"],
    "innovation": ["innovation"],
    "geopolitics": ["geopolitics", "macro"],
    "social": ["social_media"],
    "health": [],
    "crypto": [],
}

RELEVANCE_THRESHOLD_CREATE = 0.6
RELEVANCE_THRESHOLD_PAUSE = 0.3
PAUSE_DAYS_BEFORE_DESTROY = 30


class MonitorOrchestrator:
    """
    Gerencia ciclo de vida de monitores dinâmicos.

    INTENÇÃO: O agente é global por design, mas foca por relevância pessoal.
    Se saúde se torna relevante para o usuário, monitores de saúde nascem.
    Se finanças perdem relevância, monitores financeiros são pausados.
    """

    def __init__(self, causal_bank: Optional["CausalBank"] = None):
        """
        Args:
            causal_bank: Banco de Causalidade para persistir eventos de ciclo de vida.
                        Se None, opera em modo memory-only (útil para testes).
        """
        self._causal_bank = causal_bank
        self._active_monitors: Dict[str, Dict] = {}
        self._paused_monitors: Dict[str, Dict] = {}
        self._lifecycle_log: List[Dict] = []
        self._domain_relevance: Dict[str, float] = {}

    def set_domain_relevance(self, domain: str, relevance: float) -> None:
        """
        Define a relevância de um domínio para o usuário.

        INTENÇÃO: Usado pelo IntentMapper ou DecisionLearner para informar
        mudanças de interesse do usuário. Relevância 0.0-1.0.

        Args:
            domain: Domínio (ex: "finance", "energy", "health")
            relevance: Score de relevância entre 0.0 e 1.0
        """
        if not 0.0 <= relevance <= 1.0:
            raise ValueError(f"Relevância deve estar entre 0.0 e 1.0, recebido: {relevance}")
        
        old_relevance = self._domain_relevance.get(domain, 0.0)
        self._domain_relevance[domain] = relevance
        
        logger.debug(f"Relevância de {domain}: {old_relevance:.2f} → {relevance:.2f}")
        
        self._auto_adjust_monitors(domain, old_relevance, relevance)

    def _auto_adjust_monitors(self, domain: str, old_relevance: float, new_relevance: float) -> None:
        """
        Ajusta monitores automaticamente baseado em mudança de relevância.

        INTENÇÃO: Se relevância sobe acima do threshold, cria monitores.
        Se cai abaixo, pausa. Automação respeita princípio de reversibilidade.
        """
        monitor_names = DOMAIN_MONITOR_MAP.get(domain, [])
        
        if not monitor_names:
            logger.debug(f"Nenhum monitor mapeado para domínio: {domain}")
            return
        
        if old_relevance < RELEVANCE_THRESHOLD_CREATE <= new_relevance:
            for name in monitor_names:
                if name not in self._active_monitors and name not in self._paused_monitors:
                    self.create_monitor(
                        name=name,
                        domain=domain,
                        config={},
                        triggered_by="relevance_change",
                    )
                    logger.info(f"Monitor {name} criado automaticamente (relevância: {new_relevance:.2f})")
        
        elif old_relevance >= RELEVANCE_THRESHOLD_PAUSE > new_relevance:
            for name in monitor_names:
                if name in self._active_monitors:
                    self.pause_monitor(
                        name=name,
                        reason=f"Relevância do domínio caiu para {new_relevance:.2f}",
                    )
                    logger.info(f"Monitor {name} pausado automaticamente (relevância: {new_relevance:.2f})")

    def get_domain_relevance(self, domain: str) -> float:
        """Retorna a relevância atual de um domínio."""
        return self._domain_relevance.get(domain, 0.0)

    def create_monitor(
        self,
        name: str,
        domain: str,
        config: Dict[str, Any],
        triggered_by: str = "orchestrator",
    ) -> Dict[str, Any]:
        """Cria e ativa um novo monitor."""
        if name in self._active_monitors:
            return {"status": "already_active", "name": name}

        if name in self._paused_monitors:
            return self.resume_monitor(name)

        monitor = {
            "name": name,
            "domain": domain,
            "config": config,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "triggered_by": triggered_by,
        }

        self._active_monitors[name] = monitor
        self._log_lifecycle(name, domain, "created", triggered_by, "")

        logger.info(f"Monitor criado: {name} (domínio: {domain})")
        return {"status": "created", "name": name, "domain": domain}

    def pause_monitor(self, name: str, reason: str) -> Dict[str, Any]:
        """Pausa um monitor ativo."""
        if name not in self._active_monitors:
            if name in self._paused_monitors:
                return {"status": "already_paused", "name": name}
            return {"status": "not_found", "name": name}

        monitor = self._active_monitors.pop(name)
        monitor["status"] = "paused"
        monitor["paused_at"] = datetime.now(timezone.utc).isoformat()
        monitor["pause_reason"] = reason
        self._paused_monitors[name] = monitor

        self._log_lifecycle(name, monitor["domain"], "paused", "orchestrator", reason)

        logger.info(f"Monitor pausado: {name} — {reason}")
        return {"status": "paused", "name": name}

    def resume_monitor(self, name: str) -> Dict[str, Any]:
        """Resume um monitor pausado."""
        if name not in self._paused_monitors:
            return {"status": "not_found", "name": name}

        monitor = self._paused_monitors.pop(name)
        monitor["status"] = "active"
        monitor["resumed_at"] = datetime.now(timezone.utc).isoformat()
        del monitor["paused_at"]
        del monitor["pause_reason"]
        self._active_monitors[name] = monitor

        self._log_lifecycle(name, monitor["domain"], "resumed", "orchestrator", "")

        logger.info(f"Monitor resumido: {name}")
        return {"status": "resumed", "name": name}

    def destroy_monitor(self, name: str, reason: str) -> Dict[str, Any]:
        """Remove permanentemente um monitor."""
        source = None
        if name in self._active_monitors:
            source = self._active_monitors.pop(name)
        elif name in self._paused_monitors:
            source = self._paused_monitors.pop(name)

        if not source:
            return {"status": "not_found", "name": name}

        self._log_lifecycle(name, source["domain"], "destroyed", "orchestrator", reason)

        logger.info(f"Monitor destruído: {name} — {reason}")
        return {"status": "destroyed", "name": name}

    def cleanup_stale_monitors(self) -> List[str]:
        """
        Destrói monitores pausados há mais de N dias sem relevância.

        INTENÇÃO: Evita acúmulo de monitores zombie. Se um domínio permanece
        irrelevante por muito tempo, o monitor é destruído.

        Returns:
            Lista de nomes de monitores destruídos.
        """
        destroyed = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=PAUSE_DAYS_BEFORE_DESTROY)

        to_destroy = []
        for name, monitor in self._paused_monitors.items():
            paused_at_str = monitor.get("paused_at", "")
            if paused_at_str:
                try:
                    paused_at = datetime.fromisoformat(paused_at_str.replace("Z", "+00:00"))
                    domain = monitor.get("domain", "")
                    relevance = self._domain_relevance.get(domain, 0.0)
                    
                    if paused_at < cutoff and relevance < RELEVANCE_THRESHOLD_PAUSE:
                        to_destroy.append(name)
                except (ValueError, TypeError):
                    pass

        for name in to_destroy:
            result = self.destroy_monitor(
                name=name,
                reason=f"Pausado há mais de {PAUSE_DAYS_BEFORE_DESTROY} dias sem relevância",
            )
            if result["status"] == "destroyed":
                destroyed.append(name)

        return destroyed

    def get_active_monitors(self) -> List[Dict]:
        """Retorna lista de monitores ativos."""
        return list(self._active_monitors.values())

    def get_paused_monitors(self) -> List[Dict]:
        """Retorna lista de monitores pausados."""
        return list(self._paused_monitors.values())

    def get_lifecycle_log(self) -> List[Dict]:
        """Retorna log completo de ciclo de vida."""
        return self._lifecycle_log.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do orchestrator."""
        return {
            "active_count": len(self._active_monitors),
            "paused_count": len(self._paused_monitors),
            "domain_relevance": dict(self._domain_relevance),
            "total_lifecycle_events": len(self._lifecycle_log),
        }

    def _log_lifecycle(
        self, name: str, domain: str, action: str,
        triggered_by: str, reason: str = "",
    ):
        """Registra evento no log de ciclo de vida e no Banco de Causalidade."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "monitor_name": name,
            "domain": domain,
            "action": action,
            "triggered_by": triggered_by,
            "reason": reason,
        }
        
        self._lifecycle_log.append(event)

        if self._causal_bank:
            try:
                self._causal_bank.insert_monitor_lifecycle(event)
            except Exception as e:
                logger.error(f"Falha ao registrar lifecycle no banco: {e}")
