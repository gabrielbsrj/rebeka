# agent/main.py
# VERSION: 6.2.3 (Cognitive OS)
# LAST_MODIFIED: 2026-03-07
# CHANGELOG: Ajuste de assinaturas de __init__ para WhatsAppResponder e Notifier

import os
import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Garantir que o diretório 'agent' esteja no path para imports relativos funcionarem
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importações do Novo Core v6.2
try:
    from core.event_bus import GlobalEventBus
    from core.orchestration_engine import OrchestrationEngine
    from core.scheduler import PriorityScheduler
    from infrastructure.system_awareness import SystemAwareness
    from infrastructure.system_health_monitor import SystemHealthMonitor
    from intelligence.decision_engine import DecisionEngine
    from interfaces.telegram_notifications import Notifier, TelegramChannel
except ImportError:
    from agent.core.event_bus import GlobalEventBus
    from agent.core.orchestration_engine import OrchestrationEngine
    from agent.core.scheduler import PriorityScheduler
    from agent.infrastructure.system_awareness import SystemAwareness
    from agent.infrastructure.system_health_monitor import SystemHealthMonitor
    from agent.intelligence.decision_engine import DecisionEngine
    from agent.interfaces.telegram_notifications import Notifier, TelegramChannel

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent_v6.log")
    ]
)
logger = logging.getLogger("main")

async def main():
    """Entry point da Rebeka como SO Cognitivo."""
    logger.info("=== REBEKA COGNITIVE OS (v6.2) - INICIALIZANDO ===")
    
    # 0. Preparação
    load_dotenv()
    
    # 1. Inicializar Infraestrutura e Core
    event_bus = GlobalEventBus()
    decision_engine = DecisionEngine()
    orchestrator = OrchestrationEngine(event_bus, decision_engine)
    
    awareness = SystemAwareness()
    health_monitor = SystemHealthMonitor()
    
    # Configurar Notificador
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        channel = TelegramChannel(token, chat_id)
        notifier = Notifier(channel)
        logger.info("Notificador Telegram configurado.")
    else:
        notifier = Notifier() # Console fallback
        logger.info("Notificador configurado em modo Console (sem credenciais Telegram).")
    
    logger.info("Núcleo de orquestração e barramento de eventos prontos.")
    
    # 2. Inicializar Módulos de Automação e Memória
    try:
        from automation.financial_radar import FinancialRadar
        from automation.whatsapp_responder import WhatsAppResponder
        from memory.memory_core import MemoryCore
        from processors.opportunity_detector import OpportunityDetector
        from processors.email_manager import EmailManager
    except ImportError:
        from agent.automation.financial_radar import FinancialRadar
        from agent.automation.whatsapp_responder import WhatsAppResponder
        from agent.memory.memory_core import MemoryCore
        from agent.processors.opportunity_detector import OpportunityDetector
        from agent.processors.email_manager import EmailManager
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///causal_bank_dev.db")
    
    radar = FinancialRadar(db_url)
    whatsapp = WhatsAppResponder() # Removido user_name que não existe no __init__
    memory = MemoryCore(db_url)
    detector = OpportunityDetector()
    
    # EmailManager pode precisar de credenciais
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./config/gmail_credentials.json")
    try:
        email_mgr = EmailManager(creds_path)
    except:
        logger.warning(f"EmailManager não pôde ser iniciado com {creds_path}. Pulando.")
        email_mgr = None
    
    # Acoplar módulos ao barramento
    event_bus.subscribe("EXECUTE_FINANCIAL_CHECK", lambda d: radar.check_and_alert())
    event_bus.subscribe("WHATSAPP_MESSAGE_RECEIVED", lambda d: whatsapp.process_incoming_message(d.get('sender'), d.get('message')))
    event_bus.subscribe("NEW_CONVERSATION", lambda d: memory.ingest(d))
    event_bus.subscribe("GLOBAL_EVENT_DETECTED", lambda d: detector.analyze_event(d['event'], d.get('context', '')))
    
    logger.info(f"Módulos acoplados. Usando modelo: {os.getenv('MOONSHOT_API_KEY')[:5]}... (Kimi 2.5)")

    # 3. Loop Principal de Orquestração
    logger.info("Iniciando loop de orquestração cognitiva...")
    
    try:
        while True:
            if awareness.is_overloaded():
                logger.warning("Reduzindo carga.")
                await asyncio.sleep(2)
                continue
                
            health_monitor.check_services()
            orchestrator.run_cycle()
            await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        logger.info("Agente parado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro fatal na orquestração: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
