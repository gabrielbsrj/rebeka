import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.services.episodic_memory import EpisodicTaskMemory


class FakeBank:
    def __init__(self):
        self.plans = []
        self.tasks = []
        self.plan_updates = []
        self.task_updates = []

    def insert_orchestration_plan(self, plan_data):
        self.plans.append(dict(plan_data))
        return plan_data["id"]

    def insert_task_execution(self, task_data):
        self.tasks.append(dict(task_data))
        return task_data["id"]

    def update_plan_status(self, plan_id, new_status, components=None):
        self.plan_updates.append(
            {
                "plan_id": plan_id,
                "new_status": new_status,
                "components": components,
            }
        )

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


def _snapshot(*focuses):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signature": f"sig-{len(focuses)}-{'-'.join(focus['focus_id'] for focus in focuses)}",
        "summary": "Workspace sintetico para testes.",
        "focuses": list(focuses),
    }


def _focus(focus_id: str, title: str, domain: str = "finance", action: str = "research", priority: float = 0.84):
    return {
        "focus_id": focus_id,
        "kind": "world_signal",
        "domain": domain,
        "title": title,
        "summary": f"Resumo do foco {title}.",
        "priority": priority,
        "recommended_action": action,
        "source_ids": [f"src-{focus_id}"],
        "confidence": 0.81,
    }


@pytest.mark.asyncio
async def test_episodic_memory_creates_plan_and_task_for_new_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = EpisodicTaskMemory(bank, chat)

    result = await memory.synchronize_snapshot(
        _snapshot(_focus("focus-1", "Stress de liquidez"))
    )

    assert len(bank.plans) == 1
    assert len(bank.tasks) == 1
    assert result["opened"][0]["focus_id"] == "focus-1"
    assert memory.active_episodes["focus-1"]["recommended_action"] == "research"
    assert any("Stress de liquidez" in insight for insight in chat.insights)


@pytest.mark.asyncio
async def test_episodic_memory_does_not_duplicate_existing_focus():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = EpisodicTaskMemory(bank, chat)

    focus = _focus("focus-1", "Alerta macro")
    await memory.synchronize_snapshot(_snapshot(focus))
    result = await memory.synchronize_snapshot(_snapshot({**focus, "priority": 0.92}))

    assert len(bank.plans) == 1
    assert len(bank.tasks) == 1
    assert result["opened"] == []
    assert result["refreshed"] == ["focus-1"]
    assert memory.active_episodes["focus-1"]["priority"] == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_episodic_memory_closes_focus_that_leaves_workspace():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = EpisodicTaskMemory(bank, chat)

    await memory.synchronize_snapshot(_snapshot(_focus("focus-1", "Pressao de caixa")))
    result = await memory.synchronize_snapshot(_snapshot())

    assert result["closed"][0]["focus_id"] == "focus-1"
    assert bank.task_updates[0]["new_status"] == "completed"
    assert bank.plan_updates[0]["new_status"] == "completed"
    assert "focus-1" not in memory.active_episodes


@pytest.mark.asyncio
async def test_mark_episode_outcome_marks_failure_when_needed():
    bank = FakeBank()
    chat = FakeChatManager()
    memory = EpisodicTaskMemory(bank, chat)

    await memory.synchronize_snapshot(_snapshot(_focus("focus-1", "Falha de infraestrutura", domain="survival", action="alert")))
    outcome = memory.mark_episode_outcome("focus-1", "Nao foi possivel estabilizar os recursos.", success=False)

    assert outcome["status"] == "failed"
    assert bank.task_updates[0]["new_status"] == "failed"
    assert bank.task_updates[0]["success"] is False
    assert bank.plan_updates[0]["new_status"] == "failed"