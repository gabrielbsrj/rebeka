import logging
from typing import Dict, Any, List, Optional
from memory.causal_bank import CausalBank

logger = logging.getLogger(__name__)

class ExecutionTracker:
    """
    Rastreia a execução pendente e o estado dos componentes no plano.
    
    INTENÇÃO: Manter o estado para que a orquestradora saiba o que 
    pode iniciar agora, o que aguarda dependência, e quando notificar o humano.
    """
    
    def __init__(self, db: CausalBank):
        self.db = db

    def initialize_plan(self, plan_data: Dict[str, Any]) -> str:
        """Salva o plano inicial no banco e retorna seu ID."""
        logger.info(f"Registrando novo plano de orquestração no banco...")
        plan_data["status"] = "draft"
        plan_id = self.db.insert_orchestration_plan(plan_data)
        return plan_id
        
    def start_execution(self, plan_id: str) -> None:
        """Marca o plano como em execução."""
        logger.info(f"Plano {plan_id} movido para 'executing'.")
        self.db.update_plan_status(plan_id, "executing")

    def queue_component(self, plan_id: str, component: Dict[str, Any], executor_id: str) -> str:
        """Enfileira ou despacha um componente para um executor."""
        task_data = {
            "plan_id": plan_id,
            "component_id": component.get("id"),
            "executor_id": executor_id,
            "instruction_sent": component.get("instrucao_para_executor", ""),
            "status": "pending"
        }
        
        task_id = self.db.insert_task_execution(task_data)
        logger.info(f"Tarefa {task_id} enfileirada para {executor_id}.")
        return task_id

    def mark_task_success(self, task_id: str, output: str) -> None:
        """Registra a conclusão com sucesso de uma tarefa."""
        logger.info(f"Tarefa {task_id} concluída.")
        self.db.update_task_execution(task_id, new_status="completed", output=output, success=True)
        
    def mark_task_failure(self, task_id: str, error_message: str) -> None:
        """Registra falha na execução."""
        logger.error(f"Tarefa {task_id} falhou: {error_message}")
        self.db.update_task_execution(task_id, new_status="failed", output=error_message, success=False)

    def check_plan_completion(self, plan_id: str, components: List[Dict]) -> bool:
        """
        No futuro: Verifica no banco de dados se todas as dependências 
        e tarefas do plano estão 'completed'.
        """
        # Simplificado para inicialização
        return False

