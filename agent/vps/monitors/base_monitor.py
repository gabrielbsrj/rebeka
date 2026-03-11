# agent/vps/monitors/base_monitor.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — classe base para todos os monitores

import abc
import logging
import time
from typing import Dict, Any, Optional, List
from threading import Thread, Event
from memory.causal_bank import CausalBank

logger = logging.getLogger(__name__)

class BaseMonitor(abc.ABC):
    """
    Classe base para monitores da VPS.
    
    INTENÇÃO: Cada monitor é um sensor especializado do mundo.
    Eles coletam dados brutos e os transformam em Sinais (Signals)
    no Banco de Causalidade.
    """

    def __init__(self, causal_bank: CausalBank, poll_interval: int = 300):
        """
        Args:
            causal_bank: Interface para o banco de dados.
            poll_interval: Intervalo entre coletas em segundos.
        """
        self.bank = causal_bank
        self.poll_interval = poll_interval
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    @abc.abstractmethod
    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Coleta dados da fonte externa. 
        Deve ser implementado pelas subclasses.
        """
        pass

    def process_and_store(self, raw_items: List[Dict[str, Any]]):
        """
        Transforma dados brutos em Signals e salva no banco.
        """
        for item in raw_items:
            try:
                signal_data = self.map_to_signal(item)
                if signal_data:
                    self.bank.insert_signal(signal_data)
            except Exception as e:
                logger.error(f"Erro ao processar item no monitor {self.__class__.__name__}: {str(e)}")

    @abc.abstractmethod
    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Mapeia um item bruto para o formato esperado pelo CausalBank.insert_signal.
        """
        pass

    def run(self):
        """Loop principal do monitor."""
        logger.info(f"Monitor {self.__class__.__name__} iniciado.")
        while not self._stop_event.is_set():
            try:
                data = self.fetch_data()
                if data:
                    self.process_and_store(data)
            except Exception as e:
                logger.error(f"Falha no ciclo do monitor {self.__class__.__name__}: {str(e)}")
            
            self._stop_event.wait(self.poll_interval)

    def start(self):
        """Inicia o monitor em uma thread separada."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self):
        """Pára o monitor."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        logger.info(f"Monitor {self.__class__.__name__} parado.")

