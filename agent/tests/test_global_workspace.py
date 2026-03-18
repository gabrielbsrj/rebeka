import asyncio
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vps.services.global_workspace import GlobalWorkspaceService


class FakeBank:
    def __init__(self):
        self.domain_signals = {}
        self.growth_targets = []
        self.conversation_signals = []
        self.behavioral_patterns = []
        self.system_events = []

    def get_similar_signals(self, domain: str, limit: int = 5):
        return list(self.domain_signals.get(domain, []))[:limit]

    def get_active_growth_targets(self):
        return list(self.growth_targets)

    def get_recent_conversation_signals(self, days: int = 7, limit: int = 20):
        return list(self.conversation_signals)[:limit]

    def insert_system_event(self, event_data):
        self.system_events.append(event_data)
        return f"evt_{len(self.system_events)}"

    def get_behavioral_patterns(self, domain: str = None, min_confidence: float = 0.5):
        if domain:
            return [p for p in self.behavioral_patterns if p.get("domain") == domain and p.get("confidence", 0) >= min_confidence]
        return [p for p in self.behavioral_patterns if p.get("confidence", 0) >= min_confidence]


class FakeChatManager:
    def __init__(self):
        self.insights = []

    def push_insight(self, text: str):
        self.insights.append(text)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _signal(signal_id: str, domain: str, title: str, content: str, relevance: float):
    return {
        "id": signal_id,
        "domain": domain,
        "title": title,
        "content": content,
        "relevance_score": relevance,
        "created_at": _now_iso(),
    }


