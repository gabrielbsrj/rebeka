import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.services.adaptive_planner import AdaptivePlannerService


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


def _snapshot(*focuses):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signature": f"workspace-{'-'.join(focus['focus_id'] for focus in focuses)}",
        "summary": "Workspace sintetico.",
        "focuses": list(focuses),
    }


def _focus(
    focus_id: str,
    title: str,
    domain: str = "finance",
    kind: str = "world_signal",
    action: str = "research",
    priority: float = 0.84,
):
    return {
        "focus_id": focus_id,
        "kind": kind,
        "domain": domain,
        "title": title,
        "summary": f"Resumo do foco {title}.",
        "priority": priority,
        "recommended_action": action,
        "source_ids": [f"src-{focus_id}"],
        "confidence": 0.8,
    }


@pytest.mark.asyncio
async def test_adaptive_planner_enters_defense_mode_for_survival_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-survival", "focus-finance")
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-survival", "Risco imediato de recursos", domain="survival", action="alert", priority=0.95),
            _focus("focus-finance", "Mercado estressa spreads", domain="finance", action="research", priority=0.82),
        )
    )

    assert plan["mode"] == "defense"
    assert plan["immediate_actions"][0]["focus_id"] == "focus-survival"
    assert bank.system_events[0]["event_type"] == "adaptive_execution_plan"
    assert "Modo: defense" in chat.insights[0]


@pytest.mark.asyncio
async def test_adaptive_planner_updates_episode_metadata_and_avoids_duplicate_publication():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    planner = AdaptivePlannerService(bank, chat, memory)

    snapshot = _snapshot(
        _focus("focus-1", "Janela de oportunidade em macro", domain="macro", action="research", priority=0.88),
        _focus("focus-2", "Ajuste na comunicacao com usuario", domain="user", kind="user_tension", action="follow_up", priority=0.76),
    )

    await planner.synchronize_snapshot(snapshot)
    await planner.synchronize_snapshot(snapshot)

    episode = memory.active_episodes["focus-1"]
    event_types = [event["event_type"] for event in bank.system_events]
    assert episode["planner_mode"] == "growth"
    assert episode["planning_horizon"] == "now"
    assert episode["execution_rank"] == 1
    assert "Modo growth" in episode["tactical_instruction"]
    assert len(bank.system_events) == 4
    assert "adaptive_execution_plan" in event_types
    assert "adaptive_policy_snapshot" in event_types
    assert "adaptive_self_model_snapshot" in event_types
    assert "adaptive_learning_registry_snapshot" in event_types
    assert len(chat.insights) == 1


@pytest.mark.asyncio
async def test_adaptive_planner_shifts_to_growth_mode_when_opportunity_dominates():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-growth", "focus-watch")
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-growth", "Expansao de automacao financeira", domain="finance", action="plan", priority=0.9),
            _focus("focus-watch", "Sinal secundario de inovacao", domain="innovation", action="monitor", priority=0.71),
        )
    )

    assert plan["mode"] == "growth"
    assert plan["objective"].startswith("Converter 'Expansao de automacao financeira'")
    assert plan["next_actions"][0]["focus_id"] == "focus-watch"
    assert len(plan["strategic_tracks"]) >= 1


@pytest.mark.asyncio
async def test_adaptive_planner_promotes_pending_follow_up_into_agenda():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    memory.active_episodes["focus-1"]["pending_follow_up_action"] = {
        "action_id": "feedback-1",
        "focus_id": "focus-1",
        "domain": "finance",
        "kind": "feedback_follow_up",
        "title": "Replanejar Pesquisa de mercado",
        "summary": "Falha operacional anterior.",
        "priority": 0.93,
        "recommended_action": "plan",
        "executor_id": "strategy_planner",
        "horizon": "now",
        "instruction": "Replanejar a pesquisa com recorte mais estreito.",
        "rationale": "feedback failed, precisa nova estrategia",
        "dispatch_immediately": False,
        "source": "adaptive_feedback",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa de mercado", domain="finance", action="research", priority=0.78),
        )
    )

    episode = memory.active_episodes["focus-1"]
    assert plan["agenda"][0]["kind"] == "feedback_follow_up"
    assert plan["agenda"][0]["title"] == "Replanejar Pesquisa de mercado"
    assert plan["agenda"][0]["recommended_action"] == "plan"
    assert plan["agenda"][0]["instruction"] == "Replanejar a pesquisa com recorte mais estreito."
    assert plan["immediate_actions"][0]["action_id"] == "feedback-1"
    assert episode["planned_follow_up_action"]["action_id"] == "feedback-1"


