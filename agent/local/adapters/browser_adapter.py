# agent/local/adapters/browser_adapter.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v2 — Implementação de extração de mensagens via seletores CSS

import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BrowserAdapter:
    """
    Adaptador de Navegador — Rebeka acessando WebApps logados.
    """

    TELEGRAM_SELECTORS = {
        "message_list": ".messages-content .message-list .message",
        "message_text": ".message-text",
        "message_sender": ".from-name",
        "message_time": ".message-time",
        "chat_item": ".dialogs .dialog-item",
        "chat_title": ".dialog-title",
        "chat_preview": ".dialog-preview",
        "unread_badge": ".unread-badge",
    }

    def __init__(self, user_data_dir: str = None):
        self.user_data_dir = user_data_dir or os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Google/Chrome/User Data/Default'
        )
        self.browser_context = None
        self.playwright = None
        self.page = None

    async def start(self):
        """Inicia o Playwright."""
        logger.info(f"Iniciando adaptador de navegador com perfil: {self.user_data_dir}")
        self.playwright = await async_playwright().start()

    async def open_telegram_web(self) -> Dict[str, Any]:
        """Abre o Telegram Web e tenta ler mensagens."""
        try:
            browser = await self.playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=False,
                args=['--remote-debugging-port=9222'] 
            )
            
            self.page = await browser.new_page()
            await self.page.goto("https://web.telegram.org/k/")
            
            logger.info("Navegando no Telegram Web...")
            await self.page.wait_for_load_state("networkidle")
            
            messages = await self.extract_messages(count=10)
            
            return {
                "status": "success",
                "url": self.page.url,
                "messages": messages,
                "message_count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"Erro ao abrir navegador: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def extract_messages(self, count: int = 10, chat_selector: str = None) -> List[Dict[str, Any]]:
        """
        Extrai mensagens do Telegram Web via seletores CSS.
        
        Args:
            count: Número de mensagens para extrair
            chat_selector: Seletor específico do chat (opcional)
            
        Returns:
            Lista de mensagens extraídas
        """
        if not self.page:
            logger.warning("Página não iniciada. Chame open_telegram_web primeiro.")
            return []
            
        messages = []
        
        try:
            message_selector = chat_selector or self.TELEGRAM_SELECTORS["message_list"]
            await self.page.wait_for_selector(message_selector, timeout=5000)
            
            message_elements = await self.page.query_selector_all(message_selector)
            
            for elem in message_elements[:count]:
                try:
                    text_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["message_text"])
                    sender_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["message_sender"])
                    time_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["message_time"])
                    
                    message_data = {
                        "text": await text_elem.inner_text() if text_elem else "",
                        "sender": await sender_elem.inner_text() if sender_elem else "Unknown",
                        "time": await time_elem.inner_text() if time_elem else None,
                        "is_outgoing": "outgoing" in (await elem.get_attribute("class") or ""),
                    }
                    
                    if message_data["text"]:
                        messages.append(message_data)
                        
                except Exception as e:
                    logger.debug(f"Erro ao extrair mensagem: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro ao extrair mensagens: {e}")
            
        return messages

    async def get_unread_chats(self) -> List[Dict[str, Any]]:
        """
        Retorna chats com mensagens não lidas.
        """
        if not self.page:
            return []
            
        chats = []
        
        try:
            chat_selector = self.TELEGRAM_SELECTORS["chat_item"]
            await self.page.wait_for_selector(chat_selector, timeout=3000)
            
            chat_elements = await self.page.query_selector_all(chat_selector)
            
            for elem in chat_elements[:20]:
                try:
                    title_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["chat_title"])
                    preview_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["chat_preview"])
                    unread_elem = await elem.query_selector(self.TELEGRAM_SELECTORS["unread_badge"])
                    
                    chat_data = {
                        "title": await title_elem.inner_text() if title_elem else "Unknown",
                        "preview": await preview_elem.inner_text() if preview_elem else "",
                        "has_unread": unread_elem is not None,
                        "unread_count": (await unread_elem.inner_text()) if unread_elem else 0,
                    }
                    
                    if chat_data["has_unread"]:
                        chats.append(chat_data)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Erro ao buscar chats não lidos: {e}")
            
        return chats

    async def navigate_to_chat(self, chat_title: str) -> bool:
        """
        Navega para um chat específico pelo título.
        """
        if not self.page:
            return False
            
        try:
            search_input = await self.page.query_selector('input[type="search"], input[placeholder*="Search"]')
            if search_input:
                await search_input.fill(chat_title)
                await self.page.wait_for_timeout(500)
                
                first_result = await self.page.query_selector('.dialogs .dialog-item')
                if first_result:
                    await first_result.click()
                    await self.page.wait_for_timeout(1000)
                    return True
                    
        except Exception as e:
            logger.error(f"Erro ao navegar para chat {chat_title}: {e}")
            
        return False

    async def send_message(self, text: str) -> bool:
        """
        Envia mensagem no chat atual.
        """
        if not self.page:
            return False
            
        try:
            message_input = await self.page.query_selector('.message-input, input[type="text"]')
            if message_input:
                await message_input.fill(text)
                await self.page.wait_for_timeout(200)
                
                send_button = await self.page.query_selector('button.send-button, button[type="submit"]')
                if send_button:
                    await send_button.click()
                    return True
                    
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            
        return False

    async def take_screenshot(self, path: Optional[str] = None) -> Optional[bytes]:
        """
        Captura screenshot da página atual.
        """
        if not self.page:
            return None
            
        try:
            if path:
                await self.page.screenshot(path=path)
                return None
            else:
                return await self.page.screenshot()
        except Exception as e:
            logger.error(f"Erro ao capturar screenshot: {e}")
            return None

    async def stop(self):
        if self.playwright:
            await self.playwright.stop()
