import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.services.adaptive_executor import AdaptiveExecutorService


class FakeBank:
    def __init__(self):
        self.system_events = []

    def insert_system_event(self, event_data):
        self.system_events.append(dict(event_data))
        return f"evt_{len(self.system_events)}"


class FakeChatManager:
    def __init__(self):
        self.insights = []

    def push_insight(self, text: str):
        self.insights.append(text)


class FakeEpisodicMemory:
    def __init__(self, *focus_ids):
        self.active_episodes = {
            focus_id: {
                "focus_id": focus_id,
                "plan_id": f"plan-{focus_id}",
                "task_id": f"task-{focus_id}",
            }
            for focus_id in focus_ids
        }


class FakeDispatcher:
    def __init__(self):
        self.calls = []

    async def dispatch_tool(self, tool_name, arguments):
        self.calls.append((tool_name, dict(arguments)))


def _plan(signature: str, mode: str, objective: str, *actions, budget=None, policy=None):
    return {
        "signature": signature,
        "mode": mode,
        "objective": objective,
        "budget": budget or {},
        "policy": policy or {},
        "immediate_actions": list(actions),
    }


def _action(
    focus_id: str,
    title: str,
    recommended_action: str = "research",
    executor_id: str = "market_analyst",
    domain: str = "finance",
    summary: str = "Resumo sintetico.",
    kind: str = "world_signal",
    action_id: str | None = None,
    source: str | None = None,
    horizon: str = "now",
    budget_tier: str = "standard",
    tool_budget_eligible: bool | None = None,
    policy_decision: str | None = None,
    policy_reason: str | None = None,
):
    if tool_budget_eligible is None:
        tool_budget_eligible = recommended_action in {"research", "plan", "alert"}
    action = {
        "focus_id": focus_id,
        "title": title,
        "recommended_action": recommended_action,
        "executor_id": executor_id,
        "domain": domain,
        "summary": summary,
        "kind": kind,
        "priority": 0.9,
        "rank": 1,
        "horizon": horizon,
        "instruction": f"Instruir sobre {title}",
        "rationale": "teste",
        "budget_tier": budget_tier,
        "tool_budget_weight": 0.6,
        "tool_budget_eligible": tool_budget_eligible,
        "attention_allocation": 2,
    }
    if action_id:
        action["action_id"] = action_id
    if source:
        action["source"] = source
    if policy_decision:
        action["policy_decision"] = policy_decision
    if policy_reason:
        action["policy_reason"] = policy_reason
    return action


@pytest.mark.asyncio
async def test_adaptive_executor_dispatches_tool_and_updates_episode_metadata():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    cycle = await executor.synchronize_plan(
        _plan(
            "plan-1",
            "growth",
            "Converter oportunidade em execucao.",
            _action("focus-1", "Expansao de automacao financeira", recommended_action="plan", executor_id="strategy_planner"),
        )
    )

    assert cycle["dispatched"][0]["dispatch_kind"] == "tool"
    assert dispatcher.calls[0][0] == "perplexity_search"
    assert "Expansao de automacao financeira" in dispatcher.calls[0][1]["query"]
    assert bank.system_events[0]["event_type"] == "adaptive_action_dispatch"
    assert memory.active_episodes["focus-1"]["execution_status"] == "dispatched"
    assert memory.active_episodes["focus-1"]["dispatch_tool_name"] == "perplexity_search"


@pytest.mark.asyncio
async def test_adaptive_executor_avoids_duplicate_dispatch_for_same_plan():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    plan = _plan(
        "plan-1",
        "growth",
        "Converter oportunidade em execucao.",
        _action("focus-1", "Pesquisa de mercado", recommended_action="research"),
    )

    await executor.synchronize_plan(plan)
    await executor.synchronize_plan(plan)

    assert len(dispatcher.calls) == 1
    assert len(bank.system_events) == 1


@pytest.mark.asyncio
async def test_adaptive_executor_briefs_follow_up_without_tool_dispatch():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    cycle = await executor.synchronize_plan(
        _plan(
            "plan-2",
            "care",
            "Destravar a tensao do usuario.",
            _action("focus-1", "Tensao na tomada de decisao", recommended_action="follow_up", executor_id="relationship_manager", domain="user"),
        )
    )

    assert cycle["dispatched"][0]["dispatch_kind"] == "chat"
    assert dispatcher.calls == []
    assert memory.active_episodes["focus-1"]["execution_status"] == "briefed"
    assert any("follow-up" in insight.lower() for insight in chat.insights)


@pytest.mark.asyncio
async def test_adaptive_executor_dispatches_custom_tool_with_correlation():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    action = _action(
        "focus-1",
        "Mensagem para contato",
        recommended_action="message",
        executor_id="relationship_manager",
        domain="communication",
        tool_budget_eligible=False,
    )
    action["tool_name"] = "whatsapp_send_message"
    action["tool_arguments"] = {"contact_name": "Maria", "message": "Oi"}

    cycle = await executor.synchronize_plan(
        _plan(
            "plan-whatsapp",
            "care",
            "Responder contato com transparencia.",
            action,
        )
    )

    execution = cycle["dispatched"][0]
    assert execution["dispatch_kind"] == "tool"
    assert dispatcher.calls[0][0] == "whatsapp_send_message"
    assert dispatcher.calls[0][1]["contact_name"] == "Maria"
    assert dispatcher.calls[0][1]["message"] == "Oi"
    assert "correlation_id" in dispatcher.calls[0][1]


