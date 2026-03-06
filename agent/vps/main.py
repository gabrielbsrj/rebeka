# agent/vps/main.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — ponto de entrada do Gêmeo VPS

import logging
import signal
import sys
import asyncio
from shared.database.causal_bank import CausalBank
from vps.sync_server import start_sync_server
from vps.monitors.social_media import SocialMediaMonitor

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vps_main")

def handle_exit(sig, frame):
    logger.info("Encerrando Gêmeo VPS...")
    sys.exit(0)

def main():
    """
    Inicializa o Gêmeo VPS.
    1. Conecta ao Banco de Causalidade.
    2. Inicia Monitores de Segundo Plano.
    3. Sobe o Sync Server (WebSocket).
    """
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    logger.info("Iniciando Gêmeo VPS — Perspectiva Global")

    # 1. Banco de Causalidade (Config'd por env)
    bank = CausalBank(origin="vps")

    # 2. Inicializar ChatManager para os adaptadores
    from shared.communication.chat_manager import ChatManager
    chat_manager = ChatManager()

    # 3. Iniciar Monitores
    from vps.monitors.report_monitor import ReportMonitor
    from vps.monitors.geopolitics import GeopoliticsMonitor
    from vps.monitors.macro import MacroMonitor as MacroNewsMonitor
    from vps.monitors.macro_monitor import MacroMonitor as MacroHifiMonitor
    from vps.monitors.financial_monitor import FinancialMonitor
    from vps.monitors.commodities import CommoditiesMonitor
    from vps.monitors.rare_earths import RareEarthsMonitor
    from vps.monitors.energy import EnergyMonitor
    from vps.monitors.innovation import InnovationMonitor
    from vps.monitors.corporate import CorporateMonitor
    from vps.services.proactive_insight import ProactiveInsightService
    from vps.monitors.survival_monitor import SurvivalMonitor
    
    monitors = [
        SocialMediaMonitor(causal_bank=bank, poll_interval=600),
        ReportMonitor(causal_bank=bank, chat_manager=chat_manager, poll_interval=3600),
        GeopoliticsMonitor(causal_bank=bank, poll_interval=3600),
        MacroNewsMonitor(causal_bank=bank, poll_interval=7200),
        MacroHifiMonitor(causal_bank=bank, poll_interval=7200),
        FinancialMonitor(causal_bank=bank, poll_interval=300),
        CommoditiesMonitor(causal_bank=bank, poll_interval=7200),
        RareEarthsMonitor(causal_bank=bank, poll_interval=3600),
        EnergyMonitor(causal_bank=bank, poll_interval=1800),
        InnovationMonitor(causal_bank=bank, poll_interval=7200),
        CorporateMonitor(causal_bank=bank, poll_interval=3600),
        SurvivalMonitor(causal_bank=bank)
    ]

    for monitor in monitors:
        monitor.start()
        logger.info(f"Monitor {monitor.__class__.__name__} em execução.")

    # 4. Iniciar Serviço de Insights Proativos e Evolução
    insight_service = ProactiveInsightService(bank, chat_manager)
    
    # Iniciar EvolutionService em background
    from shared.evolution.observer import Observer
    from shared.evolution.developer import Developer
    async def evolution_loop():
        observer = Observer(bank)
        developer = Developer()
        while True:
            logger.info("Iniciando ciclo de auto-análise evolutiva...")
            metrics = observer.analyze_performance()
            if metrics["violation_detected"] or metrics["systemic_error_detected"]:
                question = observer.question_reasoning(metrics)
                # No futuro, o Developer agiria aqui
                logger.info(f"Observer levantou questionamento: {question}")
            await asyncio.sleep(86400) # 24 horas

    # Garantir que temos um Loop de Eventos
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(insight_service.start())
    loop.create_task(evolution_loop())

    # 4. Iniciar Adaptadores Multi-Canal
    from vps.adapters.telegram_adapter import TelegramAdapter
    from vps.adapters.discord_adapter import DiscordAdapter
    
    telegram = TelegramAdapter(chat_manager)
    discord_bot = DiscordAdapter(chat_manager)
    
    loop.create_task(telegram.start())
    loop.create_task(discord_bot.start_bot())

    # 5. Iniciar Dashboard em thread separada
    from vps.dashboard.server import start_dashboard
    import threading
    threading.Thread(target=start_dashboard, kwargs={"port": 8086}, daemon=True).start()

    # 6. Iniciar Sync Server (Bloqueante)
    try:
        start_sync_server(host="0.0.0.0", port=8000, chat_manager=chat_manager)
    except Exception as e:
        logger.error(f"Falha fatal no Sync Server: {str(e)}")
    finally:
        for monitor in monitors:
            monitor.stop()
        # Parar adaptadores se necessário

if __name__ == "__main__":
    main()
