import json
import os
import sys
from unittest.mock import AsyncMock

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.services.adaptive_executor import AdaptiveExecutorService
from vps.services.adaptive_planner import AdaptivePlannerService
import vps.sync_server as sync_server


class FakeBank:
    def __init__(self):
        self.system_events = []
        self.task_updates = []

    def insert_system_event(self, event_data):
        self.system_events.append(dict(event_data))
        return f"evt_{len(self.system_events)}"

    def update_task_execution(self, task_id, new_status, output=None, success=None):
        self.task_updates.append(
            {
                "task_id": task_id,
                "new_status": new_status,
                "output": output,
                "success": success,
            }
        )


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
                "title": f"Titulo {focus_id}",
                "domain": "finance",
                "priority": 0.91,
                "execution_rank": 1,
                "recommended_action": "research",
                "planner_mode": "growth",
            }
            for focus_id in focus_ids
        }


class FakeDispatcher:
    def __init__(self):
        self.calls = []

    async def dispatch_tool(self, tool_name, arguments):
        self.calls.append((tool_name, dict(arguments)))


def _plan(signature: str, mode: str, objective: str, *actions):
    return {
        "signature": signature,
        "mode": mode,
        "objective": objective,
        "immediate_actions": list(actions),
    }


def _action(focus_id: str, title: str, recommended_action: str = "research"):
    return {
        "focus_id": focus_id,
        "title": title,
        "recommended_action": recommended_action,
        "executor_id": "market_analyst",
        "domain": "finance",
        "summary": f"Resumo do foco {title}.",
        "kind": "world_signal",
        "priority": 0.91,
        "rank": 1,
        "horizon": "now",
        "instruction": f"Instruir sobre {title}",
        "rationale": "teste",
    }


@pytest.mark.asyncio
async def test_tool_result_updates_episode_requests_replan_and_dispatches_safe_follow_up():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    planner = AdaptivePlannerService(bank, chat, memory)
    planner.current_plan = {"mode": "growth"}
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(
        bank,
        chat,
        memory,
        dispatcher=dispatcher,
        replan_callback=planner.handle_execution_feedback,
    )

    await executor.synchronize_plan(
        _plan(
            "plan-1",
            "growth",
            "Converter pesquisa em execucao.",
            _action("focus-1", "Pesquisa de mercado", recommended_action="research"),
        )
    )

    query = dispatcher.calls[0][1]["query"]
    feedback = await executor.handle_tool_result(
        {
            "tool_name": "perplexity_search",
            "status": "success",
            "result": {
                "query": query,
                "full_answer": "Mitigacao concreta com tres caminhos de acao, sinal de confirmacao operacional, risco residual, proximo experimento e criterios claros para decidir ainda neste ciclo tatico.",
            },
        }
    )

    episode = memory.active_episodes["focus-1"]
    event_types = [event["event_type"] for event in bank.system_events]

    assert feedback["status"] == "success"
    assert feedback["quality_score"] >= 0.6
    assert feedback["replan_outcome"]["strategic_review"]["verdict"] == "actionable_progress"
    assert feedback["replan_outcome"]["strategic_review"]["posture"] == "consolidate_and_move"
    assert feedback["replan_outcome"]["follow_up_action"]["dispatch_immediately"] is True
    assert feedback["follow_up_execution"]["dispatch_kind"] == "chat"
    assert episode["execution_status"] == "briefed"
    assert episode["feedback_ready"] is True
    assert episode["replan_hint"]
    assert episode["pending_follow_up_action"] is None
    assert episode["last_follow_up_action"]["dispatch_immediately"] is True
    assert episode["strategy_verdict"] == "actionable_progress"
    assert episode["strategy_posture"] == "consolidate_and_move"
    assert episode["last_follow_up_execution"]["source"] == "adaptive_feedback"
    assert bank.task_updates[0]["new_status"] == "completed"
    assert "adaptive_action_result" in event_types
    assert "adaptive_replan_request" in event_types
    assert "adaptive_strategy_review" in event_types
    assert "adaptive_follow_up_dispatch" in event_types
    assert any("Sugestao de follow-up" in insight for insight in chat.insights)


