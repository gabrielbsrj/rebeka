# agent/vps/monitors/report_monitor.py
# VERSION: 1.1.0
# LAST_MODIFIED: 2026-02-19

import logging
import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional, List
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class ReportMonitor(BaseMonitor):
    """
    Monitor de Relatórios Proativos — Notícias e Tempo.
    """

    def __init__(self, causal_bank, chat_manager, poll_interval=3600):
        super().__init__(causal_bank, poll_interval)
        self.chat_manager = chat_manager
        self.last_report_date = None

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Implementação síncrona exigida pela BaseMonitor.
        Como o Monitor roda em Thread separada, podemos usar um loop de eventos local 
        ou simplificar para chamadas síncronas se necessário.
        """
        now = datetime.now()
        if self.last_report_date != now.date():
            logger.info("Iniciando coleta de dados para relatório diário...")
            
            # Usando loop momentâneo para as partes assíncronas
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                news = loop.run_until_complete(self._fetch_news())
                weather = loop.run_until_complete(self._fetch_weather())
                
                report_content = f"### 📊 Relatório Diário - {now.strftime('%d/%m/%Y')}\n\n"
                report_content += f"**🌤️ Tempo:** {weather}\n\n"
                report_content += f"**📰 Principais Notícias de Mercado:**\n{news}\n"
                
                self.last_report_date = now.date()
                return [{"type": "daily_report", "content": report_content}]
            finally:
                loop.close()
        
        return []

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mapeia o relatório para o formato do CausalBank."""
        return {
            "source": "report_monitor",
            "domain": "macro", # Domínio padrão para relatórios
            "title": raw_item["type"],
            "content": raw_item["content"],
            "relevance_score": 0.5,
            "metadata": {"raw_type": raw_item["type"]}
        }

    async def _fetch_news(self):
        """Busca notícias de um feed RSS de finanças."""
        try:
            url = "https://www.infomoney.com.br/mercados/feed/"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                root = ET.fromstring(response.text)
                
                titles = []
                for item in root.findall('./channel/item')[:5]:
                    title = item.find('title').text
                    titles.append(f"- {title}")
                
                return "\n".join(titles) if titles else "Nenhuma notícia encontrada."
        except Exception as e:
            return f"Erro ao buscar notícias: {str(e)}"

    async def _fetch_weather(self):
        """Busca o tempo (exemplo simplificado)."""
        return "Céu limpo, 26°C (São Paulo)"
