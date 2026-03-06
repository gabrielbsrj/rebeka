# agent/vps/monitors/commodities.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Criação inicial — monitor de commodities

"""
Monitor de Commodities (VPS).

INTENÇÃO: Monitorar OPEP, Petróleo, Ouro, Urânio.
"""

import logging
import time
from typing import Dict, Any, Optional, List
import feedparser

from shared.database.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class CommoditiesMonitor(BaseMonitor):
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 7200):
        super().__init__(causal_bank, poll_interval)
        
        self.rss_feeds = [
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000115", # CNBC Commodities
            "https://www.oilandgas360.com/feed/"
        ]
        
        self.commodities_keywords = [
            'oil', 'brent', 'wti', 'crude', 'gas', 'gold', 'uranium', 'copper',
            'opec', 'wheat', 'corn', 'soybeans'
        ]

    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        logger.info("Buscando dados de commodities...")
        
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
                logger.error(f"Erro lendo feed commodities {feed_url}: {e}")
                
        return raw_items

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrai sinal apenas se contiver commodities.
        """
        content = f"{raw_item.get('title', '')} {raw_item.get('summary', '')}".lower()
        
        matched_keywords = [kw for kw in self.commodities_keywords if kw in content]
        
        if not matched_keywords:
            return None
            
        relevance = min(1.0, len(matched_keywords) * 0.25)
        
        return {
            "domain": "commodities",
            "type": "commodity_news",
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
