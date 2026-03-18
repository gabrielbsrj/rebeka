# shared/communication/whatsapp_responder.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 6 - Implementação inicial do WhatsApp Responder via OCR/Web

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from interfaces.telegram_notifications import Notifier
# Presume a existência do parser web whatsapp criado anteriormente (na v5) ou adaptador semelhante
# from local.adapters.whatsapp_parser import WhatsAppWebParser

logger = logging.getLogger(__name__)

# INVARIANTE v6: Rebeka DEVE avisar o usuário ANTES de enviar mensagem definitiva
# exceto para contatos explicitamente marcados como "auto_reply" = True.

class WhatsAppResponder:
    """
    Atua como "Secretária Virtual" via WhatsApp.
    Classifica urgência, despacha notificação para o usuário (Telegram) e,
    dependendo da regra do contato, envia resposta padrão.
    """
    
    # Simulação do BD de contatos
    CONTACT_RULES = {
        "mãe": {
            "auto_reply": False,
            "custom_msg": "Oi! O Gabriel tá concentrado agora, mas já passo seu recado.",
            "urgency_boost": 2
        },
        "chefe": {
            "auto_reply": True,
            "custom_msg": "Olá, sou a assistente do Gabriel. Ele já vai ver sua mensagem.",
            "urgency_boost": 3
        },
        "default": {
            "auto_reply": False,
            "custom_msg": "Olá! No momento [USER] não pode responder.",
            "urgency_boost": 0
        }
    }
    
    def __init__(self, llm_provider=None):
        self.telegram = Notifier()
        self.llm = llm_provider
        
    def analyze_urgency(self, sender: str, message: str) -> Dict[str, Any]:
        """Classifica a mensagem quanto à urgência usando NLP/LLM."""
        
        # Heurística Básica
        kw_urgentes = ["urgente", "emergência", "rápido", "assalto", "hospital", "agora"]
        base_score = sum([1 for kw in kw_urgentes if kw in message.lower()])
        
        # Bônus pelo contato
        rule = self.CONTACT_RULES.get(sender.lower(), self.CONTACT_RULES["default"])
        score = base_score + rule["urgency_boost"]
        
        categoria = "normal"
        if score >= 3: categoria = "emergência"
        elif score >= 1: categoria = "urgente"
        
        return {
            "score": score,
            "categoria": categoria,
            "necessita_interrupcao": (categoria == "emergência")
        }
        
    def process_incoming_message(self, sender: str, message: str, phone: str = "") -> dict:
        """
        Recebe a notificação de nova mensagem do WhatsApp Parser.
        Retorna dicionário contendo o plano de ação.
        """
        logger.info(f"Processando WhatsApp de [{sender}]: {message[:30]}...")
        
        analysis = self.analyze_urgency(sender, message)
        rule = self.CONTACT_RULES.get(sender.lower(), self.CONTACT_RULES["default"])
        
        action_plan = {
            "notify_user": True,
            "interrupt_user": analysis["necessita_interrupcao"],
            "send_auto_reply": rule["auto_reply"],
            "reply_text": rule["custom_msg"] if rule["auto_reply"] else None,
            "categoria": analysis["categoria"]
        }
        
        # Envia para Telegram do usuário para que ele decida se interrompe o foco
        self.notify_user_on_telegram(sender, message, action_plan)
        
        return action_plan
        
    def notify_user_on_telegram(self, sender: str, message: str, action_plan: Dict[str, Any]):
        """Despacha a mensagem para o Telegram do usuário como um hub."""
        
        urgencia_str = action_plan['categoria'].upper()
        icone = "🔴" if urgencia_str == "EMERGÊNCIA" else ("🟡" if urgencia_str == "URGENTE" else "🟢")
        
        auto_replied = "Sim" if action_plan['send_auto_reply'] else "Não"
        
        msg = f"""
{icone} WHATSAPP: Mensagem de {sender} ({urgencia_str})

💬 "{message}"

🤖 Auto-Resposta enviada? {auto_replied}
{('- ' + action_plan['reply_text'] if action_plan['send_auto_reply'] else '')}

Responda esta mensagem aqui no Telegram para eu repassar ao WhatsApp.
        """
        try:
            self.telegram.send(msg)
            if action_plan["interrupt_user"]:
                # Se for urgência máxima, o Telegram Notifier poderia disparar alarme ou call no próprio Telegram.
                pass
        except Exception as e:
            logger.error(f"Erro ao notificar WhatsApp no Telegram: {e}")
            
    def execute_auto_reply(self, sender: str, action_plan: Dict[str, Any]):
        """
        Chama o cliente de automação web/app do WhatsApp para despachar a resposta,
        se autorizado pelas regras de contato.
        """
        if action_plan["send_auto_reply"] and action_plan["reply_text"]:
            logger.info(f"Enviando resposta no WHATSAPP para {sender}: {action_plan['reply_text']}")
            # whatsapp_driver.send_message(sender, action_plan["reply_text"])
            return True
        return False

if __name__ == "__main__":
    logger.info("Testando WhatsAppResponder...")
    responder = WhatsAppResponder()
    plan = responder.process_incoming_message(
        sender="Chefe",
        message="A reunião foi adiada para as 15h. Urgente ver o doc novo."
    )
    responder.execute_auto_reply("Chefe", plan)


