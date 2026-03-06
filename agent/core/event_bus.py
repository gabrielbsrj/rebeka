"""
Global Event Bus - Módulo 12 (v6.2)
Sistema Pub/Sub interno. Evita acoplamento direto entre as classes.
"""
from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class GlobalEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscrito em {event_type}: {callback.__name__}")
            
    def publish(self, event_type: str, data: Any):
        logger.info(f"Publicando evento: {event_type}")
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Erro no subscriber {callback.__name__} para evento {event_type}: {e}")
