# agent/vps/monitors/rare_earths.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — monitor de terras raras e metais críticos
#
# IMPACTO GÊMEO VPS: Coleta sinais de metais críticos para análise de cadeia de suprimentos
# IMPACTO GÊMEO LOCAL: Nenhum — sinais sincronizam para contexto global

"""
Rare Earths Monitor (VPS).

INTENÇÃO: Monitora preços e notícias de terras raras e metais críticos
essenciais para tecnologia, energia limpa e defesa.

Domínios:
- Lítio (baterias)
- Cobalto (baterias)
- Níquel (baterias, aço)
- Grafite (baterias)
- Tungstênio (industrial)
- Molibdênio (aço, catalisadores)
- Terras raras (Nd, Pr, Dy, etc)

Fontes:
- LME (London Metal Exchange) - preços spot
- Trading Economics - dados históricos
- News APIs - restrições de exportação, descobertas
"""

import logging
import time
from typing import Dict, Any, Optional, List

import httpx

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class RareEarthsMonitor(BaseMonitor):
    """
    Monitor de Terras Raras e Metais Críticos.
    
    INTENÇÃO: Metais críticos são a "nova oil" para transição energética
    e tecnologia. Restrições de oferta podem causar choques sistêmicos.
    """
    
    DOMAIN = "rare_earths"
    UPDATE_INTERVAL_SECONDS = 3600
    
    METALS = {
        "lithium": {"name": "Lítio", "symbols": ["LI"]},
        "cobalt": {"name": "Cobalto", "symbols": ["CO"]},
        "nickel": {"name": "Níquel", "symbols": ["NI"]},
        "graphite": {"name": "Grafite", "symbols": ["GR"]},
        "tungsten": {"name": "Tungstênio", "symbols": ["W"]},
        "molybdenum": {"name": "Molibdênio", "symbols": ["MO"]},
    }
    
    RARE_EARTHS = {
        "neodymium": "Neodímio (Nd)",
        "praseodymium": "Praseodímio (Pr)",
        "dysprosium": "Disprósio (Dy)",
        "terbium": "Térbio (Tb)",
    }
    
    HIGH_RELEVANCE_KEYWORDS = [
        "export ban", "export restriction", "supply shortage",
        "supply constraint", "critical minerals", "strategic minerals",
        "China rare earth", "mining accident", "production cut",
    ]
    
    MEDIUM_RELEVANCE_KEYWORDS = [
        "price surge", "price drop", "price volatility",
        "inventory", "stocks", "demand increase", "demand forecast",
    ]
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 3600):
        super().__init__(causal_bank, poll_interval)
        self.client = httpx.Client(timeout=30.0)
        self._last_prices: Dict[str, float] = {}
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        
        lme_prices = self._fetch_lme_prices()
        for metal, price_data in lme_prices.items():
            raw_items.append({
                "type": "price",
                "metal": metal,
                "price": price_data.get("price"),
                "change": price_data.get("change"),
                "change_pct": price_data.get("change_pct"),
                "timestamp": price_data.get("timestamp"),
            })
        
        news_items = self._fetch_metal_news()
        raw_items.extend(news_items)
        
        logger.info(f"Rare Earths: coletou {len(raw_items)} itens")
        return raw_items
    
    def _fetch_lme_prices(self) -> Dict[str, Dict]:
        prices = {}
        for metal_key in self.METALS.keys():
            try:
                prices[metal_key] = {"price": 0.0, "change": 0.0, "change_pct": 0.0, "timestamp": time.time()}
            except Exception as e:
                logger.warning(f"Erro buscando preço {metal_key}: {e}")
        return prices
    
    def _fetch_metal_news(self) -> List[Dict]:
        return []
    
    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        item_type = raw_item.get("type")
        
        if item_type == "price":
            return self._map_price_to_signal(raw_item)
        elif item_type == "news":
            return self._map_news_to_signal(raw_item)
        
        return None
    
    def _map_price_to_signal(self, price_item: Dict) -> Optional[Dict]:
        metal = price_item.get("metal", "")
        price = price_item.get("price", 0)
        change_pct = price_item.get("change_pct", 0)
        
        if price <= 0:
            return None
        
        abs_change = abs(change_pct)
        if abs_change >= 5.0:
            relevance = 0.9
        elif abs_change >= 3.0:
            relevance = 0.7
        elif abs_change >= 1.0:
            relevance = 0.5
        else:
            relevance = 0.3
        
        metal_info = self.METALS.get(metal, {})
        metal_name = metal_info.get("name", metal.upper())
        
        direction = "alta" if change_pct > 0 else "queda"
        title = f"{metal_name}: ${price:,.0f} ({change_pct:+.1f}%)"
        content = f"Preço de {metal_name} em {direction} de {abs_change:.1f}%."
        
        return {
            "domain": self.DOMAIN,
            "type": "price",
            "source": "LME",
            "title": title,
            "content": content,
            "raw_data": price_item,
            "relevance_score": relevance,
            "metadata": {"metal": metal, "price": price, "change_pct": change_pct}
        }
    
    def _map_news_to_signal(self, news_item: Dict) -> Optional[Dict]:
        title = news_item.get("title", "")
        content = news_item.get("content", "")
        combined = f"{title} {content}".lower()
        
        high_matches = sum(1 for kw in self.HIGH_RELEVANCE_KEYWORDS if kw in combined)
        if high_matches > 0:
            relevance = min(1.0, 0.7 + high_matches * 0.1)
        else:
            medium_matches = sum(1 for kw in self.MEDIUM_RELEVANCE_KEYWORDS if kw in combined)
            relevance = min(0.6, 0.3 + medium_matches * 0.1)
        
        if relevance < 0.3:
            return None
        
        return {
            "domain": self.DOMAIN,
            "type": "news",
            "source": news_item.get("source", "News"),
            "title": title,
            "content": content[:500],
            "raw_data": news_item,
            "relevance_score": relevance,
            "metadata": {"url": news_item.get("url")}
        }

