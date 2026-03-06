"""
Priority Task Scheduler - Módulo 13 (v6.2)
Fila de tarefas priorizada usando heapq.
"""
import heapq
from typing import Any, Dict

class PriorityScheduler:
    def __init__(self):
        self.queue = []
        self.counter = 0 # Desempate de prioridade mantendo a ordem de inserção
        
    def add_task(self, priority: int, task: Dict[str, Any]):
        """
        Adiciona uma tarefa à fila.
        Usa -priority para min-heap processar maiores primeiro.
        """
        heapq.heappush(self.queue, (-priority, self.counter, task))
        self.counter += 1
        
    def next_task(self) -> Dict[str, Any]:
        """Remove e retorna a próxima tarefa de maior prioridade."""
        if not self.queue:
            return None
        _, _, task = heapq.heappop(self.queue)
        return task
        
    def has_tasks(self) -> bool:
        return len(self.queue) > 0