@pytest.mark.asyncio
async def test_adaptive_planner_priority_shaping_promotes_actionable_progress_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "actionable_progress",
        "confidence_band": "high",
        "priority_delta": 0.07,
        "priority_policy": "advance",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Sinal consolidado", domain="finance", action="research", priority=0.72),
            _focus("focus-2", "Sinal concorrente", domain="macro", action="research", priority=0.75),
        )
    )

    dominant = plan["agenda"][0]
    assert dominant["focus_id"] == "focus-1"
    assert dominant["priority"] == 0.79
    assert dominant["priority_adjustment"] == 0.07
    assert dominant["priority_policy"] == "advance"
    assert dominant["strategy_verdict"] == "actionable_progress"
    assert dominant["budget_tier"] == "focused"
    assert dominant["tool_budget_eligible"] is True
    assert plan["budget"]["tool_dispatch_limit"] >= 1
    assert "ajuste +0.07" in dominant["rationale"]


@pytest.mark.asyncio
async def test_adaptive_planner_priority_shaping_keeps_blocked_follow_up_near_front():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "blocked_execution",
        "confidence_band": "medium",
        "priority_delta": 0.02,
        "priority_policy": "scope_repair",
    }
    memory.active_episodes["focus-1"]["pending_follow_up_action"] = {
        "action_id": "feedback-1",
        "focus_id": "focus-1",
        "domain": "finance",
        "kind": "feedback_follow_up",
        "title": "Replanejar Pesquisa de mercado",
        "summary": "Falha operacional anterior.",
        "priority": 0.62,
        "recommended_action": "plan",
        "executor_id": "strategy_planner",
        "horizon": "now",
        "instruction": "Replanejar a pesquisa com recorte mais estreito.",
        "rationale": "feedback failed, precisa nova estrategia",
        "dispatch_immediately": False,
        "source": "adaptive_feedback",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa de mercado", domain="finance", action="research", priority=0.60),
            _focus("focus-2", "Sinal paralelo", domain="macro", action="research", priority=0.64),
        )
    )

    dominant = plan["agenda"][0]
    assert dominant["focus_id"] == "focus-1"
    assert dominant["kind"] == "feedback_follow_up"
    assert dominant["priority"] == 0.68
    assert dominant["priority_adjustment"] == 0.04
    assert dominant["priority_policy"] == "scope_repair"


@pytest.mark.asyncio
async def test_adaptive_planner_learning_pattern_boosts_productive_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "actionable_progress",
        "confidence_band": "high",
        "priority_delta": 0.07,
        "priority_policy": "advance",
    }
    memory.active_episodes["focus-1"]["learning_state"] = {
        "dominant_pattern": "execution_productive",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Frente produtiva", domain="finance", action="research", priority=0.70),
            _focus("focus-2", "Frente concorrente", domain="macro", action="research", priority=0.78),
        )
    )

    dominant = plan["agenda"][0]
    assert dominant["focus_id"] == "focus-1"
    assert dominant["priority"] == 0.8
    assert dominant["learning_pattern"] == "execution_productive"
    assert dominant["learning_priority_adjustment"] == 0.03
    assert "aprendizado execution_productive" in dominant["rationale"]


