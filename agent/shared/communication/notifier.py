# shared/communication/notifier.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial

"""
Notifier — Sistema de notificações multi-canal.

INTENÇÃO: O agente se comunica com o usuário via o canal preferido.
Respeita horários, urgência e preferências de frequência.

INVARIANTE: Toda notificação passa por verificação de confiança calibrada.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Canal de notificação abstrato."""

    @abstractmethod
    def send(self, message: str, priority: str = "normal") -> bool:
        """Envia mensagem pelo canal."""
        ...


class TelegramChannel(NotificationChannel):
    """Canal Telegram via Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id

    def send(self, message: str, priority: str = "normal") -> bool:
        """Envia mensagem via Telegram Bot."""
        import httpx
        try:
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            response = httpx.post(url, json={
                "chat_id": self._chat_id,
                "text": message,
                "parse_mode": "Markdown",
            })
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Falha ao enviar Telegram: {e}")
            return False


class ConsoleChannel(NotificationChannel):
    """Canal de console para desenvolvimento."""

    def send(self, message: str, priority: str = "normal") -> bool:
        prefix = "🔴" if priority == "critical" else "🔵" if priority == "high" else "⚪"
        print(f"\n{prefix} NOTIFICAÇÃO [{priority.upper()}]:\n{message}\n")
        return True


class Notifier:
    """
    Sistema de notificações com filtro de confiança.

    INTENÇÃO: O agente só notifica quando tem algo relevante a dizer.
    Notificações sem substância destroem confiança.
    """

    def __init__(self, channel: Optional[NotificationChannel] = None):
        self._channel = channel or ConsoleChannel()
        self._notification_log: List[Dict] = []

    def notify(
        self,
        title: str,
        message: str,
        priority: str = "normal",
        confidence: float = 0.0,
        min_confidence_to_send: float = 0.0,
    ) -> bool:
        """
        Envia notificação se a confiança for suficiente.

        INTENÇÃO: Respeita o tempo do usuário. Só notifica quando
        a informação é relevante e a confiança é calibrada.
        """
        if confidence < min_confidence_to_send:
            logger.debug(
                f"Notificação suprimida — confiança {confidence:.2f} "
                f"< mínimo {min_confidence_to_send:.2f}"
            )
            return False

        full_message = f"**{title}**\n\n{message}"
        if confidence > 0:
            full_message += f"\n\n_Confiança: {confidence:.0%}_"

        sent = self._channel.send(full_message, priority)

        self._notification_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "priority": priority,
            "confidence": confidence,
            "sent": sent,
        })

        return sent

    def get_notification_log(self) -> List[Dict]:
        """Retorna histórico de notificações."""
        return self._notification_log.copy()
