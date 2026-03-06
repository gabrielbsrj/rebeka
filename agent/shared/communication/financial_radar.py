# shared/communication/financial_radar.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 6 - Implementação inicial do Radar Financeiro

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.models import Base, FinancialAlert
from shared.communication.notifier import TelegramNotifier

logger = logging.getLogger(__name__)

# INVARIANTE v6: Rebeka nunca paga contas
class FinancialRadar:
    """
    Monitor financeiro proativo.
    Detecta, organiza e alerta sobre obrigações financeiras.
    NUNCA executa pagamentos.
    """
    
    ALERTAS_ANTECIPADOS = {
        "urgente": 1,    # 1 dia antes
        "atencao": 3,    # 3 dias antes  
        "aviso": 7,      # 7 dias antes
        "lembrete": 14   # 14 dias antes
    }
    
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url, echo=False)
        self._SessionFactory = sessionmaker(bind=self._engine)
        self.telegram = TelegramNotifier()
        
    def today(self) -> datetime:
        return datetime.now(timezone.utc)
        
    def classify_urgency(self, data_vencimento: datetime) -> str:
        dias = (data_vencimento.replace(tzinfo=timezone.utc) - self.today()).days
        if dias <= 1: return "urgente"
        if dias <= 3: return "atencao"
        if dias <= 7: return "aviso"
        return "lembrete"
        
    def generate_payment_calendar(self) -> List[Dict[str, Any]]:
        """Gera calendário de vencimentos dos próximos 30 dias."""
        trinta_dias_frente = self.today() + timedelta(days=30)
        
        with self._SessionFactory() as session:
            contas = session.query(FinancialAlert).filter(
                FinancialAlert.status == 'pendente',
                FinancialAlert.vencimento >= self.today(),
                FinancialAlert.vencimento <= trinta_dias_frente
            ).order_by(FinancialAlert.vencimento.asc()).all()
            
            return [{
                "id": c.id,
                "data": c.vencimento,
                "credor": c.creditor,
                "valor": c.valor,
                "banco": c.banco,
                "tipo": c.tipo,
                "dias_restantes": (c.vencimento.replace(tzinfo=timezone.utc) - self.today()).days,
                "urgencia": self.classify_urgency(c.vencimento),
                "alerta_enviado": c.alerta_enviado
            } for c in contas]
            
    def check_and_alert(self):
        """
        Roda periodicamente (ex: a cada hora).
        Verifica vencimentos e dispara alertas por Telegram se estiver na janela.
        """
        logger.info("[Financial Radar] Checando pendências financeiras...")
        calendar = self.generate_payment_calendar()
        
        # Enviar alertas para os que estão exatamente na janela e ainda não notificados para essa janela
        # Nota: Por simplificação, o design inicial apenas muda 'alerta_enviado' para True na primeira vez que atinge threshold <= 7
        
        with self._SessionFactory() as session:
            for conta in calendar:
                if conta["dias_restantes"] in self.ALERTAS_ANTECIPADOS.values() or conta["dias_restantes"] <= 1:
                    if not conta["alerta_enviado"] or conta["urgencia"] == "urgente":
                        
                        self.send_alert(f"""
💰 CONTA A VENCER — {conta['urgencia'].upper()}

Credor: {conta['credor']}
Banco: {conta['banco']} ({conta['tipo']})
Valor: R$ {conta['valor']:.2f}
Vencimento: {conta['data'].strftime('%d/%m/%Y')}
Dias restantes: {conta['dias_restantes']}

⚠️ REBEKA NÃO PAGA AUTOMATICAMENTE.
Esta é apenas uma informação para sua organização.
                        """)
                        
                        # Atualiza flag para evitar spam diário (só avisa 1x por conta, ou se for urgente continua avisando)
                        db_conta = session.query(FinancialAlert).get(conta["id"])
                        if db_conta:
                            db_conta.alerta_enviado = True
                            
            session.commit()
            
    def format_upcoming(self, days_start: int = 0, days_end: int = 7) -> str:
        """Formata string de contas para o range de dias."""
        inicio = self.today() + timedelta(days=days_start)
        fim = self.today() + timedelta(days=days_end)
        
        with self._SessionFactory() as session:
            contas = session.query(FinancialAlert).filter(
                FinancialAlert.status == 'pendente',
                FinancialAlert.vencimento >= inicio,
                FinancialAlert.vencimento <= fim
            ).order_by(FinancialAlert.vencimento.asc()).all()
            
            if not contas:
                return "Nenhuma conta pendente identificada."
                
            out = ""
            for c in contas:
                out += f"- {c.vencimento.strftime('%d/%m')} | {c.creditor}: R$ {c.valor:.2f}\n"
            return out
            
    def total_month(self) -> float:
        trinta_dias_frente = self.today() + timedelta(days=30)
        with self._SessionFactory() as session:
            contas = session.query(FinancialAlert).filter(
                FinancialAlert.status == 'pendente',
                FinancialAlert.vencimento >= self.today(),
                FinancialAlert.vencimento <= trinta_dias_frente
            ).all()
            return sum(c.valor for c in contas)
            
    def send_alert(self, msg: str):
        try:
            self.telegram.send(msg)
            logger.info(f"Alerta enviado: {msg[:30]}...")
        except Exception as e:
            logger.error(f"Erro ao enviar alerta pelo Telegram: {e}")
            
    def weekly_financial_summary(self) -> str:
        """Resumo semanal financeiro enviado todo domingo às 20h."""
        return f"""
📊 RESUMO FINANCEIRO SEMANAL

VENCENDO ESSA SEMANA:
{self.format_upcoming(days_start=0, days_end=7)}

VENCENDO PRÓXIMA SEMANA:
{self.format_upcoming(days_start=8, days_end=14)}

TOTAL ESTIMADO (30 dias): R$ {self.total_month():.2f}
        """

if __name__ == "__main__":
    # Teste de Inicialização
    logger.info("Testando Financial Radar...")
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "sqlite:///causal_bank_dev.db")
    
    radar = FinancialRadar(db_url)
    print(radar.weekly_financial_summary())