@pytest.mark.asyncio
async def test_tool_result_updates_delivery_learning_state_for_tool_and_executor():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-delivery")
    planner = AdaptivePlannerService(bank, chat, memory)
    planner.current_plan = {"mode": "growth"}
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(
        bank,
        chat,
        memory,
        dispatcher=dispatcher,
        replan_callback=planner.handle_execution_feedback,
    )

    await executor.synchronize_plan(
        _plan(
            "plan-delivery",
            "growth",
            "Converter pesquisa em execucao.",
            _action("focus-delivery", "Pesquisa instrumental", recommended_action="research"),
        )
    )

    query = dispatcher.calls[0][1]["query"]
    feedback = await executor.handle_tool_result(
        {
            "tool_name": "perplexity_search",
            "status": "success",
            "result": {
                "query": query,
                "full_answer": "Resposta operacional consistente com implicacoes praticas claras e proximo passo de acao definido com criterios de decisao bem estruturados para o ciclo atual e proximasaccoes.",
            },
        }
    )

    delivery_state = memory.active_episodes["focus-delivery"]["delivery_learning_state"]
    assert feedback["executor_id"] == "market_analyst"
    assert delivery_state["by_tool"]["perplexity_search"]["success_count"] == 1
    assert delivery_state["by_tool"]["perplexity_search"]["pattern"] == "execution_productive"
    assert delivery_state["by_executor"]["market_analyst"]["success_count"] == 1
    assert feedback["delivery_learning_state"]["by_executor"]["market_analyst"]["pattern"] == "execution_productive"


@pytest.mark.asyncio
async def test_failed_tool_result_arms_follow_up_without_immediate_dispatch():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-2")
    planner = AdaptivePlannerService(bank, chat, memory)
    planner.current_plan = {"mode": "growth"}
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(
        bank,
        chat,
        memory,
        dispatcher=dispatcher,
        replan_callback=planner.handle_execution_feedback,
    )

    await executor.synchronize_plan(
        _plan(
            "plan-2",
            "growth",
            "Converter pesquisa em execucao.",
            _action("focus-2", "Pesquisa com falha", recommended_action="research"),
        )
    )

    query = dispatcher.calls[0][1]["query"]
    feedback = await executor.handle_tool_result(
        {
            "tool_name": "perplexity_search",
            "status": "failed",
            "result": {
                "query": query,
                "message": "Timeout na pesquisa profunda.",
            },
        }
    )

    episode = memory.active_episodes["focus-2"]
    event_types = [event["event_type"] for event in bank.system_events]

    assert feedback["status"] == "failed"
    assert feedback["replan_outcome"]["strategic_review"]["verdict"] == "blocked_execution"
    assert feedback["replan_outcome"]["strategic_review"]["posture"] == "tighten_scope"
    assert feedback["replan_outcome"]["follow_up_action"]["dispatch_immediately"] is False
    assert feedback["replan_outcome"]["follow_up_action"]["recommended_action"] == "plan"
    assert "follow_up_execution" not in feedback
    assert episode["execution_status"] == "failed"
    assert episode["pending_follow_up_action"]["dispatch_immediately"] is False
    assert episode["last_follow_up_action"]["recommended_action"] == "plan"
    assert episode["strategy_verdict"] == "blocked_execution"
    assert episode["learning_signal"] == "execution_failure_or_scope_issue"
    assert bank.task_updates[0]["new_status"] == "failed"
    assert "adaptive_action_result" in event_types
    assert "adaptive_replan_request" in event_types
    assert "adaptive_strategy_review" in event_types
    assert "adaptive_follow_up_dispatch" not in event_types
    assert not any("Sugestao de follow-up" in insight for insight in chat.insights)


@pytest.mark.asyncio
async def test_low_quality_success_requires_validation_instead_of_immediate_follow_up():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-3")
    planner = AdaptivePlannerService(bank, chat, memory)
    planner.current_plan = {"mode": "growth"}
    dispatcher = FakeDispatcher()
    executor = AdaptiveExecutorService(
        bank,
        chat,
        memory,
        dispatcher=dispatcher,
        replan_callback=planner.handle_execution_feedback,
    )

    await executor.synchronize_plan(
        _plan(
            "plan-3",
            "growth",
            "Converter pesquisa em execucao.",
            _action("focus-3", "Pesquisa rasa", recommended_action="research"),
        )
    )

    query = dispatcher.calls[0][1]["query"]
    feedback = await executor.handle_tool_result(
        {
            "tool_name": "perplexity_search",
            "status": "success",
            "result": {
                "query": query,
                "full_answer": "Panorama inicial ainda incompleto.",
            },
        }
    )

    episode = memory.active_episodes["focus-3"]

    assert feedback["status"] == "success"
    assert feedback["quality_score"] < 0.6
    assert feedback["replan_outcome"]["confidence_band"] == "low"
    assert feedback["replan_outcome"]["strategic_review"]["verdict"] == "insufficient_evidence"
    assert feedback["replan_outcome"]["strategic_review"]["posture"] == "validate_before_commit"
    assert feedback["replan_outcome"]["follow_up_action"]["dispatch_immediately"] is False
    assert feedback["replan_outcome"]["follow_up_action"]["recommended_action"] == "plan"
    assert "follow_up_execution" not in feedback
    assert episode["pending_follow_up_action"]["recommended_action"] == "plan"
    assert episode["feedback_confidence_band"] == "low"
    assert episode["feedback_quality_score"] < 0.6
    assert episode["strategy_verdict"] == "insufficient_evidence"
    assert episode["strategy_posture"] == "validate_before_commit"


