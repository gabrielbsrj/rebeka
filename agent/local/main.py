# agent/local/main.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-24
# CHANGELOG: v2 — Simplificado: removido OfflineBuffer (banco único, sempre online)

import logging
import asyncio
import signal
import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
from memory.causal_bank import CausalBank
from local.sync_client import SyncClient
from local.privacy_auditor import PrivacyAuditor
from local.privacy_filter import PrivacyFilter
from local.capture import CaptureManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local_main")

async def main_loop():
    """
    Ciclo principal do Gêmeo Local.
    Sense (Capture) -> Filter -> Audit -> Sync
    """
    # 1. Setup
    bank = CausalBank(origin="local")
    auditor = PrivacyAuditor(bank)
    filter_ = PrivacyFilter()
    capture = CaptureManager()
    from local.executor_local import LocalExecutor
    executor = LocalExecutor()
    vps_url = os.getenv("VPS_WS_URL", "ws://localhost:8000/ws/sync")
    sync = SyncClient(vps_url=vps_url, executor=executor)
    executor.register_sync_client(sync)

    # 2. Iniciar Adaptador do WhatsApp
    from local.adapters.whatsapp_local_adapter import WhatsAppLocalAdapter
    whatsapp = WhatsAppLocalAdapter(executor)
    executor.register_whatsapp_adapter(whatsapp)
    asyncio.create_task(whatsapp.start())

    # 3. Iniciar Adaptador de Navegador (Playwright)
    from local.adapters.browser_adapter import BrowserAdapter
    browser_adapter = BrowserAdapter()
    asyncio.create_task(browser_adapter.start())

    # 4. Iniciar Sync Client em tarefa separada
    asyncio.create_task(sync.run_forever())

    last_signature = None
    last_sent_at = 0.0
    resend_window_min = os.getenv("REBEKA_CONTEXT_RESEND_MINUTES", "10")
    try:
        resend_window_min = int(resend_window_min)
    except ValueError:
        resend_window_min = 10

    def _infer_domain_and_relevance(payload: Dict[str, Any]) -> tuple[str, float]:
        text = " ".join(
            str(part or "")
            for part in (
                payload.get("active_app"),
                payload.get("window_title"),
                payload.get("context_category"),
            )
        ).lower()
        if any(term in text for term in ("whatsapp", "telegram", "discord", "slack", "gmail", "outlook", "mail")):
            return "communication", 0.7
        if any(term in text for term in ("bank", "broker", "trading", "metatrader", "binance", "coin", "exchange")):
            return "finance", 0.8
        return "context", 0.35

    logger.info("Gêmeo Local em execução — Perspectiva Íntima")

    try:
        while True:
            # SENSE: Capturar contexto
            raw_context = capture.capture_active_window()
            
            # FILTER: Abstrair dados sensíveis
            abstracted_data = filter_.apply(raw_context, "screen_content")
            domain, relevance = _infer_domain_and_relevance(abstracted_data)
            abstracted_data.setdefault("domain", domain)
            abstracted_data.setdefault("relevance_score", relevance)
            if "title" not in abstracted_data:
                active_app = abstracted_data.get("active_app") or abstracted_data.get("app_name")
                abstracted_data["title"] = f"Contexto local: {active_app}" if active_app else "Contexto local abstrato"
            if "content" not in abstracted_data:
                abstracted_data["content"] = abstracted_data.get("context_category") or abstracted_data.get("window_title")
            
            # AUDIT: Registrar o que está saindo
            auditor.audit_outgoing("screen_content_abstraction", abstracted_data)
            
            # SYNC: Enviar à VPS
            signature_payload = json.dumps(abstracted_data, sort_keys=True, default=str)
            signature = hashlib.sha1(signature_payload.encode("utf-8")).hexdigest()[:16]
            now = time.time()
            if signature != last_signature or (now - last_sent_at) >= (resend_window_min * 60):
                payload = dict(abstracted_data)
                payload.setdefault("context_signature", signature)
                payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                await sync.send({
                    "type": "context_sync",
                    "priority": "normal",
                    "data": payload
                })
                last_signature = signature
                last_sent_at = now

            await asyncio.sleep(60)  # Intervalo de captura

    except asyncio.CancelledError:
        logger.info("Encerrando ciclo local...")
        sync.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass

