import pytest
from agent.core.event_bus import GlobalEventBus
from agent.core.scheduler import PriorityScheduler
from agent.core.orchestration_engine import OrchestrationEngine
from agent.intelligence.decision_engine import DecisionEngine

def test_global_event_bus():
    bus = GlobalEventBus()
    events_received = []

    def mock_subscriber(data):
        events_received.append(data)

    bus.subscribe("TEST_EVENT", mock_subscriber)
    bus.publish("TEST_EVENT", {"id": 1})
    bus.publish("OTHER_EVENT", {"id": 2})

    assert len(events_received) == 1
    assert events_received[0]["id"] == 1

def test_priority_scheduler():
    scheduler = PriorityScheduler()
    
    scheduler.add_task(10, {"name": "low_priority"})
    scheduler.add_task(100, {"name": "high_priority"})
    scheduler.add_task(50, {"name": "medium_priority"})

    assert scheduler.has_tasks() is True
    
    first = scheduler.next_task()
    assert first["name"] == "high_priority"
    
    second = scheduler.next_task()
    assert second["name"] == "medium_priority"
    
    third = scheduler.next_task()
    assert third["name"] == "low_priority"

def test_orchestration_engine():
    bus = GlobalEventBus()
    decision = DecisionEngine()
    engine = OrchestrationEngine(event_bus=bus, decision_engine=decision)
    
    dispatched_events = []
    def mock_executor(data):
        dispatched_events.append(data)
        
    bus.subscribe("EXECUTE_PAYMENT_ALERT", mock_executor)
    
    # Simula a chegada de um evento que exige acao
    bus.publish("NEW_ACTION_REQUIRED", {
        "type": "payment_alert",
        "financial_impact": 1000,
        "urgency": 5,
        "user_relevance": 5,
        "confidence": 10
    })
    
    # Processa o ciclo da engine (tira da fila e despacha)
    engine.run_cycle()
    
    assert len(dispatched_events) == 1
    assert dispatched_events[0]["type"] == "payment_alert"
