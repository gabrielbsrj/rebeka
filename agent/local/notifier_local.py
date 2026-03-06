# agent/local/notifier_local.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — notificações nativas locais

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LocalNotifier:
    """
    Notificador Nativo do Gêmeo Local.
    
    INTENÇÃO: Entrega notificações diretamente no dispositivo 
    onde o usuário está presente (PC/Celular).
    """

    def __init__(self, name: str = "Rebeka"):
        self.name = name

    def notify(self, title: str, message: str, urgency: str = "normal"):
        """
        Envia uma notificação nativa ao SO.
        """
        logger.info(f"NOTIFICAÇÃO [{urgency}]: {title} - {message}")
        
        try:
            # Placeholder para plyer ou win10toast
            # Ex: from plyer import notification; notification.notify(...)
            pass
        except Exception as e:
            logger.error(f"Falha ao enviar notificação nativa: {str(e)}")

    def alert_intervention_required(self, request_type: str, details: str):
        """
        Alerta que uma intervenção humana é necessária IMEDIATAMENTE.
        """
        self.notify(
            title="⚠️ Intervenção Necessária",
            message=f"Tipo: {request_type}. {details}",
            urgency="critical"
        )
