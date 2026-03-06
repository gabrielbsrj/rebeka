# agent/vps/monitors/energy.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — monitor de energia e commodities energéticas
#
# IMPACTO GÊMEO VPS: Coleta sinais de energia para análise de custos e oferta
# IMPACTO GÊMEO LOCAL: Nenhum — sinais sincronizam para contexto global

"""
Energy Monitor (VPS).

INTENÇÃO: Monitora o setor energético — petróleo, gás natural, nuclear,
renováveis e impacto em data centers.

Domínios:
- Petróleo bruto (WTI, Brent)
- Gás natural
- Nuclear (urânio, usinas)
- Renováveis (solar, eólica)
- GNL (LNG)
- Eletricidade / grid

Fontes:
- EIA (Energy Information Administration) - estoques semanais
- BNEF (Bloomberg New Energy Finance) - notícias
- IEA (International Energy Agency) - relatórios
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx

from shared.database.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class EnergyMonitor(BaseMonitor):
    """
    Monitor de Energia.
    
    INTENÇÃO: Energia é fundamental para economia e data centers.
    Variações de preço e oferta têm impacto sistêmico.
    """
    
    DOMAIN = "energy"
    UPDATE_INTERVAL_SECONDS = 1800
    
    COMMODITIES = {
        "crude_oil": {"name": "Petroleo Bruto WTI", "unit": "USD/bbl"},
        "brent": {"name": "Petroleo Brent", "unit": "USD/bbl"},
        "natural_gas": {"name": "Gas Natural", "unit": "USD/MMBtu"},
        "heating_oil": {"name": "Oleo Combustivel", "unit": "USD/gall"},
        "uranium": {"name": "Uranio", "unit": "USD/lb"},
        "ethanol": {"name": "Etanol", "unit": "USD/gall"},
    }
    
    HIGH_RELEVANCE_KEYWORDS = [
        "nuclear", "LNG shortage", "electricity crisis", "oil supply disruption",
        "OPEC cut", "pipeline", "refinery accident", "power outage",
        "grid failure", "data center", "energy emergency",
    ]
    
    MEDIUM_RELEVANCE_KEYWORDS = [
        "oil price", "natural gas price", "renewable", "solar", "wind",
        " EIA inventory", "EIA stocks", "production", "fracking",
        "electric vehicle", "battery", "energy transition",
    ]
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 1800):
        super().__init__(causal_bank, poll_interval)
        self.client = httpx.Client(timeout=30.0)
        self.eia_api_key = None
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        
        eia_data = self._fetch_eia_stocks()
        raw_items.extend(eia_data)
        
        price_data = self._fetch_energy_prices()
        raw_items.extend(price_data)
        
        news_items = self._fetch_energy_news()
        raw_items.extend(news_items)
        
        logger.info(f"Energy: coletou {len(raw_items)} itens")
        return raw_items
    
    def _fetch_eia_stocks(self) -> List[Dict]:
        items = []
        
        try:
            url = "https://api.eia.gov/v2/petroleum/pri/sum/data/"
            params = {
                "api_key": self.eia_api_key or "",
                "frequency": "weekly",
                "data[0]": "value",
                "facets[product][]": "EEX",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 5,
            }
            
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for record in data.get("response", {}).get("data", []):
                    items.append({
                        "type": "eia_stocks",
                        "product": record.get("product-name"),
                        "value": record.get("value"),
                        "unit": record.get("unit"),
                        "period": record.get("period"),
                    })
        except Exception as e:
            logger.warning(f"Erro buscando dados EIA: {e}")
        
        return items
    
    def _fetch_energy_prices(self) -> List[Dict]:
        items = []
        
        commodities_to_check = ["CL=F", "BZ=F", "NG=F", "UNG"]
        
        for symbol in commodities_to_check:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                params = {"interval": "1d", "range": "5d"}
                
                response = self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        meta = result[0].get("meta", {})
                        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
                        
                        if indicators.get("close"):
                            current_price = indicators["close"][-1]
                            prev_price = indicators["close"][-2] if len(indicators["close"]) > 1 else current_price
                            change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0
                            
                            commodity_type = symbol.split("=")[0] if "=" in symbol else symbol
                            
                            items.append({
                                "type": "price",
                                "symbol": symbol,
                                "commodity": commodity_type,
                                "price": current_price,
                                "change_pct": change_pct,
                                "timestamp": time.time(),
                            })
            except Exception as e:
                logger.warning(f"Erro buscando preço {symbol}: {e}")
        
        return items
    
    def _fetch_energy_news(self) -> List[Dict]:
        return []
    
    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        item_type = raw_item.get("type")
        
        if item_type == "price":
            return self._map_price_to_signal(raw_item)
        elif item_type == "eia_stocks":
            return self._map_eia_to_signal(raw_item)
        elif item_type == "news":
            return self._map_news_to_signal(raw_item)
        
        return None
    
    def _map_price_to_signal(self, price_item: Dict) -> Optional[Dict]:
        commodity = price_item.get("commodity", "")
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
        
        name_map = {
            "CL": "Petroleo WTI",
            "BZ": "Petroleo Brent", 
            "NG": "Gas Natural",
            "UNG": "Gas Natural ETN",
        }
        
        name = name_map.get(commodity, commodity)
        direction = "alta" if change_pct > 0 else "queda"
        title = f"{name}: ${price:.2f} ({change_pct:+.1f}%)"
        content = f"Preço de {name} em {direction} de {abs_change:.1f}%."
        
        return {
            "domain": self.DOMAIN,
            "type": "price",
            "source": "Yahoo Finance",
            "title": title,
            "content": content,
            "raw_data": price_item,
            "relevance_score": relevance,
            "metadata": {"commodity": commodity, "price": price, "change_pct": change_pct}
        }
    
    def _map_eia_to_signal(self, eia_item: Dict) -> Optional[Dict]:
        product = eia_item.get("product", "")
        value = eia_item.get("value")
        
        if value is None:
            return None
        
        relevance = 0.6
        
        title = f"EIA: {product} - {value:,.0f} barrels"
        content = f"Estoques de {product} segundo dados EIA."
        
        return {
            "domain": self.DOMAIN,
            "type": "eia_stocks",
            "source": "EIA",
            "title": title,
            "content": content,
            "raw_data": eia_item,
            "relevance_score": relevance,
            "metadata": {"product": product, "value": value}
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
