import inspect
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdaptiveExecutorService:
    """
    Executor adaptativo para transformar a agenda do planner em despachos reais.

    Nesta fase ele usa o canal VPS -> gemeo local para pesquisas profundas,
    processa o retorno das ferramentas e retroalimenta o episodio ativo.
    """

    TOOL_BACKED_ACTIONS = {"research", "alert", "plan"}

    def __init__(
        self,
        bank,
        chat_manager,
        episodic_memory,
        dispatcher: Optional[Any] = None,
        max_tool_dispatches: int = 2,
        replan_callback: Optional[Any] = None,
    ):
        self.bank = bank
        self.chat_manager = chat_manager
        self.episodic_memory = episodic_memory
        self.max_tool_dispatches = max_tool_dispatches
        self.replan_callback = replan_callback
        self._dispatched_action_keys = set()
        self._pending_tool_dispatches: Dict[str, Dict[str, Any]] = {}
        self.current_cycle: Optional[Dict[str, Any]] = None

        if dispatcher is None:
            from vps.sync_server import manager

            dispatcher = manager
        self.dispatcher = dispatcher

    async def synchronize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        immediate_actions = list(plan.get("immediate_actions", []))
        dispatched: List[Dict[str, Any]] = []
        cycle_budget = plan.get("budget") or {}
        tool_dispatch_limit = int(cycle_budget.get("tool_dispatch_limit", self.max_tool_dispatches))
        tool_dispatch_count = 0

        for action in immediate_actions:
            action_key = self._build_action_key(plan, action)
            if action_key in self._dispatched_action_keys:
                continue

            execution = await self._execute_action(
                plan,
                action,
                tool_budget_available=tool_dispatch_count < tool_dispatch_limit,
            )
            if execution["status"] != "queued":
                self._dispatched_action_keys.add(action_key)
            dispatched.append(execution)

            if execution["dispatch_kind"] == "tool" and execution["status"] == "dispatched":
                tool_dispatch_count += 1

        cycle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plan_signature": plan["signature"],
            "mode": plan["mode"],
            "objective": plan["objective"],
            "budget": cycle_budget,
            "policy": plan.get("policy") or {},
            "dispatched": dispatched,
        }
        self.current_cycle = cycle

        if dispatched:
            self.persist_cycle(cycle)
            self.publish_cycle(cycle)

        return cycle

    async def handle_tool_result(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tool_name = message.get("tool_name")
        status = message.get("status")
        result = message.get("result", {}) or {}
        correlation_key = self._make_tool_correlation(tool_name, result)
        pending = self._pending_tool_dispatches.pop(correlation_key, None)
        if not pending and isinstance(result, dict) and result.get("query"):
            legacy_key = f"{tool_name}:{result['query'].strip().lower()}"
            pending = self._pending_tool_dispatches.pop(legacy_key, None)
        if not pending:
            return None

        focus_id = pending["focus_id"]
        episode = self.episodic_memory.active_episodes.get(focus_id)
        success = status == "success"
        summary = self._summarize_result(tool_name, status, result)
        quality_score = self._score_result_quality(tool_name, status, summary, result)
        timestamp = datetime.now(timezone.utc).isoformat()

        if episode is not None:
            episode["execution_status"] = "completed" if success else "failed"
            episode["last_tool_result"] = result
            episode["last_tool_name"] = tool_name
            episode["last_executor_id"] = pending.get("executor_id")
            episode["result_summary"] = summary
            episode["last_quality_score"] = quality_score
            episode["result_received_at"] = timestamp
            episode["delivery_learning_state"] = self._update_delivery_learning_state(
                episode,
                tool_name,
                pending.get("executor_id"),
                status,
                quality_score,
                timestamp,
            )

            task_id = episode.get("task_id")
            if task_id:
                try:
                    self.bank.update_task_execution(
                        task_id,
                        "completed" if success else "failed",
                        output=summary,
                        success=success,
                    )
                except Exception as exc:
                    logger.error(f"Erro ao atualizar task_execution com resultado: {exc}")

        feedback = {
            "focus_id": focus_id,
            "status": status,
            "tool_name": tool_name,
            "executor_id": pending.get("executor_id"),
            "recommended_action": pending.get("recommended_action"),
            "summary": summary,
            "quality_score": quality_score,
            "result": result,
            "plan_signature": pending["plan_signature"],
            "delivery_learning_state": (episode or {}).get("delivery_learning_state"),
        }

        self.persist_feedback(feedback)
        if tool_name == "whatsapp_send_message":
            self._persist_transparency_audit(pending, result)
        self.chat_manager.push_insight(
            f"Resultado operacional vinculado a '{pending['title']}': {summary}"
        )

        replan_outcome = None
        follow_up_execution = None
        if self.replan_callback is not None:
            try:
                replan_outcome = self.replan_callback(feedback)
                if inspect.isawaitable(replan_outcome):
                    replan_outcome = await replan_outcome
                follow_up_execution = await self._maybe_execute_follow_up(
                    pending,
                    episode,
                    replan_outcome,
                )
            except Exception as exc:
                logger.error(f"Erro ao disparar callback de replanejamento: {exc}")

        feedback["replan_outcome"] = replan_outcome
        if follow_up_execution is not None:
            feedback["follow_up_execution"] = follow_up_execution

        return feedback

    async def _execute_action(
        self,
        plan: Dict[str, Any],
        action: Dict[str, Any],
        tool_budget_available: bool,
    ) -> Dict[str, Any]:
        packet = self._build_execution_packet(plan, action, tool_budget_available)
        episode = self.episodic_memory.active_episodes.get(action["focus_id"])
        timestamp = datetime.now(timezone.utc).isoformat()

        if packet["dispatch_kind"] == "tool":
            correlation_id = self._build_action_key(plan, action)
            packet_arguments = dict(packet.get("arguments") or {})
            packet_arguments.setdefault("correlation_id", correlation_id)
            packet["arguments"] = packet_arguments
            correlation_key = self._make_tool_correlation(packet["tool_name"], packet_arguments)
            self._pending_tool_dispatches[correlation_key] = {
                "focus_id": action["focus_id"],
                "title": action["title"],
                "plan_signature": plan["signature"],
                "tool_name": packet["tool_name"],
                "arguments": packet_arguments,
                "executor_id": action.get("executor_id"),
                "recommended_action": action.get("recommended_action"),
            }
            await self.dispatcher.dispatch_tool(packet["tool_name"], packet_arguments)
            status = "dispatched"
        elif packet["dispatch_kind"] == "chat":
            self.chat_manager.push_insight(packet["brief"])
            status = "briefed"
        else:
            status = "queued"

        if episode is not None:
            episode["execution_status"] = status
            episode["dispatch_kind"] = packet["dispatch_kind"]
            episode["dispatch_tool_name"] = packet.get("tool_name")
            episode["dispatch_arguments"] = packet.get("arguments")
            episode["execution_brief"] = packet["brief"]
            episode["budget_tier"] = action.get("budget_tier")
            episode["tool_budget_eligible"] = action.get("tool_budget_eligible")
            episode["policy_decision"] = action.get("policy_decision")
            if action.get("guardrail_flags"):
                episode["guardrail_flags"] = list(action["guardrail_flags"])
            episode["last_dispatched_at"] = timestamp

            if action.get("kind") == "feedback_follow_up":
                episode["last_planned_follow_up_action"] = dict(action)
                episode["follow_up_plan_signature"] = plan["signature"]
                if status in {"dispatched", "briefed"}:
                    pending = episode.get("pending_follow_up_action")
                    if not isinstance(pending, dict) or pending.get("action_id") == action.get("action_id"):
                        episode["pending_follow_up_action"] = None
                    episode["follow_up_assumed_at"] = timestamp
                else:
                    episode["pending_follow_up_action"] = dict(action)

        execution = {
            "focus_id": action["focus_id"],
            "title": action["title"],
            "dispatch_kind": packet["dispatch_kind"],
            "tool_name": packet.get("tool_name"),
            "status": status,
            "brief": packet["brief"],
            "executor_id": action["executor_id"],
            "recommended_action": action["recommended_action"],
            "kind": action.get("kind"),
            "budget_tier": action.get("budget_tier"),
            "tool_budget_eligible": action.get("tool_budget_eligible"),
            "policy_decision": action.get("policy_decision"),
        }
        if action.get("guardrail_flags"):
            execution["guardrail_flags"] = list(action["guardrail_flags"])
        if action.get("source"):
            execution["source"] = action["source"]
        if action.get("action_id"):
            execution["action_id"] = action["action_id"]
        return execution

    def persist_cycle(self, cycle: Dict[str, Any]) -> None:
        for execution in cycle["dispatched"]:
            try:
                self.bank.insert_system_event(
                    {
                        "event_type": "adaptive_action_dispatch",
                        "description": execution["brief"],
                        "context": {
                            "plan_signature": cycle["plan_signature"],
                            "mode": cycle["mode"],
                            "objective": cycle["objective"],
                            "focus_id": execution["focus_id"],
                            "title": execution["title"],
                            "dispatch_kind": execution["dispatch_kind"],
                            "tool_name": execution.get("tool_name"),
                            "status": execution["status"],
                            "executor_id": execution["executor_id"],
                            "recommended_action": execution["recommended_action"],
                            "budget_tier": execution.get("budget_tier"),
                            "tool_budget_eligible": execution.get("tool_budget_eligible"),
                            "policy_decision": execution.get("policy_decision"),
                            "guardrail_flags": execution.get("guardrail_flags"),
                            "source": execution.get("source"),
                            "action_id": execution.get("action_id"),
                        },
                    }
                )
            except Exception as exc:
                logger.error(f"Erro ao persistir despacho adaptativo: {exc}")

    async def _maybe_execute_follow_up(
        self,
        pending: Dict[str, Any],
        episode: Optional[Dict[str, Any]],
        replan_outcome: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(replan_outcome, dict):
            return None

        follow_up_action = replan_outcome.get("follow_up_action")
        if not isinstance(follow_up_action, dict):
            return None

        if episode is not None:
            episode["last_follow_up_action"] = dict(follow_up_action)
            episode["pending_follow_up_action"] = dict(follow_up_action)

        if not follow_up_action.get("dispatch_immediately"):
            return None

        synthetic_signature = f"{pending['plan_signature']}:feedback"
        follow_up_key = self._build_action_key({"signature": synthetic_signature}, follow_up_action)
        if follow_up_key in self._dispatched_action_keys:
            return None

        synthetic_plan = {
            "signature": synthetic_signature,
            "mode": replan_outcome.get("mode") or (episode or {}).get("planner_mode") or "feedback",
            "objective": replan_outcome.get("replan_hint") or f"Consolidar feedback para {pending['title']}",
        }
        execution = await self._execute_action(synthetic_plan, follow_up_action, tool_budget_available=False)
        if execution["status"] != "queued":
            self._dispatched_action_keys.add(follow_up_key)
        execution["source"] = "adaptive_feedback"
        execution["origin_title"] = pending["title"]

        if episode is not None:
            episode["last_follow_up_execution"] = execution
            episode["follow_up_dispatched_at"] = datetime.now(timezone.utc).isoformat()

        self.persist_follow_up_dispatch(synthetic_plan, follow_up_action, execution, pending)
        return execution

    def persist_follow_up_dispatch(
        self,
        plan: Dict[str, Any],
        action: Dict[str, Any],
        execution: Dict[str, Any],
        pending: Dict[str, Any],
    ) -> None:
        try:
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_follow_up_dispatch",
                    "description": execution["brief"],
                    "context": {
                        "plan_signature": plan["signature"],
                        "mode": plan["mode"],
                        "objective": plan["objective"],
                        "focus_id": action["focus_id"],
                        "origin_title": pending["title"],
                        "follow_up_title": action["title"],
                        "dispatch_kind": execution["dispatch_kind"],
                        "status": execution["status"],
                        "executor_id": execution["executor_id"],
                        "recommended_action": execution["recommended_action"],
                        "source": execution.get("source"),
                        "action_id": execution.get("action_id"),
                    },
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir follow-up adaptativo: {exc}")

    def _persist_transparency_audit(self, pending: Dict[str, Any], result: Dict[str, Any]) -> None:
        if not isinstance(result, dict) or not result.get("guardrail_applied"):
            return
        try:
            self.bank.insert_system_event(
                {
                    "event_type": "whatsapp_transparency_applied",
                    "description": "Identificacao automatica aplicada antes de enviar mensagem.",
                    "context": {
                        "focus_id": pending.get("focus_id"),
                        "plan_signature": pending.get("plan_signature"),
                        "executor_id": pending.get("executor_id"),
                        "contact_name": result.get("contact_name"),
                        "identification_message": result.get("identification_message"),
                        "correlation_id": result.get("correlation_id"),
                    },
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir auditoria de transparencia: {exc}")

    def persist_feedback(self, feedback: Dict[str, Any]) -> None:
        try:
            self.bank.insert_system_event(
                {
                    "event_type": "adaptive_action_result",
                    "description": feedback["summary"],
                    "context": feedback,
                }
            )
        except Exception as exc:
            logger.error(f"Erro ao persistir feedback adaptativo: {exc}")

    def publish_cycle(self, cycle: Dict[str, Any]) -> None:
        lines = [
            "**Executor Adaptativo**",
            "",
            f"Modo: {cycle['mode']}",
            f"Objetivo: {cycle['objective']}",
            f"Orcamento: {(cycle.get('budget') or {}).get('summary', 'padrao')}",
            f"Politica: {(cycle.get('policy') or {}).get('summary', 'nao definida')}",
            "",
            "Despachos deste ciclo:",
        ]

        for execution in cycle["dispatched"][:3]:
            if execution["dispatch_kind"] == "tool":
                lines.append(
                    f"- {execution['title']} -> {execution['tool_name']} ({execution['status']})"
                )
            else:
                lines.append(
                    f"- {execution['title']} -> {execution['dispatch_kind']} ({execution['status']})"
                )

        self.chat_manager.push_insight("\n".join(lines))

    def _build_execution_packet(
        self,
        plan: Dict[str, Any],
        action: Dict[str, Any],
        tool_budget_available: bool,
    ) -> Dict[str, Any]:
        recommended_action = action.get("recommended_action")
        policy_decision = action.get("policy_decision")
        if policy_decision == "defer":
            return {
                "dispatch_kind": "queue",
                "brief": f"Acao '{action['title']}' adiada por politica: {action.get('policy_reason', 'watchlist')}.",
            }

        if policy_decision == "needs_validation":
            return {
                "dispatch_kind": "queue",
                "brief": f"Acao '{action['title']}' requer validacao antes de autoexecucao.",
            }

        if policy_decision == "guided_execute" and (
            recommended_action in self.TOOL_BACKED_ACTIONS or action.get("tool_name")
        ):
            return {
                "dispatch_kind": "chat",
                "brief": f"Acao guiada para '{action['title']}': {action.get('policy_reason', 'conducao assistida neste ciclo')}.",
            }

        custom_tool = action.get("tool_name")
        if custom_tool:
            arguments = action.get("tool_arguments") or action.get("tool_payload") or action.get("arguments") or {}
            if not isinstance(arguments, dict):
                arguments = {"payload": arguments}
            if action.get("tool_budget_eligible") and not tool_budget_available:
                return {
                    "dispatch_kind": "queue",
                    "brief": (
                        f"Acao '{action['title']}' mantida em fila por orcamento {action.get('budget_tier', 'restrito')} "
                        f"no modo {plan['mode']}."
                    ),
                }
            return {
                "dispatch_kind": "tool",
                "tool_name": custom_tool,
                "arguments": arguments,
                "brief": f"Despachando {custom_tool} para '{action['title']}' em modo {plan['mode']}.",
            }

        if recommended_action in self.TOOL_BACKED_ACTIONS and not action.get("tool_budget_eligible", True):
            return {
                "dispatch_kind": "queue",
                "brief": (
                    f"Acao '{action['title']}' mantida em fila por orcamento {action.get('budget_tier', 'restrito')} "
                    f"no modo {plan['mode']}."
                ),
            }

        if recommended_action in self.TOOL_BACKED_ACTIONS and tool_budget_available:
            query = self._build_research_query(plan, action)
            return {
                "dispatch_kind": "tool",
                "tool_name": "perplexity_search",
                "arguments": {"query": query},
                "brief": f"Despachando pesquisa profunda para '{action['title']}' em modo {plan['mode']}.",
            }

        if recommended_action == "follow_up":
            return {
                "dispatch_kind": "chat",
                "brief": (
                    f"Sugestao de follow-up para '{action['title']}': "
                    f"aprofundar a tensao do usuario e confirmar a proxima restricao pratica."
                ),
            }

        return {
            "dispatch_kind": "queue",
            "brief": (
                f"Acao '{action['title']}' mantida em fila tatica no modo {plan['mode']} "
                f"para o executor {action['executor_id']}."
            ),
        }

    def _build_research_query(self, plan: Dict[str, Any], action: Dict[str, Any]) -> str:
        if action["recommended_action"] == "alert":
            return (
                f"Analise o risco e a melhor resposta imediata para: {action['title']}. "
                f"Contexto: {action['summary']}. Modo atual: {plan['mode']}. "
                "Quero implicacoes praticas, mitigacoes e proximos passos nas proximas 24-72h."
            )

        if action["recommended_action"] == "plan":
            return (
                f"Monte um mini playbook estrategico para: {action['title']}. "
                f"Contexto: {action['summary']}. Objetivo atual: {plan['objective']}. "
                "Traga oportunidades, sequencia de execucao, riscos e sinais de confirmacao."
            )

        return (
            f"Pesquise e sintetize o que importa agora sobre: {action['title']}. "
            f"Contexto: {action['summary']}. Objetivo atual: {plan['objective']}. "
            "Traga fundamentos, impacto operacional e pontos de monitoramento."
        )

    def _update_delivery_learning_state(
        self,
        episode: Dict[str, Any],
        tool_name: Optional[str],
        executor_id: Optional[str],
        status: str,
        quality_score: float,
        timestamp: str,
    ) -> Dict[str, Any]:
        previous = episode.get("delivery_learning_state") or {}
        by_tool = dict(previous.get("by_tool") or {})
        by_executor = dict(previous.get("by_executor") or {})

        if tool_name:
            by_tool[tool_name] = self._merge_delivery_signal(by_tool.get(tool_name), status, quality_score, timestamp)
        if executor_id:
            by_executor[executor_id] = self._merge_delivery_signal(by_executor.get(executor_id), status, quality_score, timestamp)

        return {
            "by_tool": by_tool,
            "by_executor": by_executor,
            "last_tool_name": tool_name,
            "last_executor_id": executor_id,
            "last_status": status,
            "last_updated_at": timestamp,
        }

    def _merge_delivery_signal(
        self,
        previous: Optional[Dict[str, Any]],
        status: str,
        quality_score: float,
        timestamp: str,
    ) -> Dict[str, Any]:
        previous = previous or {}
        attempts = int(previous.get("attempt_count", 0)) + 1
        success_count = int(previous.get("success_count", 0)) + (1 if status == "success" else 0)
        failure_count = int(previous.get("failure_count", 0)) + (0 if status == "success" else 1)
        rolling = round(
            ((float(previous.get("rolling_quality_score", 0.0)) * (attempts - 1)) + quality_score) / attempts,
            3,
        )
        pattern = self._delivery_pattern(success_count, failure_count, rolling)
        return {
            "attempt_count": attempts,
            "success_count": success_count,
            "failure_count": failure_count,
            "rolling_quality_score": rolling,
            "last_status": status,
            "last_updated_at": timestamp,
            "pattern": pattern,
        }

    def _delivery_pattern(self, success_count: int, failure_count: int, rolling_quality_score: float) -> str:
        if failure_count >= 2 and failure_count >= success_count:
            return "scope_fragile"
        if rolling_quality_score < 0.45:
            return "evidence_weak"
        if success_count >= 1 and failure_count == 0 and rolling_quality_score >= 0.6:
            return "execution_productive"
        if success_count >= max(1, failure_count) and rolling_quality_score >= 0.6:
            return "execution_productive"
        return "mixed"

    def _score_result_quality(self, tool_name: str, status: str, summary: str, result: Dict[str, Any]) -> float:
        if status != "success":
            return 0.15

        answer = result.get("full_answer") or result.get("answer_preview") or summary or ""
        normalized = " ".join(str(answer).split())
        lower = normalized.lower()
        word_count = len(normalized.split())
        score = 0.35

        if word_count >= 20:
            score += 0.25
        if word_count >= 60:
            score += 0.1
        if any(keyword in lower for keyword in ("mitig", "risco", "confirm", "acao", "proximo", "passo", "estrateg")):
            score += 0.2
        if result.get("sources") or result.get("citations"):
            score += 0.1
        if tool_name != "perplexity_search":
            score -= 0.05

        return round(min(0.95, max(0.0, score)), 3)

    def _build_action_key(self, plan: Dict[str, Any], action: Dict[str, Any]) -> str:
        if action.get("kind") == "feedback_follow_up" and action.get("action_id"):
            return f"feedback_follow_up:{action['action_id']}"
        return f"{plan['signature']}:{action['focus_id']}"

    def _make_tool_correlation(self, tool_name: Optional[str], payload: Any) -> str:
        if isinstance(payload, dict) and payload.get("query"):
            return f"{tool_name}:{payload['query'].strip().lower()}"
        if isinstance(payload, dict) and payload.get("correlation_id"):
            return f"{tool_name}:{payload['correlation_id']}"
        normalized = json.dumps(payload or {}, sort_keys=True, default=str)
        return f"{tool_name}:{normalized}"

    def _summarize_result(self, tool_name: str, status: str, result: Dict[str, Any]) -> str:
        if status != "success":
            return result.get("message") or f"{tool_name} retornou status {status}."
        if tool_name == "perplexity_search":
            answer = result.get("full_answer") or result.get("answer_preview") or "Relatorio sem texto."
            clean = " ".join(str(answer).split())
            return clean[:280] + ("..." if len(clean) > 280 else "")
        return json.dumps(result, ensure_ascii=False)[:280]
