import inspect
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Callable
import json

logger = logging.getLogger(__name__)

app = FastAPI(title="Rebeka VPS Sync Server")


class ConnectionManager:
    """Gerencia conexões WebSocket (principalmente com o gêmeo local)."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Gêmeo Local conectado ao Sync Server.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Gêmeo Local desconectado do Sync Server.")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

    async def dispatch_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Despacha uma ferramenta para todos os gêmeos locais conectados."""
        message = {
            "type": "tool_dispatch",
            "tool_name": tool_name,
            "arguments": arguments,
        }
        await self.broadcast(message)


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"status": "online", "mode": "sync_server"}


_chat_manager = None
_tool_result_consumers: List[Callable[[Dict[str, Any]], Any]] = []


def register_tool_result_consumer(consumer: Callable[[Dict[str, Any]], Any]) -> None:
    if consumer not in _tool_result_consumers:
        _tool_result_consumers.append(consumer)


def clear_tool_result_consumers() -> None:
    _tool_result_consumers.clear()


async def notify_tool_result_consumers(message: Dict[str, Any]) -> None:
    for consumer in list(_tool_result_consumers):
        try:
            result = consumer(message)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            logger.error(f"Erro ao notificar consumidor de tool_result: {exc}")


@app.websocket("/ws/sync")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")
            logger.info(f"Mensagem recebida do gêmeo local: {msg_type}")

            if msg_type == "tool_result":
                tool_name = message.get("tool_name")
                status = message.get("status")
                result = message.get("result", {})

                if tool_name == "perplexity_search" and status == "success":
                    answer = result.get("full_answer", "Relatório vazio.")
                    query = result.get("query", "Pesquisa")

                    if _chat_manager:
                        report_msg = f"📊 **Relatório de Deep Research**\n\n**Tópico**: {query}\n\n---\n\n{answer}"
                        _chat_manager.push_insight(report_msg)
                        logger.info("Relatório de Perplexity postado no chat.")

                await notify_tool_result_consumers(message)

            await manager.send_personal_message(
                {"type": "sync_ack", "status": "received"},
                websocket,
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Erro na conexão WebSocket: {str(e)}")
        manager.disconnect(websocket)


def start_sync_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    chat_manager=None,
    tool_result_consumers: List[Callable[[Dict[str, Any]], Any]] = None,
):
    import uvicorn

    global _chat_manager
    _chat_manager = chat_manager

    if tool_result_consumers:
        for consumer in tool_result_consumers:
            register_tool_result_consumer(consumer)

    logger.info(f"Iniciando Sync Server em {host}:{port}")
    uvicorn.run(app, host=host, port=port)