@pytest.mark.asyncio
async def test_repeated_feedback_builds_learning_state_for_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-4")
    planner = AdaptivePlannerService(bank, chat, memory)
    planner.current_plan = {"mode": "growth"}

    first = await planner.handle_execution_feedback(
        {
            "focus_id": "focus-4",
            "status": "success",
            "summary": "Panorama ainda raso e pouco acionavel.",
            "quality_score": 0.32,
            "plan_signature": "plan-a",
        }
    )
    second = await planner.handle_execution_feedback(
        {
            "focus_id": "focus-4",
            "status": "success",
            "summary": "Nova rodada ainda mostrou evidencia incompleta.",
            "quality_score": 0.28,
            "plan_signature": "plan-b",
        }
    )

    episode = memory.active_episodes["focus-4"]
    event_types = [event["event_type"] for event in bank.system_events]

    assert first["learning_state"]["review_count"] == 1
    assert second["learning_state"]["review_count"] == 2
    assert second["learning_state"]["insufficient_count"] == 2
    assert second["learning_state"]["dominant_pattern"] == "evidence_weak"
    assert episode["learning_pattern"] == "evidence_weak"
    assert episode["learning_state"]["rolling_quality_score"] == 0.3
    assert "adaptive_learning_update" in event_types


@pytest.mark.asyncio
async def test_sync_server_notifies_tool_result_consumers_and_posts_report():
    sync_server.clear_tool_result_consumers()
    chat = FakeChatManager()
    sync_server._chat_manager = chat
    consumed = []

    async def consumer(message):
        consumed.append(message)

    sync_server.register_tool_result_consumer(consumer)

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        json.dumps(
            {
                "type": "tool_result",
                "tool_name": "perplexity_search",
                "status": "success",
                "result": {
                    "query": "Tema X",
                    "full_answer": "Resposta detalhada para Tema X.",
                },
            }
        ),
        Exception("exit"),
    ]

    try:
        await sync_server.websocket_endpoint(mock_ws)
    except Exception:
        pass

    assert consumed[0]["tool_name"] == "perplexity_search"
    assert any("Deep Research" in insight and "Tema X" in insight for insight in chat.insights)
    sync_server.clear_tool_result_consumers()


@pytest.mark.asyncio
async def test_sync_server_persists_context_sync_signal():
    class FakeSignalBank:
        def __init__(self):
            self.signals = []
            self.conversation_signals = []

        def insert_signal(self, signal):
            self.signals.append(dict(signal))
            return "sig-1"

        def insert_conversation_signal(self, signal):
            self.conversation_signals.append(dict(signal))
            return "conv-1"

    bank = FakeSignalBank()
    sync_server._causal_bank = bank

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        json.dumps(
            {
                "type": "context_sync",
                "priority": "normal",
                "data": {
                    "active_app": "WhatsApp",
                    "context_category": "communication",
                    "privacy_level": "abstracted",
                },
            }
        ),
        Exception("exit"),
    ]

    try:
        await sync_server.websocket_endpoint(mock_ws)
    except Exception:
        pass

    assert len(bank.signals) == 1
    assert bank.signals[0]["domain"] == "communication"
    assert "WhatsApp" in bank.signals[0]["title"]
    assert bank.conversation_signals == []
    sync_server._causal_bank = None


@pytest.mark.asyncio
async def test_sync_server_promotes_relevant_communication_to_conversation_signal():
    class FakeSignalBank:
        def __init__(self):
            self.signals = []
            self.conversation_signals = []

        def insert_signal(self, signal):
            self.signals.append(dict(signal))
            return "sig-1"

        def insert_conversation_signal(self, signal):
            self.conversation_signals.append(dict(signal))
            return "conv-1"

    bank = FakeSignalBank()
    sync_server._causal_bank = bank

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        json.dumps(
            {
                "type": "context_sync",
                "priority": "high",
                "data": {
                    "active_app": "WhatsApp",
                    "context_category": "communication",
                    "relevance_score": 0.85,
                },
            }
        ),
        Exception("exit"),
    ]

    try:
        await sync_server.websocket_endpoint(mock_ws)
    except Exception:
        pass

    assert len(bank.signals) == 1
    assert len(bank.conversation_signals) == 1
    assert bank.conversation_signals[0]["conversation_id"]
    assert bank.conversation_signals[0]["external_events"]["summary"]
    sync_server._causal_bank = None


