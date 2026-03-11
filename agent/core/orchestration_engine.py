"""
Orchestration Engine - Módulo 11 (v6.2)
Cérebro central do sistema.
Coordena módulos, prioridades, eventos e regras de negócio.
"""
import logging
from typing import Any

try:
    from core.event_bus import GlobalEventBus
    from core.scheduler import PriorityScheduler
except ImportError:
    try:
        from agent.core.event_bus import GlobalEventBus
        from agent.core.scheduler import PriorityScheduler
    except ImportError:
        # Fallback para quando rodando de dentro da pasta core
        from event_bus import GlobalEventBus
        from scheduler import PriorityScheduler

logger = logging.getLogger(__name__)

class OrchestrationEngine:
    def __init__(self, event_bus: GlobalEventBus, decision_engine: Any = None):
        self.event_bus = event_bus
        self.scheduler = PriorityScheduler()
        self.decision_engine = decision_engine
        
        # Subscreve aos eventos que exigem processamento ou ação
        self.event_bus.subscribe("NEW_ACTION_REQUIRED", self.handle_action_required)
        
    def handle_action_required(self, data: dict):
        """
        Recebe um pedido de ação, avalia no decision engine e coloca na fila
        de execução baseada na prioridade.
        """
        if self.decision_engine:
            priority = self.decision_engine.evaluate(data)
        else:
            # Fallback se decision engine não estiver mockado ou pronto
            priority = data.get("priority", 10)
            
        self.scheduler.add_task(priority, data)
        logger.info(f"Tarefa enfileirada com prioridade {priority}: {data.get('type')}")
        
    def dispatch(self, task: dict):
        """
        Dispara a execução da tarefa publicando de volta no Event Bus
        para o Executor (Automation/Processor) específico que estiver ouvindo.
        """
        task_type = task.get("type")
        if not task_type:
            return
            
        dispatch_event = f"EXECUTE_{task_type.upper()}"
        logger.info(f"Despachando tarefa: {dispatch_event}")
        self.event_bus.publish(dispatch_event, task)
        
    def run_cycle(self):
        """
        Consome a tarefa de maior prioridade atual.
        """
        if self.scheduler.has_tasks():
            task = self.scheduler.next_task()
            self.dispatch(task)
