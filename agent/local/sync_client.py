# agent/local/sync_client.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-24
# CHANGELOG: v2 — Simplificado: removido OfflineBuffer (ambos gêmeos sempre online)

import logging
import asyncio
import websockets
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SyncClient:
    """
    Cliente de sincronização do Gêmeo Local.
    
    INTENÇÃO: Conecta-se à VPS via WebSocket para trocar abstrações
    de contexto e receber convergências do Motor de Intenção.
    
    NOTA v2: Ambos os gêmeos estão sempre online e sincronizados.
    Se a conexão cair, reconecta automaticamente com retry.
    """

    def __init__(self, vps_url: str, executor: Any = None):
        self.vps_url = vps_url
        self._executor = executor
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._is_running = False

    async def connect(self):
        """Conecta à VPS via WebSocket."""
        logger.info(f"Conectando à VPS em {self.vps_url}...")
        try:
            async with websockets.connect(self.vps_url) as ws:
                self._websocket = ws
                logger.info("Conectado à VPS com sucesso.")
                
                # Loop de recepção
                async for message in ws:
                    data = json.loads(message)
                    logger.debug(f"Mensagem da VPS: {data.get('type')}")
                    
                    if data.get("type") == "tool_dispatch" and self._executor:
                        tool_name = data.get("tool_name")
                        arguments = data.get("arguments", {})
                        logger.info(f"Comando recebido da VPS: {tool_name}")
                        
                        asyncio.create_task(self._handle_tool_dispatch(tool_name, arguments))

        except Exception as e:
            logger.error(f"Falha na conexão com a VPS: {str(e)}")
            self._websocket = None

    async def _handle_tool_dispatch(self, tool_name: str, arguments: Dict[str, Any]):
        """Executa a ferramenta e devolve o resultado para a VPS."""
        try:
            result = await self._executor.execute(tool_name, arguments)
            await self.send({
                "type": "tool_result",
                "tool_name": tool_name,
                "status": "success",
                "result": result
            })
        except Exception as e:
            logger.error(f"Erro ao executar ferramenta remota: {e}")
            await self.send({
                "type": "tool_result",
                "tool_name": tool_name,
                "status": "error",
                "message": str(e)
            })

    async def send(self, message: Dict[str, Any]):
        """
        Envia mensagem para a VPS.
        Se não estiver conectado, loga warning (reconexão automática via run_forever).
        """
        if self._websocket:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                logger.warning(f"Falha ao enviar mensagem: {e}. Reconexão automática.")
                self._websocket = None
        else:
            logger.warning("Não conectado à VPS. Mensagem descartada, aguardando reconexão.")

    async def run_forever(self):
        self._is_running = True
        while self._is_running:
            await self.connect()
            logger.info("Reconectando à VPS em 5 segundos...")
            await asyncio.sleep(5)  # Retry delay

    def stop(self):
        self._is_running = False
