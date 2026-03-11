# agent/vps/adapters/telegram_adapter.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19

import logging
import asyncio
import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from interfaces.chat_manager import ChatManager
from core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class TelegramAdapter:
    """
    Adaptador do Telegram — A voz da Rebeka no mobile.
    """

    def __init__(self, chat_manager: ChatManager, token: str = None):
        self.chat_manager = chat_manager
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.registry = ToolRegistry()
        self.application = None

    async def start(self):
        """Inicia o bot do Telegram."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN não configurado. Adaptador desativado.")
            return

        self.application = Application.builder().token(self.token).build()

        # Handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("Adaptador do Telegram iniciado.")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def stop(self):
        """Para o bot do Telegram."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resposta ao comando /start."""
        await update.message.reply_text(
            "Oi! Eu sou a Rebeka. 😊\n"
            "Estou pronta para te ajudar por aqui também. O que você precisa?"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens recebidas."""
        user_id = update.effective_user.id
        text = update.message.text
        
        logger.info(f"Telegram [{user_id}]: {text}")

        # 1. Obter resposta do LLM
        tools = self.registry.get_tool_definitions()
        response_data = await self.chat_manager.get_response(text, tools=tools)

        # 2. Loop de Execução de Ferramentas (Simples via Local Sync)
        # Nota: Como a execução real acontece no gêmeo local, 
        # a VPS apenas solicita e aguarda o resultado via CausalBank/Sync.
        # Para esta versão inicial, focamos em texto.
        
        if response_data["tool_calls"]:
            await update.message.reply_text("Processando sua solicitação com ferramentas... ⚙️")
            # VPS não pode rodar ferramentas locais diretamente
            import json
            for tool_call in response_data["tool_calls"]:
                tool_name = tool_call.function.name
                await update.message.reply_text(f"Delegação de ferramenta encaminhada: {tool_name}")
                
                # Mock fallback (A v5.0 fará essa ponte real futuramente)
                deferred_msg = {
                    "status": "deferred",
                    "message": f"Aviso Técnico: A execução de ferramentas locais como `{tool_name}` não é permitida diretamente via interface remota (Telegram VPS). Um Plano de Orquestração deve ser gerado ou envie a solicitação no Gêmeo Local."
                }
                self.chat_manager.add_tool_result(tool_call.id, tool_name, json.dumps(deferred_msg))

            # Após execução, pegar síntese final do LLM
            response_data = await self.chat_manager.get_response(user_message=None, tools=tools)

        final_content = response_data["content"] or "Processamento concluído com sucesso."
        await update.message.reply_text(final_content)

