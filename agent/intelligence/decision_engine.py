"""
Decision Engine - Módulo 6 (v6.1)
Cérebro avaliador de prioridades.
Atribui score para eventos que entram no fluxo da Orquestradora.
"""
from typing import Dict, Any

class DecisionEngine:
    def evaluate(self, event_data: Dict[str, Any]) -> int:
        """
        Calcula o score de prioridade de um evento.
        Quanto maior o score, maior a urgência na fila da Rebeka.
        """
        score = 0
        
        # Ponderações heurísticas base baseadas no README/Arquitetura
        financial_impact = event_data.get("financial_impact", 0)
        urgency = event_data.get("urgency", 0)
        user_relevance = event_data.get("user_relevance", 0)
        confidence = event_data.get("confidence", 0)
        
        # Pesos definidos na especificação Módulo 6
        score += financial_impact * 3
        score += urgency * 2
        score += user_relevance * 5
        score += confidence * 2
        
        # Adicionar regras críticas fixas
        tipo = event_data.get("type", "")
        if tipo == "security_alert":
            score += 1000 # Prioridade absoluta (crítica)
        elif tipo in ["market_opportunity", "polymarket_trade"]:
            score += 500  # Prioridade alta
        elif tipo == "whatsapp_message":
            score += 100  # Prioridade média
        elif tipo == "system_health_check":
            score += 50   # Prioridade baixa / manutenção background
            
        return score