@pytest.mark.asyncio
async def test_adaptive_executor_respects_validate_budget_and_queues_action():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    cycle = await executor.synchronize_plan(
        _plan(
            "plan-validate",
            "growth",
            "Validar retorno antes de nova pesquisa.",
            _action(
                "focus-1",
                "Validar retorno de pesquisa",
                recommended_action="plan",
                executor_id="strategy_planner",
                kind="feedback_follow_up",
                action_id="feedback-validate",
                source="adaptive_feedback",
            ),
            budget={
                "tool_dispatch_limit": 0,
                "budget_posture": "validate",
                "summary": "0 slot(s) de ferramenta, postura validate, atencao 2",
            },
        )
    )

    execution = cycle["dispatched"][0]
    episode = memory.active_episodes["focus-1"]
    assert execution["dispatch_kind"] == "queue"
    assert execution["status"] == "queued"
    assert execution["budget_tier"] == "standard"
    assert dispatcher.calls == []
    assert episode["pending_follow_up_action"]["action_id"] == "feedback-validate"


@pytest.mark.asyncio
async def test_adaptive_executor_guided_policy_briefs_tool_backed_action_without_dispatch():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)
    cycle = await executor.synchronize_plan(
        _plan(
            "plan-guided",
            "growth",
            "Conduzir frente travada com ajuda.",
            _action(
                "focus-1",
                "Reenquadrar pesquisa critica",
                recommended_action="plan",
                executor_id="strategy_planner",
                policy_decision="guided_execute",
                policy_reason="bloqueio pede escopo guiado antes de escalar",
                budget_tier="repair",
            ),
            policy={
                "summary": "auto 0, guided 1, validar 0, defer 0",
            },
        )
    )
    execution = cycle["dispatched"][0]
    episode = memory.active_episodes["focus-1"]
    assert execution["dispatch_kind"] == "chat"
    assert execution["status"] == "briefed"
    assert execution["policy_decision"] == "guided_execute"
    assert dispatcher.calls == []
    assert episode["policy_decision"] == "guided_execute"
    assert "Acao guiada" in chat.insights[0]


@pytest.mark.asyncio
async def test_adaptive_executor_validation_policy_queues_tool_action():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)
    cycle = await executor.synchronize_plan(
        _plan(
            "plan-policy-validate",
            "growth",
            "Validar antes de nova execucao.",
            _action(
                "focus-1",
                "Validar resposta incompleta",
                recommended_action="plan",
                executor_id="strategy_planner",
                kind="feedback_follow_up",
                action_id="feedback-validate-policy",
                source="adaptive_feedback",
                budget_tier="validate",
                policy_decision="needs_validation",
                policy_reason="evidencia insuficiente para autoexecucao",
            ),
            policy={
                "summary": "auto 0, guided 0, validar 1, defer 0",
            },
        )
    )
    execution = cycle["dispatched"][0]
    episode = memory.active_episodes["focus-1"]
    assert execution["dispatch_kind"] == "queue"
    assert execution["status"] == "queued"
    assert execution["policy_decision"] == "needs_validation"
    assert dispatcher.calls == []
    assert episode["pending_follow_up_action"]["action_id"] == "feedback-validate-policy"
    assert episode["policy_decision"] == "needs_validation"


@pytest.mark.asyncio
async def test_adaptive_executor_clears_pending_follow_up_when_promoted_action_executes():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    memory.active_episodes["focus-1"]["pending_follow_up_action"] = {
        "action_id": "feedback-1",
        "focus_id": "focus-1",
        "domain": "finance",
        "kind": "feedback_follow_up",
        "title": "Replanejar pesquisa",
        "summary": "Falha anterior",
        "priority": 0.94,
        "recommended_action": "plan",
        "executor_id": "strategy_planner",
        "horizon": "now",
        "instruction": "Replanejar com pergunta mais estreita.",
        "rationale": "feedback failed",
        "dispatch_immediately": False,
        "source": "adaptive_feedback",
    }
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(bank, chat, memory, dispatcher=dispatcher)

    cycle = await executor.synchronize_plan(
        _plan(
            "plan-follow-up",
            "growth",
            "Replanejar frente travada.",
            _action(
                "focus-1",
                "Replanejar pesquisa",
                recommended_action="plan",
                executor_id="strategy_planner",
                kind="feedback_follow_up",
                action_id="feedback-1",
                source="adaptive_feedback",
            ),
        )
    )

    episode = memory.active_episodes["focus-1"]
    assert cycle["dispatched"][0]["dispatch_kind"] == "tool"
    assert dispatcher.calls[0][0] == "perplexity_search"
    assert episode["pending_follow_up_action"] is None
    assert episode["last_planned_follow_up_action"]["action_id"] == "feedback-1"
    assert episode["follow_up_plan_signature"] == "plan-follow-up"
