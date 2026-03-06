import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentRouter:
    """
    Decide qual executor é o melhor para uma tarefa específica.
    Pode usar roteamento baseado em regras fixas ou LLM para casos complexos.
    """
    
    # Mapeamento fixo inicial de especialidades
    DEFAULT_ROUTING = {
        "codigo_backend": "cursor_agent",
        "codigo_frontend": "windsurf_agent",
        "pesquisa_internet": "perplexity",
        "automacao_api": "n8n_workflow",
        "web_scraping_complexo": "make_scenario",
        "decisao_subjetiva": "usuario_humano",
        "texto_criativo": "claude_api",
        "analise_dados": "gpt4_api"
    }
    
    def __init__(self, causal_bank: Optional[Any] = None):
        """Inicializa o Router com acesso opcional ao banco de logs de delegação."""
        self.db = causal_bank

    def route_task(self, component: Dict[str, Any]) -> str:
        """
        Recebe um componente decomposto e retorna o ID do executor ideal.
        
        A orquestradora (Decomposer) já tentou sugerir um 'executor' no JSON.
        O Router valida essa sugestão contra as capacidades reais registradas
        e o log histórico de falhas/sucessos (DelegationLog).
        """
        suggested_executor = component.get("executor")
        task_name = component.get("nome", "").lower()
        
        logger.info(f"Roteando tarefa '{task_name}' (Sugerido: {suggested_executor})")
        
        # 1. Validação básica de sugestão
        if suggested_executor and self._is_executor_available(suggested_executor):
            # No futuro, aqui checamos o banco para ver se esse executor falhou muito nisso
            return suggested_executor
            
        # 2. Roteamento por heurística de palavras-chave
        if "backend" in task_name or "python" in task_name or "api" in task_name:
            return "cursor_agent"
        elif "frontend" in task_name or "react" in task_name or "css" in task_name:
            return "windsurf_agent"
        elif "pesquisar" in task_name or "resumo" in task_name:
            return "perplexity"
        elif "aprovar" in task_name or "decidir" in task_name:
            return "usuario_humano"
            
        # 3. Fallback seguro
        logger.warning(f"Executor não garantido para '{task_name}'. Rotacionando para humano.")
        return "usuario_humano"
        
    def _is_executor_available(self, executor_id: str) -> bool:
        """Verifica se o executor está online/configurado (Mock inicial)."""
        valid_executors = [
            "cursor_agent", "windsurf_agent", "claude_api", "gpt4_api", 
            "perplexity", "n8n_workflow", "make_scenario", "usuario_humano",
            "github_copilot", "colaborador_externo"
        ]
        return executor_id in valid_executors
