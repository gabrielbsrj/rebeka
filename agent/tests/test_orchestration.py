import pytest
from unittest.mock import Mock, AsyncMock
from shared.orchestration.agent_router import AgentRouter
from shared.orchestration.idea_decomposer import IdeaDecomposer

def test_agent_router_heuristics():
    """Testa se o router consegue rotear baseado no nome da tarefa."""
    router = AgentRouter()
    
    # Tarefa de backend
    comp1 = {"nome": "Criar API em python para o banco de dados"}
    assert router.route_task(comp1) == "cursor_agent"
    
    # Tarefa de frontend
    comp2 = {"nome": "Fazer os estilos CSS do dashboard e React"}
    assert router.route_task(comp2) == "windsurf_agent"
    
    # Tarefa de pesquisa
    comp3 = {"nome": "Pesquisar ultimas noticias sobre IA"}
    assert router.route_task(comp3) == "perplexity"

    # Tarefa subjetiva/decisao
    comp4 = {"nome": "Aprovar deploy para producao"}
    assert router.route_task(comp4) == "usuario_humano"
    
    # Fallback
    comp5 = {"nome": "Abastecer o carro"}
    assert router.route_task(comp5) == "usuario_humano"

def test_agent_router_suggestion_validation():
    """Testa se o router aceita uma sugestão válida do decomposer."""
    router = AgentRouter()
    
    # Sugestão válida
    comp1 = {
        "nome": "Tarefa generica",
        "executor": "n8n_workflow"
    }
    assert router.route_task(comp1) == "n8n_workflow"
    
    # Sugestão inválida
    comp2 = {
        "nome": "Tarefa generica",
        "executor": "agente_inventado"
    }
    # Deve cair no fallback ou na heurística da tarefa
    assert router.route_task(comp2) == "usuario_humano"

@pytest.mark.asyncio
async def test_idea_decomposer_parsing():
    """Testa se o decomposer extrai o JSON corretamente de uma resposta mockada do LLM."""
    mock_chat = Mock()
    mock_chat.get_response = AsyncMock(return_value={
        "content": '''```json
{
  "objetivo_central": "Testar API",
  "entregavel_final": "Um teste",
  "componentes": [
    {"id": "C1", "nome": "Setup", "executor": "cursor_agent"}
  ],
  "sequencia_sugerida": [],
  "incertezas": []
}
```'''
    })
    
    decomposer = IdeaDecomposer(chat_manager=mock_chat)
    result = await decomposer.decompose("Uma ideia qualquer")
    
    assert result["objetivo_central"] == "Testar API"
    assert len(result["componentes"]) == 1
    assert result["componentes"][0]["executor"] == "cursor_agent"
