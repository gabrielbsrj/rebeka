# shared/database/memory_core.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 6 - Implementação do Core de Memória e Morning Briefing

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

# Dependências locais da Rebeka
from memory.causal_bank import CausalBank
from interfaces.telegram_notifications import Notifier
from automation.financial_radar import FinancialRadar

logger = logging.getLogger(__name__)

# INVARIANTE v6: A memória atende o usuário, proativamente procurando
# soluções para problemas detectados em sessões anteriores.

class MemoryCore:
    """
    Motor principal que lê metadados das conversas salvos no CausalBank
    (tabela conversation_signals) para estruturar soluções proativas
    e emitir o Morning Briefing.
    """
    
    def __init__(self, db_url: str):
        self.bank = CausalBank(database_url=db_url)
        self.telegram = Notifier()
        self.radar = FinancialRadar(database_url=db_url)
        
    def ingest_session_metadata(self, session_data: Dict[str, Any]):
        """
        Recebe metadados de uma sessão recém finalizada com o usuário
        e salva via CausalBank. Usado pelo módulo Orquestrador.
        """
        logger.info("[Memory Core] Ingerindo metadados de sessão.")
        
        # Identifica se a sessão continha dores ou problemas explícitos
        problemas = session_data.get("problemas_citados", [])
        
        # Salva o signal no CausalBank usando o esquema existente de conversation signals
        signal_id = self.bank.insert_conversation_signal({
            "conversation_id": session_data.get("session_id", "manual"),
            "behavioral_patterns": {
                "problemas_ativos": problemas,
                "interesses": session_data.get("interesses", [])
            },
            "emotional_state_inferred": session_data.get("estado_emocional", "neutro"),
            "friction_potential": session_data.get("friccao", {})
        })
        
        if problemas:
            logger.info(f"Problemas detectados: {problemas}. Agendando busca proativa.")
            self.schedule_proactive_search(problemas)
            
        return signal_id
        
    def schedule_proactive_search(self, problemas: List[str]):
        """
        No futuro, chama o agente de web search autonomamente
        para buscar artigos, teses ou repositórios que resolvam
        as dores citadas.
        """
        pass
        
    def generate_morning_briefing(self) -> str:
        """
        Cruza informações de Metas de Crescimento (GrowthTarget),
        Contas a Pagar (FinancialRadar) e Resumo de Eventos,
        para disparar de manhã.
        """
        logger.info("[Memory Core] Gerando Morning Briefing...")
        
        # 1. Pega os Alvos de Crescimento Ativos
        targets = self.bank.get_active_growth_targets()
        focus_str = "Sem projetos definidos."
        if targets:
            titulos = [t.get("domain", "Geral").upper() for t in targets]
            focus_str = ", ".join(titulos)
            
        # 2. Financial Radar (Contas de hoje e do dia seguinte)
        contas_str = self.radar.format_upcoming(days_start=0, days_end=1)
        
        # O Memory Core age como o "amigo conselheiro"
        briefing = f"""
🌅 BOM DIA, GABRIEL. AQUI É A REBEKA.
(Data: {datetime.now().strftime('%d/%m/%Y')})

🎯 SEU FOCO ATUAL SEGUNDO NOSSO ÚLTIMO ALINHAMENTO:
{focus_str}

💸 RADAR FINANCEIRO (Hoje e Amanhã):
{contas_str}

🧠 RESUMO DA MEMÓRIA:
Lembre-se que você me pediu para monitorar ativamente tecnologias de automação financeira.
Estou rodando os jobs background silenciosamente.

Desejo um excelente dia produtivo! Se precisar, jogue a demanda aqui.
        """
        
        return briefing
        
    def dispatch_morning_briefing(self):
        """Envia pelo Telegram."""
        briefing = self.generate_morning_briefing()
        try:
            self.telegram.send(briefing)
            logger.info("Morning Briefing disparado via Telegram.")
        except Exception as e:
            logger.error(f"Erro ao disparar briefing: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "sqlite:///causal_bank_dev.db")
    
    logger.info("Testando Memory Core...")
    mc = MemoryCore(db_url)
    print(mc.generate_morning_briefing())