def test_workspace_prioritizes_survival_signal_and_user_tension():
    bank = FakeBank()
    chat = FakeChatManager()

    bank.domain_signals = {
        "survival": [
            _signal(
                "surv-1",
                "survival",
                "Crise de liquidez critica",
                "Falha de recursos pode interromper o sistema.",
                0.92,
            )
        ],
        "innovation": [
            _signal(
                "inn-1",
                "innovation",
                "Novo paper interessante",
                "Uma tecnica promissora, mas sem urgencia operacional.",
                0.95,
            )
        ],
    }
    bank.conversation_signals = [
        {
            "id": "conv-1",
            "behavioral_patterns": {
                "problemas_ativos": ["liquidez", "automacao financeira"],
                "interesses": ["macro"],
            },
            "emotional_state_inferred": "alerta",
            "friction_potential": {"finance": 0.8},
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()

    assert snapshot["focuses"][0]["domain"] == "survival"
    assert any(focus["kind"] == "user_tension" for focus in snapshot["focuses"])


@pytest.mark.asyncio
async def test_run_cycle_persists_and_publishes_only_on_new_signature():
    bank = FakeBank()
    chat = FakeChatManager()
    bank.domain_signals = {
        "finance": [
            _signal(
                "fin-1",
                "finance",
                "Mercado estressa spreads",
                "Ha deterioracao relevante no curto prazo.",
                0.83,
            )
        ]
    }

    service = GlobalWorkspaceService(bank, chat, check_interval=1)

    await service.run_cycle()
    await service.run_cycle()

    assert len(bank.system_events) == 1
    assert len(chat.insights) == 1

    bank.domain_signals["finance"] = [
        _signal(
            "fin-2",
            "finance",
            "Queda abrupta no fluxo de caixa",
            "Novo sinal material alterando a agenda cognitiva.",
            0.96,
        )
    ]

    await service.run_cycle()

    assert len(bank.system_events) == 2
    assert len(chat.insights) == 2


@pytest.mark.asyncio
async def test_run_cycle_notifies_snapshot_consumers_on_new_signature():
    bank = FakeBank()
    chat = FakeChatManager()
    bank.domain_signals = {
        "survival": [
            _signal(
                "surv-1",
                "survival",
                "Risco operacional imediato",
                "A continuidade do sistema exige atencao.",
                0.91,
            )
        ]
    }

    consumed = []

    async def consumer(snapshot):
        consumed.append(snapshot["signature"])

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    service.register_snapshot_consumer(consumer)

    await service.run_cycle()
    await service.run_cycle()

    assert len(consumed) == 1


def test_workspace_boosts_signal_aligned_with_growth_target():
    bank = FakeBank()
    chat = FakeChatManager()

    bank.domain_signals = {
        "finance": [
            _signal(
                "fin-1",
                "finance",
                "Automacao financeira ganha tracao",
                "Fluxos financeiros ficaram mais relevantes para o usuario.",
                0.70,
            )
        ],
        "innovation": [
            _signal(
                "inn-1",
                "innovation",
                "Nova interface de video",
                "Sinal interessante, mas sem alinhamento com o alvo ativo.",
                0.70,
            )
        ],
    }
    bank.growth_targets = [
        {
            "id": "gt-1",
            "domain": "finance",
            "current_state": "operacao manual",
            "desired_state": "rotina financeira automatizada",
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()
    titles = [focus["title"] for focus in snapshot["focuses"]]

    assert titles.index("Automacao financeira ganha tracao") < titles.index("Nova interface de video")


def test_workspace_filters_low_relevance_communication_signal():
    bank = FakeBank()
    chat = FakeChatManager()

    bank.domain_signals = {
        "communication": [
            _signal(
                "comm-1",
                "communication",
                "Nova mensagem",
                "Contexto generico sem prioridade.",
                0.25,
            )
        ]
    }

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()

    assert snapshot["focuses"] == []


def test_workspace_conversation_summary_includes_values_and_context():
    bank = FakeBank()
    chat = FakeChatManager()

    bank.conversation_signals = [
        {
            "id": "conv-2",
            "behavioral_patterns": {
                "problemas_ativos": ["organizacao"],
                "interesses": ["produtividade"],
            },
            "values_revealed": ["seguranca", "controle"],
            "external_events": {"summary": "Mensagem urgente do cliente."},
            "emotional_state_inferred": "alerta",
            "friction_potential": {"communication": 0.8},
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()
    focus = next(focus for focus in snapshot["focuses"] if focus["kind"] == "user_tension")

    assert "Valores percebidos" in focus["summary"]
    assert "Contexto recente" in focus["summary"]


def test_workspace_includes_behavioral_pattern_focus():
    bank = FakeBank()
    chat = FakeChatManager()

    bank.behavioral_patterns = [
        {
            "id": "bp-1",
            "domain": "communication",
            "type": "communication_urgency",
            "description": "Pressao recorrente por resposta rapida.",
            "confidence": 0.72,
            "potentially_limiting": True,
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()

    assert any(focus["kind"] == "behavioral_pattern" for focus in snapshot["focuses"])


def test_workspace_excludes_expired_behavioral_pattern():
    """Patterns com last_detected mais antigo que o TTL devem ser descartados."""
    from datetime import timedelta

    bank = FakeBank()
    chat = FakeChatManager()

    old_ts = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    bank.behavioral_patterns = [
        {
            "id": "bp-old",
            "domain": "communication",
            "type": "communication_urgency",
            "description": "Pattern antigo que nao deve virar foco.",
            "confidence": 0.72,
            "potentially_limiting": True,
            "last_detected": old_ts,
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()

    assert not any(focus["kind"] == "behavioral_pattern" for focus in snapshot["focuses"])


def test_workspace_keeps_recent_behavioral_pattern():
    """Patterns com last_detected dentro do TTL devem continuar como focos."""
    from datetime import timedelta

    bank = FakeBank()
    chat = FakeChatManager()

    recent_ts = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    bank.behavioral_patterns = [
        {
            "id": "bp-recent",
            "domain": "communication",
            "type": "communication_urgency",
            "description": "Pattern recente que deve virar foco.",
            "confidence": 0.72,
            "potentially_limiting": True,
            "last_detected": recent_ts,
        }
    ]

    service = GlobalWorkspaceService(bank, chat, check_interval=1)
    snapshot = service.build_snapshot()

    assert any(focus["kind"] == "behavioral_pattern" for focus in snapshot["focuses"])
