# agent/vps/adapters/discord_adapter.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19

import logging
import asyncio
import os
import discord
from discord.ext import commands
from interfaces.chat_manager import ChatManager
from core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class DiscordAdapter(commands.Bot):
    """
    Adaptador do Discord — A Rebeka no Discord.
    """

    def __init__(self, chat_manager: ChatManager, token: str = None):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        
        self.chat_manager = chat_manager
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.registry = ToolRegistry()

    async def start_bot(self):
        """Inicia o bot do Discord."""
        if not self.token:
            logger.warning("DISCORD_BOT_TOKEN não configurado. Adaptador desativado.")
            return

        logger.info("Adaptador do Discord iniciado.")
        # O start() do discord.py é bloqueante, ideal rodar via create_task se integrado no main
        try:
            await self.start(self.token)
        except Exception as e:
            logger.error(f"Erro ao iniciar o Discord: {str(e)}")

    async def on_ready(self):
        logger.info(f"Bot logado como {self.user} (ID: {self.user.id})")

    async def on_message(self, message):
        """Processa mensagens recebidas."""
        # Evitar responder a si mesma
        if message.author == self.user:
            return

        # Ignorar comandos (deixando para o framework do discord.py se necessário)
        if message.content.startswith("!"):
            await self.process_commands(message)
            return

        user_name = message.author.name
        text = message.content
        
        logger.info(f"Discord [{user_name}]: {text}")

        async with message.channel.typing():
            # 1. Obter resposta do LLM
            tools = self.registry.get_tool_definitions()
            response_data = await self.chat_manager.get_response(text, tools=tools)

            if response_data["tool_calls"]:
                await message.reply("Um momento, estou processando isso... ⚙️")
                for tool_call in response_data["tool_calls"]:
                    await message.reply(f"Ação: {tool_call.function.name}")

            final_content = response_data["content"] or "Aqui está."
            await message.reply(final_content)

