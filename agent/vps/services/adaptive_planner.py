import hashlib
import inspect
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from intelligence.strategic_planner import StrategicPlanner

logger = logging.getLogger(__name__)


class AdaptivePlannerService:
    """
    Planejador adaptativo para transformar focos do workspace em agenda operacional.

    Ele nao executa ferramentas ainda. Seu papel e:
    - escolher o modo cognitivo atual;
    - priorizar frentes imediatas;
    - registrar um brief de execucao reaproveitavel;
    - anotar os episodios ativos com metadados taticos.
    """

    GROWTH_DOMAINS = {"finance", "crypto", "macro", "innovation", "growth", "corporate"}

    ACTION_EXECUTORS = {
        "alert": "survival_guard",
        "research": "market_analyst",
        "follow_up": "relationship_manager",
        "plan": "strategy_planner",
        "monitor": "signal_monitor",
    }

    def __init__(
        self,
        bank,
        chat_manager,
        episodic_memory,
        strategic_planner: Optional[StrategicPlanner] = None,
        max_actions: int = 4,
    ):
        self.bank = bank
        self.chat_manager = chat_manager
        self.episodic_memory = episodic_memory
        self.strategic_planner = strategic_planner or StrategicPlanner()
        self.max_actions = max_actions
        self._last_signature: Optional[str] = None
        self._plan_consumers: List[Callable[[Dict[str, Any]], Any]] = []
        self.current_plan: Optional[Dict[str, Any]] = None

    async def synchronize_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.build_plan(snapshot)
        self._apply_plan_metadata(plan)

        if plan["signature"] == self._last_signature:
            self.current_plan = plan
            return plan

        self.persist_plan(plan)
        self.publish_plan(plan)
        await self.notify_plan_consumers(plan)
        self._last_signature = plan["signature"]
        self.current_plan = plan
        return plan

    async def handle_execution_feedback(self, feedback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        focus_id = feedback.get("focus_id")
        episode = self.episodic_memory.active_episodes.get(focus_id)
        if not episode:
            return None

        replan_hint = self._build_replan_hint(episode, feedback)
        follow_up_action = self._build_follow_up_action(episode, feedback, replan_hint)
        strategic_review = self._build_strategy_review(episode, feedback, replan_hint, follow_up_action)
        learning_state = self._build_learning_state(episode, feedback, strategic_review)
        timestamp = datetime.now(timezone.utc).isoformat()

        episode["feedback_ready"] = True
        episode["feedback_status"] = feedback.get("status")
        episode["last_feedback_summary"] = feedback.get("summary")
        episode["feedback_quality_score"] = feedback.get("quality_score")
        episode["feedback_confidence_band"] = self._quality_band(feedback.get("quality_score"))
        episode["replan_hint"] = replan_hint
        episode["follow_up_action"] = follow_up_action
        episode["strategic_review"] = strategic_review
        episode["strategy_verdict"] = strategic_review["verdict"]
        episode["strategy_posture"] = strategic_review["posture"]
        episode["learning_signal"] = strategic_review["learning_signal"]
        episode["priority_adjustment"] = strategic_review["priority_delta"]
        episode["priority_policy"] = strategic_review["priority_policy"]
        episode["learning_state"] = learning_state
        episode["learning_pattern"] = learning_state["dominant_pattern"]
        episode["planner_updated_at"] = timestamp
        episode["planning_horizon"] = follow_up_action["horizon"]
        episode["tactical_instruction"] = follow_up_action["instruction"]
        episode["follow_up_ready_at"] = timestamp
        episode["strategy_reviewed_at"] = timestamp

        payload = {
            "focus_id": focus_id,
            "title": episode.get("title"),
            "status": feedback.get("status"),
            "summary": feedback.get("summary"),
            "quality_score": feedback.get("quality_score"),
            "confidence_band": self._quality_band(feedback.get("quality_score")),
            "replan_hint": replan_hint,
            "mode": self.current_plan.get("mode") if self.current_plan else None,
            "follow_up_action": follow_up_action,
            "strategic_review": strategic_review,
            "learning_state": learning_state,
        }

        try:
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_replan_request",
                    "description": replan_hint,
                    "context": payload,
                }
            )
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_strategy_review",
                    "description": strategic_review["summary"],
                    "context": strategic_review,
                }
            )
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_learning_update",
                    "description": learning_state["summary"],
                    "context": learning_state,
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir revisao adaptativa: {exc}")

        self.chat_manager.push_insight(
            f"Replanejamento armado para '{episode.get('title', focus_id)}': {replan_hint}"
        )
        return payload

    def register_plan_consumer(self, consumer: Callable[[Dict[str, Any]], Any]) -> None:
        if consumer not in self._plan_consumers:
            self._plan_consumers.append(consumer)

    async def notify_plan_consumers(self, plan: Dict[str, Any]) -> None:
        for consumer in self._plan_consumers:
            try:
                result = consumer(plan)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.error(f"Erro ao notificar consumidor de plano: {exc}")

    def build_plan(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        focuses = self._prepare_focuses(snapshot)
        mode = self._select_mode(focuses)
        objective = self._build_objective(focuses, mode)
        agenda = self._build_agenda(focuses, mode)
        strategic_tracks = self._build_strategic_tracks(objective)
        learning_registry = self._build_learning_registry(agenda)
        agenda = self._apply_learning_registry(agenda, learning_registry)
        budget = self._build_budget(mode, agenda, learning_registry)
        self_model = self._build_self_model(mode, focuses, agenda, budget, learning_registry)
        agenda = self._apply_policy_layer(agenda, self_model)
        policy = self._build_policy_snapshot(agenda, self_model)

        immediate_actions = [item for item in agenda if item["horizon"] == "now"]
        next_actions = [item for item in agenda if item["horizon"] == "next"]
        watchlist = [item for item in agenda if item["horizon"] == "watch"]
        dominant = focuses[0] if focuses else None

        plan = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workspace_signature": snapshot.get("signature"),
            "mode": mode,
            "objective": objective,
            "dominant_focus": dominant,
            "agenda": agenda,
            "immediate_actions": immediate_actions,
            "next_actions": next_actions,
            "watchlist": watchlist,
            "strategic_tracks": strategic_tracks,
            "budget": budget,
            "learning_registry": learning_registry,
            "self_model": self_model,
            "policy": policy,
            "summary": self._make_summary(mode, dominant, immediate_actions, len(focuses)),
        }
        plan["signature"] = self._calculate_signature(plan)
        return plan

    def persist_plan(self, plan: Dict[str, Any]) -> None:
        try:
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_execution_plan",
                    "description": plan["summary"],
                    "context": {
                        "mode": plan["mode"],
                        "objective": plan["objective"],
                        "signature": plan["signature"],
                        "workspace_signature": plan["workspace_signature"],
                        "immediate_actions": plan["immediate_actions"],
                        "next_actions": plan["next_actions"],
                        "watchlist": plan["watchlist"],
                        "strategic_tracks": plan["strategic_tracks"],
                        "budget": plan["budget"],
                        "learning_registry": plan["learning_registry"],
                        "self_model": plan["self_model"],
                        "policy": plan["policy"],
                    },
                }
            )
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_policy_snapshot",
                    "description": plan["policy"]["summary"],
                    "context": plan["policy"],
                }
            )
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_self_model_snapshot",
                    "description": plan["self_model"]["summary"],
                    "context": plan["self_model"],
                }
            )
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_learning_registry_snapshot",
                    "description": plan["learning_registry"]["summary"],
                    "context": plan["learning_registry"],
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir plano adaptativo: {exc}")

    def publish_plan(self, plan: Dict[str, Any]) -> None:
        if not plan["agenda"]:
            return

        lines = [
            "**Plano Adaptativo Atualizado**",
            "",
            f"Modo: {plan['mode']}",
            f"Objetivo: {plan['objective']}",
            f"Postura: {plan['self_model']['autonomy_posture']}",
            f"Politica: {plan['policy']['summary']}",
            f"Aprendizado: {plan['learning_registry']['summary']}",
            "",
            f"Orcamento: {plan['budget']['summary']}",
            "",
            "Acoes imediatas:",
        ]

        for idx, action in enumerate(plan["immediate_actions"][:3], start=1):
            lines.append(
                f"{idx}. [{action['domain']}] {action['title']} -> {action['executor_id']} ({action['horizon']})"
            )

        if plan["next_actions"]:
            lines.append("")
            lines.append("Proximo lote:")
            for action in plan["next_actions"][:2]:
                lines.append(f"- {action['title']} ({action['executor_id']})")

        self.chat_manager.push_insight("\n".join(lines))

    def _apply_plan_metadata(self, plan: Dict[str, Any]) -> None:
        planned_at = plan["timestamp"]
        by_focus_id = {item["focus_id"]: item for item in plan["agenda"]}

        for focus_id, episode in list(self.episodic_memory.active_episodes.items()):
            action = by_focus_id.get(focus_id)
            if not action:
                continue

            episode["planner_mode"] = plan["mode"]
            episode["planning_horizon"] = action["horizon"]
            episode["execution_rank"] = action["rank"]
            episode["executor_id"] = action["executor_id"]
            episode["tactical_instruction"] = action["instruction"]
            episode["planner_updated_at"] = planned_at
            if action.get("executor_policy"):
                episode["executor_policy"] = action["executor_policy"]
            if action.get("executor_rerouted_from"):
                episode["executor_rerouted_from"] = action["executor_rerouted_from"]
            if action.get("kind") == "feedback_follow_up":
                episode["planned_follow_up_action"] = action
                episode["follow_up_promoted_at"] = planned_at

    def _prepare_focuses(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        by_focus_id: Dict[str, Dict[str, Any]] = {}

        for focus in snapshot.get("focuses", []):
            shaped_focus = self._apply_priority_shaping(dict(focus))
            by_focus_id[shaped_focus["focus_id"]] = shaped_focus

        for follow_up_action in self._collect_pending_follow_ups():
            existing = by_focus_id.get(follow_up_action["focus_id"])
            promoted = self._promote_follow_up_focus(follow_up_action, existing)
            promoted = self._apply_priority_shaping(promoted)
            by_focus_id[promoted["focus_id"]] = promoted

        focuses = list(by_focus_id.values())
        focuses.sort(key=lambda item: float(item.get("priority", 0.0)), reverse=True)
        return focuses[: self.max_actions]

    def _collect_pending_follow_ups(self) -> List[Dict[str, Any]]:
        pending: List[Dict[str, Any]] = []
        for episode in self.episodic_memory.active_episodes.values():
            action = episode.get("pending_follow_up_action")
            if not isinstance(action, dict):
                continue
            if action.get("dispatch_immediately"):
                continue
            pending.append(dict(action))
        return pending

    def _apply_priority_shaping(self, focus: Dict[str, Any]) -> Dict[str, Any]:
        focus = dict(focus)
        episode = self.episodic_memory.active_episodes.get(focus.get("focus_id"))
        if not episode:
            return focus

        strategic_review = episode.get("strategic_review")
        if not isinstance(strategic_review, dict):
            return focus

        base_priority = float(focus.get("priority", 0.0))
        delta = float(strategic_review.get("priority_delta") or 0.0)
        verdict = strategic_review.get("verdict")
        learning_state = episode.get("learning_state") or {}
        learning_pattern = learning_state.get("dominant_pattern")
        learning_delta = 0.0

        if learning_pattern == "execution_productive":
            learning_delta = 0.03
        elif learning_pattern == "evidence_weak":
            learning_delta = -0.02 if focus.get("kind") == "feedback_follow_up" else -0.05
        elif learning_pattern == "scope_fragile":
            learning_delta = 0.01 if focus.get("kind") == "feedback_follow_up" else -0.03

        if focus.get("kind") == "feedback_follow_up":
            if verdict == "blocked_execution":
                delta = max(delta, 0.04)
            elif verdict == "insufficient_evidence":
                delta = max(delta, -0.01)

        total_delta = delta + learning_delta
        shaped_priority = min(1.0, max(0.0, base_priority + total_delta))
        focus["priority_before"] = round(base_priority, 3)
        focus["priority"] = round(shaped_priority, 3)
        focus["priority_adjustment"] = round(total_delta, 3)
        focus["priority_policy"] = strategic_review.get("priority_policy")
        focus["strategy_verdict"] = verdict
        focus["confidence_band"] = strategic_review.get("confidence_band")
        focus["learning_pattern"] = learning_pattern
        focus["learning_priority_adjustment"] = round(learning_delta, 3)
        return focus

    def _promote_follow_up_focus(
        self,
        action: Dict[str, Any],
        existing_focus: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        existing_focus = existing_focus or {}
        existing_priority = float(existing_focus.get("priority_before", existing_focus.get("priority", 0.0)))
        action_priority = float(action.get("priority", 0.75))
        priority = min(1.0, max(action_priority, existing_priority + 0.04))
        source_ids = list(existing_focus.get("source_ids", []) or [])
        if action.get("action_id"):
            source_ids.append(action["action_id"])

        deduped_sources = []
        for source_id in source_ids:
            if source_id and source_id not in deduped_sources:
                deduped_sources.append(source_id)

        summary = action.get("instruction") or action.get("summary") or existing_focus.get("summary") or "Follow-up pendente."
        return {
            "focus_id": action["focus_id"],
            "kind": action.get("kind", "feedback_follow_up"),
            "domain": action.get("domain") or existing_focus.get("domain", "unknown"),
            "title": action.get("title") or existing_focus.get("title") or action["focus_id"],
            "summary": summary,
            "priority": round(priority, 3),
            "recommended_action": action.get("recommended_action", existing_focus.get("recommended_action", "plan")),
            "source_ids": deduped_sources,
            "confidence": 0.92,
            "action_id": action.get("action_id"),
            "executor_id": action.get("executor_id"),
            "desired_horizon": action.get("horizon", "now"),
            "preserved_instruction": action.get("instruction"),
            "preserved_rationale": action.get("rationale"),
            "source": action.get("source", "adaptive_feedback"),
        }

    def _build_agenda(self, focuses: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        agenda = []
        for index, focus in enumerate(focuses, start=1):
            horizon = focus.get("desired_horizon") or self._choose_horizon(index, focus, mode)
            executor_id = focus.get("executor_id") or self._resolve_executor(focus)
            budget_profile = self._build_budget_profile(focus, horizon)
            enriched_focus = {**focus, **budget_profile}
            action = {
                "step_id": focus.get("action_id") or self._stable_id("step", focus["focus_id"]),
                "focus_id": focus["focus_id"],
                "title": focus["title"],
                "domain": focus["domain"],
                "kind": focus["kind"],
                "summary": focus["summary"],
                "recommended_action": focus["recommended_action"],
                "priority": round(float(focus["priority"]), 3),
                "rank": index,
                "horizon": horizon,
                "executor_id": executor_id,
                "instruction": focus.get("preserved_instruction") or self._build_instruction(focus, mode, horizon),
                "rationale": focus.get("preserved_rationale") or self._build_rationale(enriched_focus, mode, horizon, index),
                **budget_profile,
            }
            if focus.get("source"):
                action["source"] = focus["source"]
            if focus.get("action_id"):
                action["action_id"] = focus["action_id"]
            if "priority_adjustment" in focus:
                action["priority_adjustment"] = focus["priority_adjustment"]
            if focus.get("priority_policy"):
                action["priority_policy"] = focus["priority_policy"]
            if focus.get("strategy_verdict"):
                action["strategy_verdict"] = focus["strategy_verdict"]
            if focus.get("confidence_band"):
                action["confidence_band"] = focus["confidence_band"]
            if focus.get("learning_pattern"):
                action["learning_pattern"] = focus["learning_pattern"]
            if "learning_priority_adjustment" in focus:
                action["learning_priority_adjustment"] = focus["learning_priority_adjustment"]
            agenda.append(action)
        return agenda

    def _build_budget_profile(self, focus: Dict[str, Any], horizon: str) -> Dict[str, Any]:
        verdict = focus.get("strategy_verdict")
        recommended_action = focus.get("recommended_action")

        if verdict == "actionable_defense":
            return {
                "budget_tier": "priority",
                "tool_budget_weight": 1.0,
                "attention_allocation": 3,
                "tool_budget_eligible": True,
            }
        if verdict == "actionable_progress":
            return {
                "budget_tier": "focused",
                "tool_budget_weight": 0.8,
                "attention_allocation": 3 if horizon == "now" else 2,
                "tool_budget_eligible": True,
            }
        if verdict == "blocked_execution":
            return {
                "budget_tier": "repair",
                "tool_budget_weight": 0.55,
                "attention_allocation": 2,
                "tool_budget_eligible": horizon == "now" and recommended_action in {"plan", "research", "alert"},
            }
        if verdict == "insufficient_evidence":
            return {
                "budget_tier": "validate",
                "tool_budget_weight": 0.25,
                "attention_allocation": 2,
                "tool_budget_eligible": False,
            }
        if horizon == "watch":
            return {
                "budget_tier": "reserve",
                "tool_budget_weight": 0.1,
                "attention_allocation": 1,
                "tool_budget_eligible": False,
            }
        if recommended_action in {"research", "plan", "alert"}:
            return {
                "budget_tier": "standard",
                "tool_budget_weight": 0.6,
                "attention_allocation": 2,
                "tool_budget_eligible": True,
            }
        return {
            "budget_tier": "light",
            "tool_budget_weight": 0.2,
            "attention_allocation": 1,
            "tool_budget_eligible": False,
        }

    def _build_budget(
        self,
        mode: str,
        agenda: List[Dict[str, Any]],
        learning_registry: Dict[str, Any],
    ) -> Dict[str, Any]:
        immediate_actions = [item for item in agenda if item["horizon"] == "now"]
        eligible_actions = [
            item
            for item in immediate_actions
            if item.get("tool_budget_eligible") and item.get("recommended_action") in {"research", "plan", "alert"}
        ]
        weighted_pressure = round(sum(float(item.get("tool_budget_weight", 0.0)) for item in eligible_actions), 2)
        attention_capacity = sum(int(item.get("attention_allocation", 0)) for item in immediate_actions[:4])
        learning_bias = self._learning_budget_bias(learning_registry)

        if not eligible_actions:
            tool_dispatch_limit = 0
        else:
            base_allowance = 1 if mode in {"defense", "growth", "balance"} else 0
            tool_dispatch_limit = int(round(weighted_pressure + base_allowance + learning_bias))
            tool_dispatch_limit = max(1, min(4, tool_dispatch_limit, len(eligible_actions)))

        if any(item.get("budget_tier") == "priority" for item in immediate_actions):
            budget_posture = "surge"
        elif any(item.get("budget_tier") == "repair" for item in immediate_actions):
            budget_posture = "repair"
        elif any(item.get("budget_tier") == "validate" for item in immediate_actions):
            budget_posture = "validate"
        else:
            budget_posture = "steady"

        learning_pattern = learning_registry.get("global_pattern", "mixed")
        summary = (
            f"{tool_dispatch_limit} slot(s) de ferramenta, postura {budget_posture}, "
            f"atencao {attention_capacity}, aprendizado {learning_pattern}"
        )
        return {
            "tool_dispatch_limit": tool_dispatch_limit,
            "attention_capacity": attention_capacity,
            "research_pressure": weighted_pressure,
            "learning_bias": learning_bias,
            "budget_posture": budget_posture,
            "summary": summary,
        }

    def _build_self_model(
        self,
        mode: str,
        focuses: List[Dict[str, Any]],
        agenda: List[Dict[str, Any]],
        budget: Dict[str, Any],
        learning_registry: Dict[str, Any],
    ) -> Dict[str, Any]:
        focus_count = len(focuses)
        immediate_actions = [item for item in agenda if item["horizon"] == "now"]
        domain_confidence = self._estimate_domain_confidence(agenda, learning_registry)
        resource_pressure = self._estimate_resource_pressure(focus_count, budget)
        autonomy_posture = self._derive_autonomy_posture(mode, agenda, budget, domain_confidence, learning_registry)
        executor_confidence = {
            executor_id: round(float(data.get("quality_score", 0.0)), 3)
            for executor_id, data in (learning_registry.get("executors") or {}).items()
        }
        tool_confidence = {
            tool_name: round(float(data.get("quality_score", 0.0)), 3)
            for tool_name, data in (learning_registry.get("tools") or {}).items()
        }
        summary = (
            f"Postura {autonomy_posture}, {budget['tool_dispatch_limit']} slot(s) de ferramenta, "
            f"{focus_count} foco(s) ativos, pressao {resource_pressure} e aprendizado {learning_registry['global_pattern']}."
        )
        return {
            "mode": mode,
            "open_focus_count": focus_count,
            "immediate_focus_count": len(immediate_actions),
            "tool_capacity": budget["tool_dispatch_limit"],
            "attention_capacity": budget["attention_capacity"],
            "resource_pressure": resource_pressure,
            "autonomy_posture": autonomy_posture,
            "domain_confidence": domain_confidence,
            "executor_confidence": executor_confidence,
            "tool_confidence": tool_confidence,
            "learning_registry_pattern": learning_registry["global_pattern"],
            "limits": {
                "requires_validation_below_score": 0.6,
                "max_auto_tool_dispatches": budget["tool_dispatch_limit"],
                "max_open_focuses": self.max_actions,
            },
            "summary": summary,
        }

    def _estimate_domain_confidence(
        self,
        agenda: List[Dict[str, Any]],
        learning_registry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = {}
        for action in agenda:
            domain = action.get("domain")
            if not domain:
                continue
            confidence = self._confidence_from_action(action)
            grouped.setdefault(domain, []).append(confidence)

        registry_domains = (learning_registry or {}).get("domains") or {}
        confidence_by_domain: Dict[str, float] = {}
        for domain, values in grouped.items():
            blended = sum(values) / len(values)
            registry = registry_domains.get(domain)
            if registry:
                registry_quality = float(registry.get("quality_score", blended))
                pattern = registry.get("pattern")
                if pattern == "execution_productive":
                    blended = (blended * 0.75) + (registry_quality * 0.25) + 0.04
                elif pattern == "evidence_weak":
                    blended = (blended * 0.7) + (registry_quality * 0.3) - 0.08
                elif pattern == "scope_fragile":
                    blended = (blended * 0.72) + (registry_quality * 0.28) - 0.05
                else:
                    blended = (blended * 0.8) + (registry_quality * 0.2)
            confidence_by_domain[domain] = round(min(0.95, max(0.25, blended)), 3)
        return confidence_by_domain

    def _build_learning_registry(self, agenda: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_focus_id = {item["focus_id"]: item for item in agenda}
        domains: Dict[str, Dict[str, Any]] = {}
        executors: Dict[str, Dict[str, Any]] = {}
        tools: Dict[str, Dict[str, Any]] = {}
        pattern_votes: List[str] = []
        observed_focus_ids: List[str] = []

        for focus_id, episode in self.episodic_memory.active_episodes.items():
            action = by_focus_id.get(focus_id, {})
            learning_state = episode.get("learning_state") or {}
            strategic_review = episode.get("strategic_review") or {}
            delivery_learning_state = episode.get("delivery_learning_state") or {}
            if not learning_state and not strategic_review and not delivery_learning_state:
                continue

            domain = episode.get("domain") or action.get("domain")
            executor_id = episode.get("executor_id") or action.get("executor_id")
            pattern = learning_state.get("dominant_pattern") or self._pattern_from_verdict(strategic_review.get("verdict"))
            quality_score = float(
                learning_state.get(
                    "rolling_quality_score",
                    strategic_review.get("quality_score") or self._confidence_from_action(action) or 0.0,
                )
            )
            review_count = int(learning_state.get("review_count", 1 if strategic_review else 0)) or 1
            verdict = strategic_review.get("verdict")

            observed_focus_ids.append(focus_id)
            if pattern:
                pattern_votes.extend([pattern] * max(1, review_count))

            if domain:
                bucket = domains.setdefault(domain, self._new_learning_bucket())
                self._update_learning_bucket(bucket, focus_id, pattern, quality_score, review_count, verdict)
            if executor_id:
                bucket = executors.setdefault(executor_id, self._new_learning_bucket())
                self._update_learning_bucket(bucket, focus_id, pattern, quality_score, review_count, verdict)

            for delivery_tool_name, tool_state in (delivery_learning_state.get("by_tool") or {}).items():
                tool_pattern = tool_state.get("pattern")
                tool_quality = float(tool_state.get("rolling_quality_score", 0.0))
                tool_attempts = int(tool_state.get("attempt_count", 1)) or 1
                tool_status = tool_state.get("last_status")
                if tool_pattern:
                    pattern_votes.extend([tool_pattern] * tool_attempts)
                bucket = tools.setdefault(delivery_tool_name, self._new_learning_bucket())
                self._update_learning_bucket(bucket, focus_id, tool_pattern, tool_quality, tool_attempts, tool_status)

            for delivery_executor_id, executor_state in (delivery_learning_state.get("by_executor") or {}).items():
                executor_pattern = executor_state.get("pattern")
                executor_quality = float(executor_state.get("rolling_quality_score", 0.0))
                executor_attempts = int(executor_state.get("attempt_count", 1)) or 1
                executor_status = executor_state.get("last_status")
                bucket = executors.setdefault(delivery_executor_id, self._new_learning_bucket())
                self._update_learning_bucket(
                    bucket,
                    focus_id,
                    executor_pattern,
                    executor_quality,
                    executor_attempts,
                    executor_status,
                )

        finalized_domains = {
            domain: self._finalize_learning_bucket(domain, bucket)
            for domain, bucket in domains.items()
        }
        finalized_executors = {
            executor_id: self._finalize_learning_bucket(executor_id, bucket)
            for executor_id, bucket in executors.items()
        }
        finalized_tools = {
            tool_name: self._finalize_learning_bucket(tool_name, bucket)
            for tool_name, bucket in tools.items()
        }
        global_pattern = self._dominant_learning_pattern(pattern_votes)
        summary = (
            f"{global_pattern}, {len(finalized_domains)} dominio(s), {len(finalized_executors)} executor(es), "
            f"{len(finalized_tools)} tool(s), {len(observed_focus_ids)} foco(s) com historico"
        )
        return {
            "global_pattern": global_pattern,
            "focus_count": len(observed_focus_ids),
            "domains": finalized_domains,
            "executors": finalized_executors,
            "tools": finalized_tools,
            "summary": summary,
        }

    def _new_learning_bucket(self) -> Dict[str, Any]:
        return {
            "review_count": 0,
            "quality_total": 0.0,
            "pattern_counts": {},
            "verdict_counts": {},
            "focus_ids": [],
        }

    def _update_learning_bucket(
        self,
        bucket: Dict[str, Any],
        focus_id: str,
        pattern: Optional[str],
        quality_score: float,
        review_count: int,
        verdict: Optional[str],
    ) -> None:
        bucket["review_count"] += max(1, review_count)
        bucket["quality_total"] += quality_score * max(1, review_count)
        if focus_id not in bucket["focus_ids"]:
            bucket["focus_ids"].append(focus_id)
        if pattern:
            bucket["pattern_counts"][pattern] = bucket["pattern_counts"].get(pattern, 0) + max(1, review_count)
        if verdict:
            bucket["verdict_counts"][verdict] = bucket["verdict_counts"].get(verdict, 0) + max(1, review_count)

    def _finalize_learning_bucket(self, label: str, bucket: Dict[str, Any]) -> Dict[str, Any]:
        review_count = max(1, int(bucket.get("review_count", 0)))
        pattern = self._dominant_learning_pattern(
            [
                pattern
                for pattern, count in (bucket.get("pattern_counts") or {}).items()
                for _ in range(count)
            ]
        )
        quality_score = round(float(bucket.get("quality_total", 0.0)) / review_count, 3)
        return {
            "label": label,
            "pattern": pattern,
            "review_count": review_count,
            "quality_score": quality_score,
            "focus_ids": list(bucket.get("focus_ids", [])),
            "verdict_counts": dict(bucket.get("verdict_counts", {})),
        }

    def _dominant_learning_pattern(self, patterns: List[str]) -> str:
        if not patterns:
            return "mixed"
        weights = {
            "execution_productive": 0,
            "evidence_weak": 0,
            "scope_fragile": 0,
            "mixed": 0,
        }
        for pattern in patterns:
            weights[pattern] = weights.get(pattern, 0) + 1
        return max(weights, key=weights.get)

    def _pattern_from_verdict(self, verdict: Optional[str]) -> Optional[str]:
        if verdict in {"actionable_progress", "actionable_defense"}:
            return "execution_productive"
        if verdict == "insufficient_evidence":
            return "evidence_weak"
        if verdict == "blocked_execution":
            return "scope_fragile"
        return None

    def _learning_budget_bias(self, learning_registry: Dict[str, Any]) -> float:
        pattern = learning_registry.get("global_pattern")
        if pattern == "execution_productive":
            return 0.6
        if pattern in {"evidence_weak", "scope_fragile"}:
            return -0.6
        return 0.0

    def _apply_learning_registry(
        self,
        agenda: List[Dict[str, Any]],
        learning_registry: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        updated = []
        registry_domains = learning_registry.get("domains") or {}
        registry_executors = learning_registry.get("executors") or {}
        registry_tools = learning_registry.get("tools") or {}

        for action in agenda:
            enriched = dict(action)
            domain_data = registry_domains.get(action.get("domain")) or {}
            executor_data = registry_executors.get(action.get("executor_id")) or {}
            enriched["domain_learning_pattern"] = domain_data.get("pattern")
            enriched["domain_learning_quality"] = domain_data.get("quality_score")
            enriched["executor_learning_pattern"] = executor_data.get("pattern")
            enriched["executor_learning_quality"] = executor_data.get("quality_score")
            tool_name = self._tool_name_for_action(enriched)
            if tool_name:
                tool_data = registry_tools.get(tool_name) or {}
                enriched["tool_name"] = tool_name
                enriched["tool_learning_pattern"] = tool_data.get("pattern")
                enriched["tool_learning_quality"] = tool_data.get("quality_score")
            enriched["tool_budget_weight"] = self._tune_tool_budget_weight(enriched)

            executor_id, executor_policy = self._select_executor_with_learning(enriched)
            if executor_id != enriched["executor_id"]:
                enriched["executor_rerouted_from"] = enriched["executor_id"]
                enriched["executor_id"] = executor_id
            if executor_policy:
                enriched["executor_policy"] = executor_policy
            updated.append(enriched)
        return updated

    def _tune_tool_budget_weight(self, action: Dict[str, Any]) -> float:
        weight = float(action.get("tool_budget_weight", 0.0))
        if not action.get("tool_budget_eligible"):
            return round(weight, 2)

        domain_pattern = action.get("domain_learning_pattern")
        executor_pattern = action.get("executor_learning_pattern")

        if domain_pattern == "execution_productive":
            weight += 0.1
        elif domain_pattern == "evidence_weak":
            weight -= 0.15
        elif domain_pattern == "scope_fragile":
            weight -= 0.1

        if executor_pattern == "execution_productive":
            weight += 0.05
        elif executor_pattern in {"evidence_weak", "scope_fragile"}:
            weight -= 0.1

        tool_pattern = action.get("tool_learning_pattern")
        if tool_pattern == "execution_productive":
            weight += 0.05
        elif tool_pattern == "evidence_weak":
            weight -= 0.08
        elif tool_pattern == "scope_fragile":
            weight -= 0.12

        return round(min(1.0, max(0.1, weight)), 2)

    def _tool_name_for_action(self, action: Dict[str, Any]) -> Optional[str]:
        if action.get("recommended_action") in {"research", "plan", "alert"}:
            return "perplexity_search"
        return None

    def _select_executor_with_learning(self, action: Dict[str, Any]) -> tuple[str, Optional[str]]:
        current_executor = action.get("executor_id") or self.ACTION_EXECUTORS.get(
            action.get("recommended_action"),
            "signal_monitor",
        )
        if action.get("recommended_action") in {"follow_up", "monitor"}:
            return current_executor, None

        executor_pattern = action.get("executor_learning_pattern")
        domain_pattern = action.get("domain_learning_pattern")
        if executor_pattern == "execution_productive":
            return current_executor, "executor produtivo mantido"
        if current_executor != self.ACTION_EXECUTORS["plan"] and (
            executor_pattern in {"evidence_weak", "scope_fragile"} or domain_pattern == "scope_fragile"
        ):
            return self.ACTION_EXECUTORS["plan"], "executor recalibrado por historico fragil"
        return current_executor, None

    def _confidence_from_action(self, action: Dict[str, Any]) -> float:
        band = action.get("confidence_band")
        if band == "high":
            return 0.85
        if band == "medium":
            return 0.6
        if band == "low":
            return 0.35
        return round(min(0.9, max(0.3, float(action.get("priority", 0.5)))), 3)

    def _estimate_resource_pressure(self, focus_count: int, budget: Dict[str, Any]) -> str:
        attention_capacity = int(budget.get("attention_capacity", 0))
        if focus_count >= self.max_actions or attention_capacity >= 8:
            return "high"
        if focus_count >= max(2, self.max_actions - 1) or attention_capacity >= 5:
            return "medium"
        return "low"

    def _derive_autonomy_posture(
        self,
        mode: str,
        agenda: List[Dict[str, Any]],
        budget: Dict[str, Any],
        domain_confidence: Dict[str, float],
        learning_registry: Dict[str, Any],
    ) -> str:
        verdicts = {item.get("strategy_verdict") for item in agenda if item.get("strategy_verdict")}
        high_confidence_domains = [value for value in domain_confidence.values() if value >= 0.75]
        learning_pattern = learning_registry.get("global_pattern")
        fragile_histories = any(
            item.get("executor_learning_pattern") in {"evidence_weak", "scope_fragile"}
            or item.get("domain_learning_pattern") in {"evidence_weak", "scope_fragile"}
            for item in agenda
            if item.get("tool_budget_eligible")
        )

        if mode == "defense" and budget.get("tool_dispatch_limit", 0) >= 1:
            return "protective"
        if learning_pattern in {"evidence_weak", "scope_fragile"} and fragile_histories:
            return "skeptical"
        if "blocked_execution" in verdicts or "insufficient_evidence" in verdicts:
            return "guarded"
        if budget.get("tool_dispatch_limit", 0) >= 2 and high_confidence_domains:
            return "assertive"
        return "measured"

    def _apply_policy_layer(self, agenda: List[Dict[str, Any]], self_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        updated = []
        for action in agenda:
            decision, reason = self._policy_decision(action, self_model)
            enriched = dict(action)
            enriched["policy_decision"] = decision
            enriched["policy_reason"] = reason
            enriched["auto_execute"] = decision == "auto_execute"
            updated.append(enriched)
        return updated

    def _build_policy_snapshot(self, agenda: List[Dict[str, Any]], self_model: Dict[str, Any]) -> Dict[str, Any]:
        counts = {
            "auto_execute": 0,
            "guided_execute": 0,
            "needs_validation": 0,
            "defer": 0,
        }
        for action in agenda:
            decision = action.get("policy_decision")
            if decision in counts:
                counts[decision] += 1

        summary = (
            f"auto {counts['auto_execute']}, guided {counts['guided_execute']}, "
            f"validar {counts['needs_validation']}, defer {counts['defer']}"
        )
        return {
            "autonomy_posture": self_model["autonomy_posture"],
            "counts": counts,
            "summary": summary,
        }

    def _policy_decision(self, action: Dict[str, Any], self_model: Dict[str, Any]) -> tuple[str, str]:
        if action.get("horizon") == "watch":
            return "defer", "frente mantida em observacao"
        if action.get("budget_tier") == "validate" or action.get("strategy_verdict") == "insufficient_evidence":
            return "needs_validation", "evidencia insuficiente para autoexecucao"
        if action.get("strategy_verdict") == "blocked_execution":
            return "guided_execute", "bloqueio pede escopo guiado antes de escalar"
        if self_model.get("autonomy_posture") == "skeptical" and action.get("tool_budget_eligible"):
            if action.get("executor_learning_pattern") == "scope_fragile" or action.get("domain_learning_pattern") == "scope_fragile":
                return "guided_execute", "historico multi-ciclo indica escopo fragil"
            return "needs_validation", "historico multi-ciclo ainda fraco para autoexecucao"
        if self_model.get("autonomy_posture") == "protective" and action.get("strategy_verdict") == "actionable_defense":
            return "auto_execute", "protecao prioritaria autorizada"
        if self_model.get("autonomy_posture") == "assertive" and action.get("tool_budget_eligible"):
            return "auto_execute", "janela favoravel para execucao automatica"
        if action.get("recommended_action") == "follow_up":
            return "guided_execute", "follow-up relacional deve permanecer guiado"
        if action.get("tool_budget_eligible") and action.get("horizon") == "now":
            return "auto_execute", "acao imediata com orcamento e confianca suficientes"
        return "guided_execute", "manter conducao guiada neste ciclo"

    def _select_mode(self, focuses: List[Dict[str, Any]]) -> str:
        if not focuses:
            return "standby"

        if any(focus.get("domain") == "survival" or focus.get("recommended_action") == "alert" for focus in focuses[:2]):
            return "defense"

        dominant = focuses[0]
        if dominant.get("kind") == "user_tension" and float(dominant.get("priority", 0.0)) >= 0.78:
            return "care"

        if any(
            focus.get("domain") in self.GROWTH_DOMAINS and float(focus.get("priority", 0.0)) >= 0.78
            for focus in focuses[:2]
        ):
            return "growth"

        return "balance"

    def _build_objective(self, focuses: List[Dict[str, Any]], mode: str) -> str:
        if not focuses:
            return "Manter vigilancia basal enquanto novos focos nao emergem."

        dominant = focuses[0]
        title = dominant["title"]
        domain = dominant["domain"]

        if mode == "defense":
            return f"Preservar continuidade e reduzir risco em torno de '{title}' no dominio {domain}."
        if mode == "care":
            return f"Destravar a tensao central do usuario a partir de '{title}'."
        if mode == "growth":
            return f"Converter '{title}' em alavanca de crescimento com execucao disciplinada."
        if mode == "standby":
            return "Manter o sistema pronto para agir ao menor sinal material."
        return f"Equilibrar estabilidade e progresso enquanto acompanhamos '{title}'."

    def _build_strategic_tracks(self, objective: str) -> List[str]:
        try:
            tasks = self.strategic_planner.create_plan(objective)
        except Exception as exc:
            logger.error(f"Erro ao gerar trilhas estrategicas: {exc}")
            return []

        tracks = []
        for task in tasks[:3]:
            name = task.get("tarefa") or task.get("task") or task.get("nome")
            if name:
                tracks.append(name)
        return tracks

    def _choose_horizon(self, index: int, focus: Dict[str, Any], mode: str) -> str:
        priority = float(focus.get("priority", 0.0))
        if mode == "defense" and (focus.get("domain") == "survival" or focus.get("recommended_action") == "alert"):
            return "now"
        if index == 1:
            return "now"
        if index == 2 and priority >= 0.78:
            return "now"
        if index <= 3:
            return "next"
        return "watch"

    def _resolve_executor(self, focus: Dict[str, Any]) -> str:
        return self.ACTION_EXECUTORS.get(focus.get("recommended_action"), "signal_monitor")

    def _build_instruction(self, focus: Dict[str, Any], mode: str, horizon: str) -> str:
        time_box = {
            "now": "agir neste ciclo",
            "next": "preparar no proximo lote",
            "watch": "observar sem interromper outras frentes",
        }[horizon]
        return (
            f"Modo {mode}: {time_box} sobre '{focus['title']}' no dominio {focus['domain']}. "
            f"Acao sugerida: {focus['recommended_action']}. Resumo: {focus['summary']}"
        )

    def _build_rationale(self, focus: Dict[str, Any], mode: str, horizon: str, rank: int) -> str:
        reasons = [f"rank {rank}", f"modo {mode}", f"prioridade {float(focus['priority']):.2f}"]
        if focus.get("domain") == "survival":
            reasons.append("dominio de preservacao")
        if focus.get("kind") == "user_tension":
            reasons.append("tensao humana ativa")
        if horizon == "watch":
            reasons.append("mantido em observacao")
        if focus.get("kind") == "feedback_follow_up":
            reasons.append("feedback operacional pendente")
        if focus.get("budget_tier"):
            reasons.append(f"orcamento {focus['budget_tier']}")
        if focus.get("learning_pattern") and focus.get("learning_pattern") != "mixed":
            reasons.append(f"aprendizado {focus['learning_pattern']}")
        adjustment = float(focus.get("priority_adjustment") or 0.0)
        if abs(adjustment) >= 0.01:
            reasons.append(f"ajuste {adjustment:+.2f}")
        if focus.get("priority_policy"):
            reasons.append(f"politica {focus['priority_policy']}")
        return ", ".join(reasons)

    def _build_replan_hint(self, episode: Dict[str, Any], feedback: Dict[str, Any]) -> str:
        summary = (feedback.get("summary") or "").lower()
        quality_score = float(feedback.get("quality_score") or 0.0)
        if feedback.get("status") != "success":
            return "Reabrir investigacao com pergunta mais estreita, checar bloqueios e elevar a prioridade operacional."
        if quality_score < 0.6:
            return "Validar o retorno com uma pergunta mais especifica, checar lacunas e evitar decisao prematura."
        if episode.get("planner_mode") == "defense" or "risco" in summary or "mitig" in summary:
            return "Extrair 3 mitigacoes concretas, escolher a primeira acao defensiva e validar sinais de piora."
        if episode.get("recommended_action") == "plan":
            return "Converter o retorno em checklist executavel, com sequencia, risco e gatilhos de confirmacao."
        return "Destilar implicacoes praticas, definir o proximo experimento e manter monitoramento focal."

    def _build_follow_up_action(
        self,
        episode: Dict[str, Any],
        feedback: Dict[str, Any],
        replan_hint: str,
    ) -> Dict[str, Any]:
        focus_id = episode["focus_id"]
        status = feedback.get("status")
        mode = episode.get("planner_mode") or (self.current_plan or {}).get("mode") or "balance"
        quality_score = float(feedback.get("quality_score") or 0.0)
        priority = round(float(episode.get("priority", 0.75)), 3)
        title = episode.get("title", focus_id)
        summary = feedback.get("summary") or "Sem resumo operacional."
        base_action = {
            "action_id": self._stable_id("feedback_follow_up", focus_id),
            "focus_id": focus_id,
            "domain": episode.get("domain", "unknown"),
            "kind": "feedback_follow_up",
            "priority": priority,
            "rank": int(episode.get("execution_rank") or 1),
            "summary": summary,
            "source": "adaptive_feedback",
        }

        if status == "success" and quality_score >= 0.6:
            return {
                **base_action,
                "title": f"Consolidar retorno de {title}",
                "recommended_action": "follow_up",
                "executor_id": self.ACTION_EXECUTORS["follow_up"],
                "horizon": "now",
                "instruction": (
                    f"Usar o retorno de '{title}' para {replan_hint.lower()} "
                    "Sintetize o que muda agora, o proximo passo pratico e o sinal de confirmacao."
                ),
                "rationale": f"feedback success, qualidade {quality_score:.2f}, consolidacao imediata",
                "dispatch_immediately": True,
            }

        if status == "success":
            return {
                **base_action,
                "title": f"Validar retorno de {title}",
                "recommended_action": "plan",
                "executor_id": self.ACTION_EXECUTORS["plan"],
                "horizon": "now",
                "instruction": (
                    f"Resultado parcial para '{title}'. {replan_hint} "
                    "Estruture a proxima pergunta, defina criterios de suficiencia e evite acao prematura."
                ),
                "rationale": f"feedback success, qualidade {quality_score:.2f}, precisa validacao",
                "dispatch_immediately": False,
            }

        retry_action = "plan" if episode.get("recommended_action") != "plan" else "research"
        return {
            **base_action,
            "title": f"Replanejar {title}",
            "recommended_action": retry_action,
            "executor_id": self.ACTION_EXECUTORS[retry_action],
            "horizon": "now",
            "instruction": (
                f"Replanejar '{title}' apos falha de execucao. {replan_hint} "
                "Antes do proximo despacho, estreite a pergunta, revise premissas e confirme o bloqueio dominante."
            ),
            "rationale": f"feedback {status}, modo {mode}, precisa nova estrategia",
            "dispatch_immediately": False,
        }

    def _build_strategy_review(
        self,
        episode: Dict[str, Any],
        feedback: Dict[str, Any],
        replan_hint: str,
        follow_up_action: Dict[str, Any],
    ) -> Dict[str, Any]:
        focus_id = episode["focus_id"]
        quality_score = float(feedback.get("quality_score") or 0.0)
        confidence_band = self._quality_band(quality_score)
        mode = episode.get("planner_mode") or (self.current_plan or {}).get("mode") or "balance"
        status = feedback.get("status")
        title = episode.get("title", focus_id)

        if status != "success":
            verdict = "blocked_execution"
            posture = "tighten_scope"
            learning_signal = "execution_failure_or_scope_issue"
            summary = (
                f"Retorno falhou para '{title}'. Apertar escopo, revisar premissas e reduzir ambiguidade antes do proximo despacho."
            )
        elif quality_score < 0.6:
            verdict = "insufficient_evidence"
            posture = "validate_before_commit"
            learning_signal = "evidence_shallow_or_ambiguous"
            summary = (
                f"Retorno ainda fraco para '{title}'. Validar lacunas e elevar a qualidade da evidencia antes de agir."
            )
        elif mode == "defense":
            verdict = "actionable_defense"
            posture = "mitigate_and_confirm"
            learning_signal = "actionable_risk_signal_confirmed"
            summary = (
                f"Retorno forte em modo defense para '{title}'. Mitigar agora e confirmar sinais de piora."
            )
        else:
            verdict = "actionable_progress"
            posture = "consolidate_and_move"
            learning_signal = "actionable_signal_confirmed"
            summary = (
                f"Retorno forte para '{title}'. Consolidar aprendizado e converter em proximo passo pratico."
            )

        priority_delta, priority_policy = self._priority_profile(verdict)

        review_basis = f"status={status}, score={quality_score:.2f}, band={confidence_band}, mode={mode}"
        review_seed = f"{focus_id}:{feedback.get('plan_signature')}:{verdict}:{confidence_band}"
        review_id = hashlib.sha1(review_seed.encode("utf-8")).hexdigest()[:20]

        return {
            "review_id": review_id,
            "focus_id": focus_id,
            "title": title,
            "mode": mode,
            "status": status,
            "quality_score": quality_score,
            "confidence_band": confidence_band,
            "verdict": verdict,
            "posture": posture,
            "learning_signal": learning_signal,
            "priority_delta": priority_delta,
            "priority_policy": priority_policy,
            "recommended_action": follow_up_action.get("recommended_action"),
            "dispatch_immediately": bool(follow_up_action.get("dispatch_immediately")),
            "review_basis": review_basis,
            "replan_hint": replan_hint,
            "summary": summary,
        }

    def _build_learning_state(
        self,
        episode: Dict[str, Any],
        feedback: Dict[str, Any],
        strategic_review: Dict[str, Any],
    ) -> Dict[str, Any]:
        previous = episode.get("learning_state") or {}
        previous_reviews = int(previous.get("review_count", 0))
        review_count = previous_reviews + 1
        quality_score = float(feedback.get("quality_score") or 0.0)
        verdict = strategic_review["verdict"]

        actionable_count = int(previous.get("actionable_count", 0)) + (1 if verdict in {"actionable_progress", "actionable_defense"} else 0)
        blocked_count = int(previous.get("blocked_count", 0)) + (1 if verdict == "blocked_execution" else 0)
        insufficient_count = int(previous.get("insufficient_count", 0)) + (1 if verdict == "insufficient_evidence" else 0)
        rolling_quality_score = round(
            ((float(previous.get("rolling_quality_score", 0.0)) * previous_reviews) + quality_score) / review_count,
            3,
        )
        previous_average = float(previous.get("rolling_quality_score", 0.0))
        if previous_reviews == 0:
            confidence_trend = "initial"
        elif quality_score > previous_average + 0.1:
            confidence_trend = "improving"
        elif quality_score < previous_average - 0.1:
            confidence_trend = "falling"
        else:
            confidence_trend = "stable"

        recent_verdicts = list(previous.get("recent_verdicts", []))[-2:] + [verdict]
        dominant_pattern = self._derive_learning_pattern(
            actionable_count,
            blocked_count,
            insufficient_count,
            recent_verdicts,
        )
        summary = (
            f"Aprendizado em '{episode.get('title', episode['focus_id'])}': padrao {dominant_pattern}, "
            f"qualidade media {rolling_quality_score:.2f}, revisoes {review_count}."
        )
        return {
            "focus_id": episode["focus_id"],
            "title": episode.get("title", episode["focus_id"]),
            "review_count": review_count,
            "actionable_count": actionable_count,
            "blocked_count": blocked_count,
            "insufficient_count": insufficient_count,
            "rolling_quality_score": rolling_quality_score,
            "confidence_trend": confidence_trend,
            "dominant_pattern": dominant_pattern,
            "recent_verdicts": recent_verdicts,
            "summary": summary,
        }

    def _derive_learning_pattern(
        self,
        actionable_count: int,
        blocked_count: int,
        insufficient_count: int,
        recent_verdicts: List[str],
    ) -> str:
        if actionable_count >= 2 and actionable_count >= blocked_count + insufficient_count:
            return "execution_productive"
        if insufficient_count >= 2 and insufficient_count >= actionable_count:
            return "evidence_weak"
        if blocked_count >= 2 and blocked_count >= actionable_count:
            return "scope_fragile"
        if len(recent_verdicts) >= 2 and recent_verdicts[-1] == recent_verdicts[-2] == "insufficient_evidence":
            return "evidence_weak"
        if len(recent_verdicts) >= 2 and recent_verdicts[-1] == recent_verdicts[-2] == "blocked_execution":
            return "scope_fragile"
        if len(recent_verdicts) >= 2 and all(verdict in {"actionable_progress", "actionable_defense"} for verdict in recent_verdicts[-2:]):
            return "execution_productive"
        return "mixed"

    def _priority_profile(self, verdict: str) -> tuple[float, str]:
        if verdict == "actionable_defense":
            return 0.14, "accelerate"
        if verdict == "actionable_progress":
            return 0.07, "advance"
        if verdict == "blocked_execution":
            return 0.02, "scope_repair"
        if verdict == "insufficient_evidence":
            return -0.08, "validate"
        return 0.0, "steady"

    def _quality_band(self, quality_score: Optional[float]) -> str:
        score = float(quality_score or 0.0)
        if score >= 0.75:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    def _make_summary(
        self,
        mode: str,
        dominant: Optional[Dict[str, Any]],
        immediate_actions: List[Dict[str, Any]],
        focus_count: int,
    ) -> str:
        if not dominant:
            return "Planner adaptativo em standby, sem focos materiais ativos."

        return (
            f"Modo {mode}. Foco dominante: {dominant['title']} ({dominant['domain']}). "
            f"{len(immediate_actions)} acoes imediatas para {focus_count} foco(s) ativos."
        )

    def _calculate_signature(self, plan: Dict[str, Any]) -> str:
        normalized = json.dumps(
            {
                "mode": plan["mode"],
                "objective": plan["objective"],
                "agenda": [
                    {
                        "focus_id": action["focus_id"],
                        "horizon": action["horizon"],
                        "executor_id": action["executor_id"],
                        "recommended_action": action["recommended_action"],
                        "priority": action["priority"],
                        "budget_tier": action.get("budget_tier"),
                        "tool_budget_eligible": action.get("tool_budget_eligible"),
                        "confidence_band": action.get("confidence_band"),
                        "policy_decision": action.get("policy_decision"),
                    }
                    for action in plan["agenda"]
                ],
            },
            sort_keys=True,
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _stable_id(self, prefix: str, focus_id: str) -> str:
        payload = f"{prefix}:{focus_id}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]