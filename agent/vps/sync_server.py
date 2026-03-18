import inspect
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Callable, Optional
import json
import hashlib
import os
from datetime import datetime, timezone

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
_causal_bank = None
_tool_result_consumers: List[Callable[[Dict[str, Any]], Any]] = []
_recent_context_signatures: Dict[str, datetime] = {}


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


def _infer_context_domain(payload: Dict[str, Any]) -> str:
    text_parts = [
        payload.get("active_app"),
        payload.get("app_name"),
        payload.get("context_category"),
        payload.get("title"),
    ]
    text = " ".join(str(part or "") for part in text_parts).lower()

    if any(term in text for term in ("whatsapp", "telegram", "discord", "slack", "gmail", "outlook", "mail")):
        return "communication"
    if any(term in text for term in ("bank", "trading", "broker", "wallet", "crypto", "exchange", "finance")):
        return "finance"
    return "context"


def _normalize_context_payload(payload: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    created_at = normalized.get("created_at") or message.get("created_at")
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    priority_label = str(message.get("priority") or normalized.get("priority") or "normal").strip().lower()
    priority_weight = {"low": 0.2, "normal": 0.5, "high": 0.8, "critical": 1.0}.get(priority_label, 0.5)

    relevance = normalized.get("relevance_score", normalized.get("relevance", 0.35))
    try:
        relevance = float(relevance)
    except (TypeError, ValueError):
        relevance = 0.35

    raw_signature = normalized.get("context_signature")
    if not raw_signature:
        signature_payload = json.dumps(normalized, sort_keys=True, default=str)
        raw_signature = hashlib.sha1(signature_payload.encode("utf-8")).hexdigest()[:16]

    source_id = normalized.get("source_id") or raw_signature
    priority_score = min(1.0, round((relevance * 0.7) + (priority_weight * 0.3), 3))

    normalized["created_at"] = created_at
    normalized["source_id"] = source_id
    normalized["priority_label"] = priority_label
    normalized["priority_score"] = priority_score
    normalized["relevance_score"] = relevance
    normalized["context_signature"] = raw_signature
    return normalized


def _build_context_signal(payload: Any, message: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"content": str(payload)}

    payload = _normalize_context_payload(payload, message)
    domain = payload.get("domain") or _infer_context_domain(payload)
    active_app = payload.get("active_app") or payload.get("app_name")
    title = payload.get("title") or (f"Contexto local: {active_app}" if active_app else "Contexto local abstrato")
    content = (
        payload.get("content")
        or payload.get("context_category")
        or payload.get("window_title")
        or active_app
        or "Contexto local abstrato."
    )
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("created_at", payload.get("created_at"))
    metadata.setdefault("source_id", payload.get("source_id"))
    metadata.setdefault("priority_score", payload.get("priority_score"))
    metadata.setdefault("priority_label", payload.get("priority_label"))
    metadata.setdefault("context_signature", payload.get("context_signature"))
    if payload.get("privacy_level"):
        metadata.setdefault("privacy_level", payload.get("privacy_level"))

    return {
        "domain": domain,
        "source": payload.get("source") or "local_context_sync",
        "title": title,
        "content": content,
        "raw_data": payload.get("raw_data", payload),
        "relevance_score": float(payload.get("relevance_score", 0.35)),
        "metadata": metadata or None,
    }


def _communication_is_relevant(payload: Dict[str, Any]) -> bool:
    threshold_raw = os.getenv("REBEKA_COMM_CONVERSATION_THRESHOLD", "0.65")
    try:
        threshold = float(threshold_raw)
    except ValueError:
        threshold = 0.65

    title = str(payload.get("title") or "")
    content = str(payload.get("content") or "")
    text = f"{title} {content}".lower()
    urgent = any(term in text for term in ("urg", "emerg", "crise", "falha", "agora", "asap"))
    priority_score = float(payload.get("priority_score") or 0.0)
    return urgent or priority_score >= threshold


def _should_accept_context_signature(signature: Optional[str], now: Optional[datetime] = None) -> bool:
    if not signature:
        return True

    now = now or datetime.now(timezone.utc)
    ttl_raw = os.getenv("REBEKA_CONTEXT_DEDUP_TTL_SECONDS", "300")
    try:
        ttl_seconds = int(ttl_raw)
    except ValueError:
        ttl_seconds = 300

    last_seen = _recent_context_signatures.get(signature)
    if last_seen and (now - last_seen).total_seconds() < ttl_seconds:
        return False

    _recent_context_signatures[signature] = now
    expired = [
        sig for sig, ts in _recent_context_signatures.items()
        if (now - ts).total_seconds() > ttl_seconds
    ]
    for sig in expired:
        _recent_context_signatures.pop(sig, None)
    return True


def _build_conversation_signal(payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "")
    content = str(payload.get("content") or "")
    text = f"{title} {content}".lower()
    urgent = any(term in text for term in ("urg", "emerg", "crise", "falha", "agora", "asap"))
    emotional_state = "alerta" if urgent else "neutro"
    summary = content.strip() or title.strip()
    summary = " ".join(summary.split())[:160]

    values = []
    if urgent:
        values.append("seguranca")
        values.append("estabilidade")
    if any(term in text for term in ("finance", "bank", "pagamento", "pix", "boleto")):
        values.append("controle")
        values.append("responsabilidade")
    if any(term in text for term in ("trabalho", "cliente", "projeto", "prazo")):
        values.append("confiabilidade")
        values.append("reputacao")
    if any(term in text for term in ("familia", "saude", "pessoal")):
        values.append("cuidado")
        values.append("bem_estar")

    friction = None
    if urgent or float(payload.get("priority_score") or 0.0) >= 0.7:
        friction = {"communication": round(float(payload.get("priority_score") or 0.7), 2)}

    return {
        "conversation_id": payload.get("source_id"),
        "behavioral_patterns": {
            "problemas_ativos": [],
            "interesses": [],
        },
        "emotional_state_inferred": emotional_state,
        "emotional_confidence": 0.4 if urgent else 0.25,
        "external_events": {
            "source": "context_sync",
            "summary": summary or "Contexto local relevante.",
            "channel": payload.get("domain") or "communication",
            "created_at": payload.get("created_at"),
        },
        "values_revealed": list(dict.fromkeys(values)) or None,
        "friction_potential": friction,
    }


def _maybe_register_behavioral_pattern(conversation: Dict[str, Any]) -> None:
    if _causal_bank is None:
        return

    friction = conversation.get("friction_potential") or {}
    if not isinstance(friction, dict):
        return

    threshold_raw = os.getenv("REBEKA_COMM_PATTERN_SCORE_THRESHOLD", "0.7")
    try:
        threshold = float(threshold_raw)
    except ValueError:
        threshold = 0.7

    comm_score = float(friction.get("communication", 0.0))
    if comm_score < threshold:
        return

    min_count_raw = os.getenv("REBEKA_COMM_PATTERN_MIN_COUNT", "3")
    try:
        min_count = int(min_count_raw)
    except ValueError:
        min_count = 3

    try:
        recent = _causal_bank.get_recent_conversation_signals(days=3, limit=50)
        count = 0
        for signal in recent:
            signal_friction = signal.get("friction_potential") or {}
            if isinstance(signal_friction, dict) and float(signal_friction.get("communication", 0.0)) >= threshold:
                count += 1
        if count < min_count:
            return

        patterns = _causal_bank.get_behavioral_patterns(domain="communication", min_confidence=0.3)
        existing = next((p for p in patterns if p.get("type") == "communication_urgency"), None)
        evidence = {
            "source": "context_sync",
            "observations": count,
            "last_seen": conversation.get("external_events", {}).get("created_at"),
        }
        if existing:
            _causal_bank.append_behavioral_evidence(existing["id"], evidence)
        else:
            confidence = min(0.75, 0.45 + (0.05 * count))
            _causal_bank.insert_behavioral_pattern(
                {
                    "domain": "communication",
                    "pattern_type": "communication_urgency",
                    "description": "Pressao recorrente por resposta ou eventos urgentes em comunicacao.",
                    "confidence": confidence,
                    "confirmation_count": count,
                    "potentially_limiting": True,
                    "evidence": [evidence],
                }
            )
    except Exception as exc:
        logger.error(f"Erro ao registrar behavioral pattern: {exc}")


def _infer_growth_target_from_values(values: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    if not values:
        return None
    values_set = {str(v).strip().lower() for v in values if v}
    if {"controle", "responsabilidade"} & values_set:
        return {
            "domain": "finance",
            "current_state_declared": "pressao por controle financeiro",
            "desired_future_state": "rotina financeira previsivel e automatizada",
        }
    if {"confiabilidade", "reputacao"} & values_set:
        return {
            "domain": "growth",
            "current_state_declared": "carga de prazos e entregas",
            "desired_future_state": "execucao consistente com previsibilidade",
        }
    if {"cuidado", "bem_estar"} & values_set:
        return {
            "domain": "user",
            "current_state_declared": "energia emocional sob demanda",
            "desired_future_state": "rotina com mais estabilidade e recuperacao",
        }
    return None


def _upsert_growth_target(target: Dict[str, Any]) -> Optional[str]:
    if _causal_bank is None or not target:
        return None
    domain = target.get("domain")
    if not domain:
        return None
    try:
        existing = _causal_bank.get_active_growth_targets(domain=domain)
        if existing:
            return None
        return _causal_bank.insert_growth_target(target)
    except Exception as exc:
        logger.error(f"Erro ao registrar growth_target: {exc}")
        return None

async def _handle_context_sync(message: Dict[str, Any]) -> None:
    if _causal_bank is None:
        logger.warning("context_sync recebido sem causal_bank registrado.")
        return

    try:
        payload = _normalize_context_payload(message.get("data") or {}, message)
        signature = payload.get("context_signature")
        if not _should_accept_context_signature(signature):
            logger.debug("context_sync ignorado por dedupe no sync_server.")
            return
        signal = _build_context_signal(payload, message)
        _causal_bank.insert_signal(signal)
        domain = payload.get("domain") or _infer_context_domain(payload)
        if domain == "communication" and _communication_is_relevant(payload):
            conversation = _build_conversation_signal(payload)
            _causal_bank.insert_conversation_signal(conversation)
            _maybe_register_behavioral_pattern(conversation)
            growth_from_values = _infer_growth_target_from_values(conversation.get("values_revealed"))
            if growth_from_values:
                _upsert_growth_target(growth_from_values)
        logger.info("context_sync persistido no CausalBank.")
    except Exception as exc:
        logger.error(f"Erro ao persistir context_sync: {exc}")


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
            elif msg_type == "context_sync":
                await _handle_context_sync(message)

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
    causal_bank=None,
    tool_result_consumers: List[Callable[[Dict[str, Any]], Any]] = None,
):
    import uvicorn

    global _chat_manager, _causal_bank
    _chat_manager = chat_manager
    _causal_bank = causal_bank

    if tool_result_consumers:
        for consumer in tool_result_consumers:
            register_tool_result_consumer(consumer)

    logger.info(f"Iniciando Sync Server em {host}:{port}")
    uvicorn.run(app, host=host, port=port)