@pytest.mark.asyncio
async def test_sync_server_dedupes_context_signature():
    class FakeSignalBank:
        def __init__(self):
            self.signals = []

        def insert_signal(self, signal):
            self.signals.append(dict(signal))
            return "sig-1"

        def insert_conversation_signal(self, signal):
            return "conv-1"

    bank = FakeSignalBank()
    sync_server._causal_bank = bank
    sync_server._recent_context_signatures = {}

    message = {
        "type": "context_sync",
        "priority": "normal",
        "data": {
            "active_app": "WhatsApp",
            "context_category": "communication",
            "context_signature": "abc123",
            "relevance_score": 0.8,
        },
    }

    await sync_server._handle_context_sync(message)
    await sync_server._handle_context_sync(message)

    assert len(bank.signals) == 1
    sync_server._causal_bank = None
    sync_server._recent_context_signatures = {}


@pytest.mark.asyncio
async def test_sync_server_registers_growth_target_from_values():
    class FakeSignalBank:
        def __init__(self):
            self.signals = []
            self.conversation_signals = []
            self.growth_targets = []

        def insert_signal(self, signal):
            self.signals.append(dict(signal))
            return "sig-1"

        def insert_conversation_signal(self, signal):
            self.conversation_signals.append(dict(signal))
            return "conv-1"

        def get_active_growth_targets(self, domain=None):
            if domain:
                return [t for t in self.growth_targets if t.get("domain") == domain]
            return list(self.growth_targets)

        def insert_growth_target(self, target):
            self.growth_targets.append(dict(target))
            return "gt-1"

    bank = FakeSignalBank()
    sync_server._causal_bank = bank

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        json.dumps(
            {
                "type": "context_sync",
                "priority": "high",
                "data": {
                    "active_app": "WhatsApp",
                    "context_category": "communication",
                    "relevance_score": 0.9,
                    "content": "Preciso resolver o controle financeiro hoje.",
                },
            }
        ),
        Exception("exit"),
    ]

    try:
        await sync_server.websocket_endpoint(mock_ws)
    except Exception:
        pass

    assert len(bank.growth_targets) == 1
    assert bank.growth_targets[0]["domain"] == "finance"
    sync_server._causal_bank = None


@pytest.mark.asyncio
async def test_sync_server_registers_behavioral_pattern_from_repeated_friction():
    class FakeSignalBank:
        def __init__(self):
            self.signals = []
            self.conversation_signals = []
            self.behavioral_patterns = []

        def insert_signal(self, signal):
            self.signals.append(dict(signal))
            return "sig-1"

        def insert_conversation_signal(self, signal):
            self.conversation_signals.append(dict(signal))
            return "conv-1"

        def get_recent_conversation_signals(self, days=3, limit=50):
            return list(self.conversation_signals)[:limit]

        def get_behavioral_patterns(self, domain=None, min_confidence=0.3):
            if domain:
                return [p for p in self.behavioral_patterns if p.get("domain") == domain]
            return list(self.behavioral_patterns)

        def insert_behavioral_pattern(self, pattern):
            self.behavioral_patterns.append(dict(pattern))
            return "bp-1"

        def append_behavioral_evidence(self, pattern_id, evidence):
            return "bp-2"

    import os
    bank = FakeSignalBank()
    sync_server._causal_bank = bank

    old_count = os.environ.get("REBEKA_COMM_PATTERN_MIN_COUNT")
    old_threshold = os.environ.get("REBEKA_COMM_PATTERN_SCORE_THRESHOLD")
    os.environ["REBEKA_COMM_PATTERN_MIN_COUNT"] = "1"
    os.environ["REBEKA_COMM_PATTERN_SCORE_THRESHOLD"] = "0.5"

    mock_ws = AsyncMock()
    mock_ws.receive_text.side_effect = [
        json.dumps(
            {
                "type": "context_sync",
                "priority": "high",
                "data": {
                    "active_app": "WhatsApp",
                    "context_category": "communication",
                    "relevance_score": 0.9,
                    "content": "Mensagem urgente sobre prazo.",
                },
            }
        ),
        Exception("exit"),
    ]

    try:
        await sync_server.websocket_endpoint(mock_ws)
    except Exception:
        pass

    if old_count is None:
        os.environ.pop("REBEKA_COMM_PATTERN_MIN_COUNT", None)
    else:
        os.environ["REBEKA_COMM_PATTERN_MIN_COUNT"] = old_count
    if old_threshold is None:
        os.environ.pop("REBEKA_COMM_PATTERN_SCORE_THRESHOLD", None)
    else:
        os.environ["REBEKA_COMM_PATTERN_SCORE_THRESHOLD"] = old_threshold

    assert len(bank.behavioral_patterns) == 1
    assert bank.behavioral_patterns[0]["pattern_type"] == "communication_urgency"
    sync_server._causal_bank = None
