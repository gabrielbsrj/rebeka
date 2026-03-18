import pytest
from agent.intelligence.decision_engine import DecisionEngine
from agent.intelligence.strategic_planner import StrategicPlanner
from agent.memory.prediction_memory import PredictionMemory

def test_decision_engine():
    engine = DecisionEngine()
    
    # Evento comum
    score1 = engine.evaluate({"financial_impact": 10, "urgency": 2, "user_relevance": 1, "confidence": 5, "type": "common"})
    
    # Evento critico de seguranca
    score2 = engine.evaluate({"financial_impact": 0, "urgency": 10, "user_relevance": 10, "confidence": 10, "type": "security_alert"})
    
    assert score2 > score1
    assert score2 >= 1000  # Devido a regra fixa de security_alert

def test_strategic_planner():
    planner = StrategicPlanner()
    plan = planner.create_plan("Criar produto digital")
    
    assert len(plan) > 0
    assert "tarefa" in plan[0]
    assert "duracao_estimada" in plan[0]

def test_prediction_memory():
    memory = PredictionMemory()
    memory.record_prediction({"asset": "BTC", "expected_price": 100000})
    
    result = memory.evaluate_prediction("mock_id", 95000)
    assert "error_margin" in result
    assert result["model_adjusted"] is True