@pytest.mark.asyncio
async def test_adaptive_planner_allocates_validate_budget_for_low_evidence_follow_up():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "insufficient_evidence",
        "confidence_band": "low",
        "priority_delta": -0.08,
        "priority_policy": "validate",
    }
    memory.active_episodes["focus-1"]["pending_follow_up_action"] = {
        "action_id": "feedback-validate",
        "focus_id": "focus-1",
        "domain": "finance",
        "kind": "feedback_follow_up",
        "title": "Validar retorno de pesquisa",
        "summary": "Evidencia ainda rasa.",
        "priority": 0.74,
        "recommended_action": "plan",
        "executor_id": "strategy_planner",
        "horizon": "now",
        "instruction": "Validar lacunas antes de nova acao.",
        "rationale": "feedback success, qualidade baixa",
        "dispatch_immediately": False,
        "source": "adaptive_feedback",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa rasa", domain="finance", action="research", priority=0.73),
            _focus("focus-2", "Sinal forte paralelo", domain="macro", action="research", priority=0.82),
        )
    )

    validate_action = next(action for action in plan["agenda"] if action["focus_id"] == "focus-1")
    assert validate_action["budget_tier"] == "validate"
    assert validate_action["tool_budget_eligible"] is False
    assert validate_action["priority_policy"] == "validate"
    assert validate_action["policy_decision"] == "needs_validation"
    assert plan["budget"]["budget_posture"] == "validate"
    assert plan["budget"]["tool_dispatch_limit"] == 1
    assert plan["policy"]["counts"]["needs_validation"] == 1


@pytest.mark.asyncio
async def test_adaptive_planner_builds_operational_self_model_snapshot():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "actionable_progress",
        "confidence_band": "high",
        "priority_delta": 0.07,
        "priority_policy": "advance",
    }
    memory.active_episodes["focus-2"]["strategic_review"] = {
        "verdict": "insufficient_evidence",
        "confidence_band": "low",
        "priority_delta": -0.08,
        "priority_policy": "validate",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Frente madura", domain="finance", action="research", priority=0.84),
            _focus("focus-2", "Frente incerta", domain="macro", action="plan", priority=0.8),
        )
    )

    self_model = plan["self_model"]
    event_types = [event["event_type"] for event in bank.system_events]
    assert self_model["autonomy_posture"] == "guarded"
    assert self_model["tool_capacity"] == plan["budget"]["tool_dispatch_limit"]
    assert self_model["domain_confidence"]["finance"] >= 0.8
    assert self_model["domain_confidence"]["macro"] <= 0.35
    assert plan["policy"]["autonomy_posture"] == self_model["autonomy_posture"]
    assert "adaptive_policy_snapshot" in event_types
    assert "adaptive_self_model_snapshot" in event_types
    assert "adaptive_learning_registry_snapshot" in event_types


@pytest.mark.asyncio
async def test_adaptive_planner_builds_learning_registry_and_expands_budget_when_productive():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 2,
        "rolling_quality_score": 0.81,
        "dominant_pattern": "execution_productive",
    }
    memory.active_episodes["focus-2"]["learning_state"] = {
        "review_count": 2,
        "rolling_quality_score": 0.79,
        "dominant_pattern": "execution_productive",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Tensao prioritaria", domain="user", kind="user_tension", action="research", priority=0.86),
            _focus("focus-2", "Pesquisa tatico-financeira", domain="finance", action="research", priority=0.8),
        )
    )

    learning_registry = plan["learning_registry"]
    event_types = [event["event_type"] for event in bank.system_events]
    assert plan["mode"] == "care"
    assert learning_registry["global_pattern"] == "execution_productive"
    assert learning_registry["domains"]["finance"]["pattern"] == "execution_productive"
    assert plan["budget"]["learning_bias"] == 0.6
    assert plan["budget"]["tool_dispatch_limit"] == 2
    assert plan["self_model"]["learning_registry_pattern"] == "execution_productive"
    assert "adaptive_learning_registry_snapshot" in event_types


