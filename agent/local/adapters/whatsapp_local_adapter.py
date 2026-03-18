# agent/local/adapters/whatsapp_local_adapter.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19

import logging
import asyncio
import os
import pyautogui
from typing import Optional
from local.executor_local import LocalExecutor

logger = logging.getLogger(__name__)

class WhatsAppLocalAdapter:
    DEFAULT_TRANSPARENCY_TEMPLATE = (
        "Ola! Aqui e a Rebeka, assistente de IA de {user_name}. "
        "Vou avisar sobre sua mensagem agora."
    )
    """
    Adaptador Local do WhatsApp — Rebeka agindo no Desktop.
    """

    def __init__(self, executor: LocalExecutor):
        self.executor = executor
        self.running = False
        self._identified_contacts = set()
        self._trusted_contacts = self._load_trusted_contacts()

    async def start(self):
        """Inicia a monitoração do WhatsApp."""
        self.running = True
        logger.info("Adaptador Local do WhatsApp iniciado.")
        # asyncio.create_task(self.monitor_loop())

    async def stop(self):
        self.running = False

    async def send_message(self, contact_name: str, message: str):
        """
        Envia uma mensagem para um contato via WhatsApp Desktop.
        Assume que o WhatsApp está instalado e logado.
        """
        try:
            message_to_send, guardrail_applied, identification = self._apply_transparency_guardrail(
                contact_name, message
            )
            # 1. Abrir WhatsApp (Atalho ou via Start)
            # A lógica real usaria busca por imagem de ícone ou atalhos
            logger.info(f"Enviando mensagem para {contact_name} via WhatsApp Desktop...")
            
            # Atalho comum para abrir o 'Nova Conversa' ou busca (Ctrl+N ou Ctrl+F)
            self.executor.desktop_hotkey(['ctrl', 'n'])
            await asyncio.sleep(1)
            
            # Digitar nome do contato
            self.executor.desktop_type_text(contact_name, interval=0.1)
            await asyncio.sleep(1)
            
            # Enter para selecionar
            self.executor.desktop_hotkey(['enter'])
            await asyncio.sleep(1)
            
            # Digitar mensagem
            self.executor.desktop_type_text(message_to_send, interval=0.05)
            await asyncio.sleep(0.5)
            
            # Enter para enviar
            self.executor.desktop_hotkey(['enter'])
            
            return {
                "status": "success",
                "message": f"Mensagem enviada para {contact_name}",
                "contact_name": contact_name,
                "guardrail_applied": guardrail_applied,
                "identification_message": identification,
            }
        except Exception as e:
            logger.error(f"Erro no WhatsApp Local: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _load_trusted_contacts(self):
        raw = os.getenv("REBEKA_WHATSAPP_TRUSTED_CONTACTS", "")
        contacts = {name.strip().lower() for name in raw.split(",") if name.strip()}
        return contacts

    def _apply_transparency_guardrail(self, contact_name: str, message: str) -> tuple[str, bool, Optional[str]]:
        if os.getenv("REBEKA_WHATSAPP_TRANSPARENCY_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
            return message, False, None

        contact_key = (contact_name or "").strip().lower()
        if contact_key in self._trusted_contacts or contact_key in self._identified_contacts:
            return message, False, None

        user_name = os.getenv("USER_NAME") or os.getenv("REBEKA_USER_NAME") or "o usuario"
        template = os.getenv("REBEKA_WHATSAPP_TRANSPARENCY_TEMPLATE") or self.DEFAULT_TRANSPARENCY_TEMPLATE
        identification = template.format(user_name=user_name)
        self._identified_contacts.add(contact_key)
        if message:
            return f"{identification}\n\n{message}", True, identification
        return identification, True, identification

    async def monitor_loop(self):
        """
        Loop para detectar novas mensagens usando Screen Vision.
        Ele procura pelo ícone verde de notificação na tela.
        """
        while self.running:
            try:
                # O parâmetro confidence requer a biblioteca opencv-python
                # Procuramos o ícone de mensagem não lida na tela (bolinha verde do WhatsApp)
                # NOTA: Requer que o arquivo unread_icon.png exista na pasta config/vision/
                icon_path = os.path.join(os.getcwd(), "config", "vision", "whatsapp_unread.png")
                
                if os.path.exists(icon_path):
                    location = pyautogui.locateOnScreen(icon_path, confidence=0.8)
                    if location:
                        logger.info(f"Nova mensagem do WhatsApp detectada em: {location}")
                        
                        # 1. Clicar na nova mensagem para ler
                        pyautogui.click(pyautogui.center(location))
                        await asyncio.sleep(1)
                        
                        # 2. Em um fluxo avançado, tiraríamos printScreen da área de chat e OCR 
                        # ou usaríamos atalhos para copiar a última mensagem.
                        # Por ora, disparamos a percepção de que "há algo no WhatsApp".
                        await self.executor.notify_vps(
                            domain="communication",
                            source="whatsapp_local",
                            title="Nova Mensagem Direta",
                            content="Uma nova mensagem não lida foi aberta na tela. Verifique a captura de tela.",
                            relevance=0.8
                        )
                        
                        # Evitar loop de clique rápido
                        await asyncio.sleep(10)
            except Exception as e:
                # Caso PyAutoGUI falhe (ex: tela bloqueada, RDP minimizado, ou cv2 faltando)
                pass

            await asyncio.sleep(5)
