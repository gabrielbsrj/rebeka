# main.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — entry point do sistema

import os
import asyncio
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv

from shared.database.causal_bank import CausalBank
from shared.core.planner import Planner
from shared.core.evaluator import Evaluator
from shared.core.executor_base import PaperExecutor
from shared.core.security_phase1 import SecurityPhase1
from shared.core.orchestrator import Orchestrator
from shared.communication.notifier import Notifier

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log")
    ]
)
logger = logging.getLogger("main")

async def main():
    """Inicializa e roda o agente."""
    logger.info("=== REBEKA AGENT - INICIALIZANDO ===")
    
    # 0. Auditoria de conflitos de sistemas (FASE 1 v6.0)
    # Verifica conflitos antes de iniciar qualquer coisa
    try:
        from shared.audit.system_conflict_checker import SystemConflictChecker
        audit = SystemConflictChecker()
        audit_report = audit.audit_on_startup()
        logger.info(f"Auditoria de sistemas: Safe to start = {audit_report['safe_to_start']}")
        
        if audit_report['porta_conflitos']:
            for conflito in audit_report['porta_conflitos']:
                logger.warning(f"CONFLITO DETECTADO: {conflito}")
        
        if not audit_report['safe_to_start']:
            logger.error("⚠️ CONFLITOS CRÍTICOS DETECTADOS - Verifique manualmente antes de continuar")
            # Não bloqueia inicialização, mas alerta
    except Exception as e:
        logger.warning(f"Não foi possível executar auditoria de sistemas: {e}")
    
    # 1. Carregar ambiente e config
    load_dotenv()
    
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error("Arquivo config/config.yaml não encontrado!")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Inicializar componentes core
    db_url = os.getenv("DATABASE_URL", "sqlite:///causal_bank_dev.db")
    origin = os.getenv("TWIN_TYPE", "local") # "vps" ou "local"
    
    security = SecurityPhase1()
    bank = CausalBank(database_url=db_url, origin=origin)
    
    notifier = Notifier(config.get("notifications", {}))
    
    # Carregar modelos usando a nova lógica de config_loader
    from shared.core.config_loader import get_model_config
    planner_conf = get_model_config("planner")
    evaluator_conf = get_model_config("evaluator")

    planner = Planner(
        model=planner_conf["model"],
        api_key=planner_conf.get("api_key") or os.getenv("MOONSHOT_API_KEY"),
        api_base=planner_conf.get("api_base") or os.getenv("OPENAI_API_BASE"),
        personality_name=config.get("personality", {}).get("name", "Rebeka"),
        personality_style=config.get("personality", {}).get("style", "direto")
    )
    
    evaluator = Evaluator(
        model=evaluator_conf["model"],
        api_key=evaluator_conf.get("api_key") or os.getenv("MOONSHOT_API_KEY"),
        api_base=evaluator_conf.get("api_base") or os.getenv("OPENAI_API_BASE")
    )
    
    # Na fase 1, usamos PaperExecutor por padrão
    executor = PaperExecutor(origin=origin)

    # 3. Inicializar e rodar Orquestrador
    orchestrator = Orchestrator(
        bank=bank,
        planner=planner,
        evaluator=evaluator,
        executor=executor,
        security=security,
        notifier=notifier,
        interval_seconds=config.get("agent_settings", {}).get("loop_interval", 60)
    )

    logger.info(f"Agente inicializado como gêmeo: {origin.upper()}")
    
    try:
        await orchestrator.run_forever()
    except KeyboardInterrupt:
        orchestrator.stop()
        logger.info("Agente parado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro fatal na execução: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
