# agent/vps/monitors/geopolitics.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Criação inicial — monitor geopolítico baseado em RSS

"""
Monitor Geopolítico (VPS).

INTENÇÃO: Lê feeds RSS de notícias globais (Reuters, Al Jazeera, etc.)
e extrai sinais usando heurísticas baseadas em palavras-chave para detectar
tensões, guerras ou sanções.
"""

import logging
import time
from typing import Dict, Any, Optional, List
import feedparser

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class GeopoliticsMonitor(BaseMonitor):
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 3600):
        # Default de 1h para RSS
        super().__init__(causal_bank, poll_interval)
        self.rss_feeds = [
            "http://feeds.bbci.co.uk/news/world/rss.xml",
            "https://www.aljazeera.com/xml/rss/all.xml",
            # Adicione mais conforme necessário
        ]
        
        # Palavras-chave simples de detecção (Poderia ser um pequeno LLM aqui)
        self.tension_keywords = [
            'war', 'strike', 'missile', 'sanction', 'tension', 'nuclear',
            'troops', 'invasion', 'conflict', 'ceasefire', 'treaty'
        ]

    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        logger.info("Buscando feeds geopolíticos...")
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]: # Top 10 recentes
                    raw_items.append({
                        "source": feed_url,
                        "title": entry.title,
                        "link": entry.link,
                        "published": getattr(entry, 'published', str(time.time())),
                        "summary": getattr(entry, 'summary', '')
                    })
            except Exception as e:
                logger.error(f"Erro lendo feed {feed_url}: {e}")
                
        return raw_items

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrai sinal apenas se contiver palavras-chave de tensão.
        """
        content = f"{raw_item.get('title', '')} {raw_item.get('summary', '')}".lower()
        
        # Heurística Sense-before-act simplificada
        matched_keywords = [kw for kw in self.tension_keywords if kw in content]
        
        if not matched_keywords:
            return None # Não é um sinal geopolítico relevante para o agente
            
        relevance = min(1.0, len(matched_keywords) * 0.2) # Max 1.0
        
        return {
            "domain": "geopolitics",
            "type": "news",
            "source": raw_item["source"],
            "title": raw_item["title"],
            "content": content[:500],
            "extracted_entities": matched_keywords,
            "relevance_score": relevance,
            "metadata": {
                "link": raw_item["link"],
                "published": raw_item["published"]
            }
        }

