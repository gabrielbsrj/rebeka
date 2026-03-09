import asyncio
import hashlib
import inspect
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FocusItem:
    """Representa um item no workspace global da Rebeka."""

    focus_id: str
    kind: str
    domain: str
    title: str
    summary: str
    priority: float
    recommended_action: str
    source_ids: List[str]
    confidence: float


class GlobalWorkspaceService:
    """
    Camada de global workspace para a trilha estavel do gemeo VPS.

    Objetivo:
    - consolidar sinais do mundo, tensoes do usuario e horizontes ativos;
    - produzir uma agenda cognitiva curta e priorizada;
    - persistir snapshots relevantes para permitir reflexao posterior.
    """

    DOMAIN_BASE_PRIORITIES = {
        "survival": 0.95,
        "finance": 0.85,
        "crypto": 0.82,
        "macro": 0.78,
        "commodities": 0.74,
        "energy": 0.72,
        "corporate": 0.68,
        "innovation": 0.65,
        "communication": 0.60,
        "user": 0.88,
        "growth": 0.76,
    }

    DOMAIN_ACTIONS = {
        "survival": "alert",
        "finance": "research",
        "crypto": "research",
        "macro": "research",
        "commodities": "research",
        "energy": "research",
        "corporate": "monitor",
        "innovation": "monitor",
        "communication": "follow_up",
        "user": "follow_up",
        "growth": "plan",
    }

    URGENT_KEYWORDS = (
        "crise",
        "crash",
        "queda",
        "fall",
        "emerg",
        "urg",
        "falha",
        "ataque",
        "attack",
        "breach",
        "colapso",
        "drawdown",
        "liquidez",
        "hospital",
    )

    def __init__(
        self,
        bank,
        chat_manager,
        check_interval: int = 300,
        top_n: int = 5,
        tracked_domains: Optional[List[str]] = None,
    ):
        self.bank = bank
        self.chat_manager = chat_manager
        self.check_interval = check_interval
        self.top_n = top_n
        self.tracked_domains = tracked_domains or [
            "survival",
            "finance",
            "crypto",
            "macro",
            "commodities",
            "energy",
            "innovation",
            "corporate",
        ]
        self._last_signature: Optional[str] = None
        self._snapshot_consumers: List[Callable[[Dict[str, Any]], Any]] = []
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info("Global Workspace Service iniciado.")

        await asyncio.sleep(8)

        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as exc:
                logger.error(f"Erro no Global Workspace Service: {exc}")
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self.is_running = False

    async def run_cycle(self) -> Dict[str, Any]:
        snapshot = self.build_snapshot()
        if snapshot["signature"] == self._last_signature:
            logger.debug("Workspace sem mudancas materiais.")
            return snapshot

        self.persist_snapshot(snapshot)
        self.publish_snapshot(snapshot)
        await self.notify_snapshot_consumers(snapshot)
        self._last_signature = snapshot["signature"]
        return snapshot

    def register_snapshot_consumer(self, consumer: Callable[[Dict[str, Any]], Any]) -> None:
        if consumer not in self._snapshot_consumers:
            self._snapshot_consumers.append(consumer)

    async def notify_snapshot_consumers(self, snapshot: Dict[str, Any]) -> None:
        for consumer in self._snapshot_consumers:
            try:
                result = consumer(snapshot)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.error(f"Erro ao notificar consumidor de snapshot: {exc}")

    def build_snapshot(self) -> Dict[str, Any]:
        growth_targets = self.bank.get_active_growth_targets()
        conversation_signals = self.bank.get_recent_conversation_signals(days=7, limit=20)
        world_signals = self._collect_world_signals()

        focuses: List[FocusItem] = []
        focuses.extend(
            self._focus_from_signal(signal, growth_targets, conversation_signals)
            for signal in world_signals
        )
        focuses.extend(self._focus_from_growth_target(target, conversation_signals) for target in growth_targets)
        focuses.extend(
            self._focus_from_conversation_signal(signal)
            for signal in conversation_signals
            if self._conversation_has_active_tension(signal)
        )

        ranked_focuses = self._deduplicate_focuses(focuses)
        ranked_focuses.sort(key=lambda item: item.priority, reverse=True)
        ranked_focuses = ranked_focuses[: self.top_n]

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "focuses": [asdict(item) for item in ranked_focuses],
            "summary": self._make_summary(ranked_focuses),
        }
        snapshot["signature"] = self._calculate_signature(snapshot["focuses"])
        return snapshot

    def persist_snapshot(self, snapshot: Dict[str, Any]) -> None:
        try:
            self.bank.insert_system_event(
                {
                    "event_type": "global_workspace_snapshot",
                    "description": snapshot["summary"],
                    "context": {
                        "signature": snapshot["signature"],
                        "focus_count": len(snapshot["focuses"]),
                        "focuses": snapshot["focuses"],
                    },
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir snapshot do workspace: {exc}")

    def publish_snapshot(self, snapshot: Dict[str, Any]) -> None:
        if not snapshot["focuses"]:
            return

        lines = ["**Workspace Global Atualizado**", "", snapshot["summary"], "", "Focos ativos:"]
        for idx, focus in enumerate(snapshot["focuses"][:3], start=1):
            lines.append(
                f"{idx}. [{focus['domain']}] {focus['title']} "
                f"(prioridade {focus['priority']:.2f}, acao: {focus['recommended_action']})"
            )

        self.chat_manager.push_insight("\n".join(lines))

    def _collect_world_signals(self) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        for domain in self.tracked_domains:
            try:
                signals.extend(self.bank.get_similar_signals(domain=domain, limit=5))
            except Exception as exc:
                logger.error(f"Erro ao coletar sinais do dominio {domain}: {exc}")
        return signals

    def _focus_from_signal(
        self,
        signal: Dict[str, Any],
        growth_targets: List[Dict[str, Any]],
        conversation_signals: List[Dict[str, Any]],
    ) -> FocusItem:
        signal_text = f"{signal.get('title', '')} {signal.get('content', '')}".lower()
        domain = signal.get("domain", "unknown")
        base_relevance = float(signal.get("relevance_score", 0.0))
        domain_bonus = self.DOMAIN_BASE_PRIORITIES.get(domain, 0.55)
        urgent_bonus = 0.12 if any(keyword in signal_text for keyword in self.URGENT_KEYWORDS) else 0.0
        recency_bonus = self._recency_bonus(signal.get("created_at"))
        target_bonus = 0.08 if any(target.get("domain") == domain for target in growth_targets) else 0.0
        tension_bonus = 0.08 if self._signal_touches_user_tension(signal_text, conversation_signals) else 0.0

        priority = min(
            1.0,
            (base_relevance * 0.62) + (domain_bonus * 0.24) + urgent_bonus + recency_bonus + target_bonus + tension_bonus,
        )

        return FocusItem(
            focus_id=self._stable_id("world_signal", domain, signal.get("id", signal.get("title", ""))),
            kind="world_signal",
            domain=domain,
            title=signal.get("title", "Sinal sem titulo"),
            summary=self._truncate(signal.get("content") or signal.get("title") or "Sem detalhes."),
            priority=priority,
            recommended_action=self.DOMAIN_ACTIONS.get(domain, "monitor"),
            source_ids=[signal.get("id")] if signal.get("id") else [],
            confidence=base_relevance,
        )

    def _focus_from_growth_target(
        self,
        target: Dict[str, Any],
        conversation_signals: List[Dict[str, Any]],
    ) -> FocusItem:
        domain = target.get("domain", "growth")
        tension_bonus = 0.10 if self._domain_appears_in_tension(domain, conversation_signals) else 0.0
        priority = min(1.0, 0.58 + self.DOMAIN_BASE_PRIORITIES.get(domain, 0.60) * 0.25 + tension_bonus)

        desired_state = target.get("desired_state") or "evoluir"
        current_state = target.get("current_state") or "estado atual nao descrito"

        return FocusItem(
            focus_id=self._stable_id("growth_target", domain, target.get("id", desired_state)),
            kind="growth_target",
            domain=domain,
            title=f"Avancar em {domain}",
            summary=self._truncate(f"Atual: {current_state}. Desejado: {desired_state}."),
            priority=priority,
            recommended_action="plan",
            source_ids=[target.get("id")] if target.get("id") else [],
            confidence=0.70,
        )

    def _focus_from_conversation_signal(self, signal: Dict[str, Any]) -> FocusItem:
        behavioral = signal.get("behavioral_patterns", {}) or {}
        problems = behavioral.get("problemas_ativos", []) or []
        interests = behavioral.get("interesses", []) or []
        emotional_state = signal.get("emotional_state_inferred", "neutro")
        friction = signal.get("friction_potential", {}) or {}
        friction_level = 0.05 * len(friction) if isinstance(friction, dict) else 0.0

        priority = min(1.0, 0.66 + (0.06 * len(problems)) + friction_level)
        summary_bits = []
        if problems:
            summary_bits.append("Problemas ativos: " + ", ".join(problems[:3]))
        if interests:
            summary_bits.append("Interesses: " + ", ".join(interests[:3]))
        summary_bits.append(f"Estado emocional inferido: {emotional_state}")

        return FocusItem(
            focus_id=self._stable_id("user_tension", "user", signal.get("id", emotional_state)),
            kind="user_tension",
            domain="user",
            title="Tensao ativa do usuario",
            summary=self._truncate(" | ".join(summary_bits)),
            priority=priority,
            recommended_action="follow_up",
            source_ids=[signal.get("id")] if signal.get("id") else [],
            confidence=0.68,
        )

    def _deduplicate_focuses(self, focuses: Iterable[FocusItem]) -> List[FocusItem]:
        best_by_key: Dict[str, FocusItem] = {}
        for focus in focuses:
            key = f"{focus.kind}:{focus.domain}:{focus.title.lower()}"
            current = best_by_key.get(key)
            if current is None or focus.priority > current.priority:
                best_by_key[key] = focus
        return list(best_by_key.values())

    def _make_summary(self, focuses: List[FocusItem]) -> str:
        if not focuses:
            return "Nenhum foco critico emergiu no workspace global."

        lead = focuses[0]
        return (
            f"Foco dominante: {lead.title} ({lead.domain}). "
            f"{len(focuses)} frente(s) relevantes mantidas no espaco de trabalho."
        )

    def _signal_touches_user_tension(self, signal_text: str, conversation_signals: List[Dict[str, Any]]) -> bool:
        for signal in conversation_signals:
            behavioral = signal.get("behavioral_patterns", {}) or {}
            terms = []
            terms.extend(behavioral.get("problemas_ativos", []) or [])
            terms.extend(behavioral.get("interesses", []) or [])
            for term in terms:
                term_lower = str(term).strip().lower()
                if term_lower and term_lower in signal_text:
                    return True
        return False

    def _domain_appears_in_tension(self, domain: str, conversation_signals: List[Dict[str, Any]]) -> bool:
        domain_lower = domain.lower()
        for signal in conversation_signals:
            behavioral = signal.get("behavioral_patterns", {}) or {}
            terms = []
            terms.extend(behavioral.get("problemas_ativos", []) or [])
            terms.extend(behavioral.get("interesses", []) or [])
            if any(domain_lower in str(term).lower() for term in terms):
                return True
        return False

    def _conversation_has_active_tension(self, signal: Dict[str, Any]) -> bool:
        behavioral = signal.get("behavioral_patterns", {}) or {}
        friction = signal.get("friction_potential", {}) or {}
        return bool(behavioral.get("problemas_ativos")) or bool(friction)

    def _recency_bonus(self, created_at_iso: Optional[str]) -> float:
        if not created_at_iso:
            return 0.0

        try:
            created_at = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        except ValueError:
            return 0.0

        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age = now - created_at.astimezone(timezone.utc)
        if age <= timedelta(hours=2):
            return 0.10
        if age <= timedelta(hours=6):
            return 0.06
        if age <= timedelta(hours=24):
            return 0.03
        return 0.0

    def _calculate_signature(self, focuses: List[Dict[str, Any]]) -> str:
        normalized = json.dumps(
            [
                {
                    "focus_id": focus["focus_id"],
                    "priority": round(float(focus["priority"]), 3),
                    "recommended_action": focus["recommended_action"],
                }
                for focus in focuses
            ],
            sort_keys=True,
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _stable_id(self, kind: str, domain: str, raw: str) -> str:
        payload = f"{kind}:{domain}:{raw}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _truncate(self, text: str, limit: int = 180) -> str:
        clean = " ".join(text.split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 3] + "..."