@pytest.mark.asyncio
async def test_adaptive_planner_blends_weak_learning_into_domain_confidence():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.28,
        "dominant_pattern": "evidence_weak",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa recorrente", domain="finance", action="research", priority=0.88),
            _focus("focus-2", "Sinal secundario", domain="macro", action="research", priority=0.76),
        )
    )

    learning_registry = plan["learning_registry"]
    assert learning_registry["global_pattern"] == "evidence_weak"
    assert learning_registry["domains"]["finance"]["pattern"] == "evidence_weak"
    assert plan["budget"]["learning_bias"] == -0.6
    assert plan["self_model"]["learning_registry_pattern"] == "evidence_weak"
    assert plan["self_model"]["domain_confidence"]["finance"] == 0.62


@pytest.mark.asyncio
async def test_adaptive_planner_uses_delivery_learning_for_tool_and_executor_policy():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["delivery_learning_state"] = {
        "by_tool": {
            "perplexity_search": {
                "attempt_count": 2,
                "success_count": 0,
                "failure_count": 2,
                "rolling_quality_score": 0.18,
                "last_status": "failed",
                "pattern": "scope_fragile",
            }
        },
        "by_executor": {
            "market_analyst": {
                "attempt_count": 2,
                "success_count": 0,
                "failure_count": 2,
                "rolling_quality_score": 0.22,
                "last_status": "failed",
                "pattern": "scope_fragile",
            }
        },
        "last_tool_name": "perplexity_search",
        "last_executor_id": "market_analyst",
        "last_status": "failed",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa critica", domain="finance", action="research", priority=0.88),
            _focus("focus-2", "Sinal lateral", domain="macro", action="monitor", priority=0.62),
        )
    )

    action = next(item for item in plan["agenda"] if item["focus_id"] == "focus-1")
    assert plan["learning_registry"]["tools"]["perplexity_search"]["pattern"] == "scope_fragile"
    assert plan["self_model"]["tool_confidence"]["perplexity_search"] == 0.18
    assert plan["self_model"]["autonomy_posture"] == "skeptical"
    assert action["tool_learning_pattern"] == "scope_fragile"
    assert action["executor_rerouted_from"] == "market_analyst"
    assert action["executor_id"] == "strategy_planner"
    assert action["tool_budget_weight"] < 0.5
    assert action["policy_decision"] == "guided_execute"


@pytest.mark.asyncio
async def test_adaptive_planner_reduces_budget_with_behavioral_pattern_pressure():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.28,
        "dominant_pattern": "scope_fragile",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa fragil", domain="finance", action="research", priority=0.88),
            _focus("focus-bp", "Padrao recorrente", domain="finance", kind="behavioral_pattern", action="follow_up", priority=0.8),
        )
    )

    action = next(item for item in plan["agenda"] if item["focus_id"] == "focus-1")
    assert action["behavioral_pressure"] is True
    assert action["tool_budget_weight"] < 0.5


@pytest.mark.asyncio
async def test_adaptive_planner_recalibrates_executor_when_learning_is_fragile():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.31,
        "dominant_pattern": "evidence_weak",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa fragil", domain="finance", action="research", priority=0.88),
            _focus("focus-2", "Observacao de apoio", domain="macro", action="monitor", priority=0.62),
        )
    )

    action = next(item for item in plan["agenda"] if item["focus_id"] == "focus-1")
    episode = memory.active_episodes["focus-1"]
    assert action["executor_rerouted_from"] == "market_analyst"
    assert action["executor_id"] == "strategy_planner"
    assert action["executor_learning_pattern"] == "evidence_weak"
    assert action["tool_budget_weight"] < 0.6
    assert episode["executor_id"] == "strategy_planner"
    assert episode["executor_rerouted_from"] == "market_analyst"


