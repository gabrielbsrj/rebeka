# agent/local/main.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-24
# CHANGELOG: v2 — Simplificado: removido OfflineBuffer (banco único, sempre online)

import logging
import asyncio
import signal
import os
from shared.database.causal_bank import CausalBank
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

    # 2. Iniciar Adaptador do WhatsApp
    from local.adapters.whatsapp_local_adapter import WhatsAppLocalAdapter
    whatsapp = WhatsAppLocalAdapter(executor)
    asyncio.create_task(whatsapp.start())

    # 3. Iniciar Adaptador de Navegador (Playwright)
    from local.adapters.browser_adapter import BrowserAdapter
    browser_adapter = BrowserAdapter()
    asyncio.create_task(browser_adapter.start())

    # 4. Iniciar Sync Client em tarefa separada
    asyncio.create_task(sync.run_forever())

    logger.info("Gêmeo Local em execução — Perspectiva Íntima")

    try:
        while True:
            # SENSE: Capturar contexto
            raw_context = capture.capture_active_window()
            
            # FILTER: Abstrair dados sensíveis
            abstracted_data = filter_.apply(raw_context, "screen_content")
            
            # AUDIT: Registrar o que está saindo
            auditor.audit_outgoing("screen_content_abstraction", abstracted_data)
            
            # SYNC: Enviar à VPS
            await sync.send({
                "type": "context_sync",
                "priority": "normal",
                "data": abstracted_data
            })

            await asyncio.sleep(60)  # Intervalo de captura

    except asyncio.CancelledError:
        logger.info("Encerrando ciclo local...")
        sync.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