@pytest.mark.asyncio
async def test_adaptive_planner_uses_skeptical_autonomy_for_multi_cycle_weak_learning():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.28,
        "dominant_pattern": "evidence_weak",
    }
    memory.active_episodes["focus-2"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.3,
        "dominant_pattern": "evidence_weak",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa recorrente", domain="finance", action="research", priority=0.88),
            _focus("focus-2", "Pesquisa complementar", domain="macro", action="research", priority=0.82),
        )
    )

    by_focus = {action["focus_id"]: action for action in plan["agenda"]}
    assert plan["self_model"]["autonomy_posture"] == "skeptical"
    assert plan["policy"]["autonomy_posture"] == "skeptical"
    assert by_focus["focus-1"]["policy_decision"] == "needs_validation"
    assert by_focus["focus-1"]["executor_learning_pattern"] == "evidence_weak"
    assert plan["budget"]["tool_dispatch_limit"] == 1
    assert plan["policy"]["counts"]["needs_validation"] == 2


@pytest.mark.asyncio
async def test_adaptive_planner_applies_guardrail_for_financial_payment_intent():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pagar boleto de energia", domain="finance", action="plan", priority=0.86),
        )
    )

    action = plan["agenda"][0]
    assert action["policy_decision"] == "needs_validation"
    assert "payment_operation" in action.get("guardrail_flags", [])


@pytest.mark.asyncio
async def test_adaptive_planner_assigns_policy_decisions_for_assertive_and_watch_actions():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1", "focus-2", "focus-3", "focus-4")
    memory.active_episodes["focus-1"]["strategic_review"] = {
        "verdict": "actionable_progress",
        "confidence_band": "high",
        "priority_delta": 0.07,
        "priority_policy": "advance",
    }
    memory.active_episodes["focus-2"]["strategic_review"] = {
        "verdict": "actionable_progress",
        "confidence_band": "high",
        "priority_delta": 0.07,
        "priority_policy": "advance",
    }
    planner = AdaptivePlannerService(bank, chat, memory)
    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Frente principal", domain="finance", action="research", priority=0.88),
            _focus("focus-2", "Frente secundaria", domain="macro", action="plan", priority=0.83),
            _focus("focus-3", "Frente lateral", domain="innovation", action="research", priority=0.72),
            _focus("focus-4", "Observacao de fundo", domain="corporate", action="monitor", priority=0.61),
        )
    )
    by_focus = {action["focus_id"]: action for action in plan["agenda"]}
    assert plan["self_model"]["autonomy_posture"] == "assertive"
    assert by_focus["focus-1"]["policy_decision"] == "auto_execute"
    assert by_focus["focus-1"]["auto_execute"] is True
    assert by_focus["focus-4"]["horizon"] == "watch"
    assert by_focus["focus-4"]["policy_decision"] == "defer"
    assert plan["policy"]["counts"]["auto_execute"] >= 2
    assert plan["policy"]["counts"]["defer"] == 1


@pytest.mark.asyncio
async def test_adaptive_planner_notifies_plan_consumers_only_on_new_signature():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    planner = AdaptivePlannerService(bank, chat, memory)
    consumed = []

    async def consumer(plan):
        consumed.append(plan["signature"])

    planner.register_plan_consumer(consumer)
    snapshot = _snapshot(_focus("focus-1", "Foco unico", domain="finance", action="research", priority=0.85))

    await planner.synchronize_snapshot(snapshot)
    assert len(consumed) == 1


@pytest.mark.asyncio
async def test_adaptive_planner_forces_guided_execute_under_behavioral_pressure():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = FakeEpisodicMemory("focus-1")
    memory.active_episodes["focus-1"]["learning_state"] = {
        "review_count": 3,
        "rolling_quality_score": 0.28,
        "dominant_pattern": "scope_fragile",
    }
    planner = AdaptivePlannerService(bank, chat, memory)

    plan = await planner.synchronize_snapshot(
        _snapshot(
            _focus("focus-1", "Pesquisa fragil", domain="finance", action="research", priority=0.88),
            _focus("focus-bp", "Padrao recorrente", domain="finance", kind="behavioral_pattern", action="follow_up", priority=0.8),
        )
    )

    action = next(item for item in plan["agenda"] if item["focus_id"] == "focus-1")
    assert action["behavioral_pressure"] is True
    assert action["policy_decision"] == "guided_execute"
    assert action["policy_reason"] == "pressao comportamental em dominio fragil exige conducao guiada"
