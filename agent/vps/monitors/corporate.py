# agent/vps/monitors/corporate.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — monitor corporativo de earnings e fundamentals
#
# IMPACTO GÊMEO VPS: Coleta sinais de earnings e fundamentals para análise financeira
# IMPACTO GÊMEO LOCAL: Nenhum — sinais sincronizam para contexto global

"""
Corporate Monitor (VPS).

INTENÇÃO: Monitora earnings, guidance e fundamentals de empresas relevantes.

Domínios:
- Earnings calendar
- Earnings surprises
- Guidance changes
- Dividend announcements
- Stock splits

Fontes:
- Yahoo Finance
- Alpha Vantage
- IEX Cloud
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class CorporateMonitor(BaseMonitor):
    """
    Monitor Corporativo.
    
    INTENÇÃO: Acompanha earnings e fundamentals para antecipar
    movimentos de mercado e validar hipóteses do Planejador.
    """
    
    DOMAIN = "corporate"
    UPDATE_INTERVAL_SECONDS = 3600
    
    TRACKED_TICKERS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
        "V", "UNH", "JNJ", "WMT", "PG", "MA", "HD", "DIS", "NFLX",
    ]
    
    HIGH_RELEVANCE_KEYWORDS = [
        "earnings beat", "revenue beat", "guidance raise", "guidance upgrade",
        "dividend increase", "stock split", "buyback", "acquisition",
    ]
    
    MEDIUM_RELEVANCE_KEYWORDS = [
        "earnings", "revenue", "guidance", "quarterly", "EPS",
        "dividend", "outlook", "forecast", "Q1", "Q2", "Q3", "Q4",
    ]
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 3600):
        super().__init__(causal_bank, poll_interval)
        self.client = httpx.Client(timeout=30.0)
        self.alpha_vantage_key = None
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        
        earnings = self._fetch_earnings_calendar()
        raw_items.extend(earnings)
        
        quotes = self._fetch_quotes()
        raw_items.extend(quotes)
        
        news = self._fetch_corporate_news()
        raw_items.extend(news)
        
        logger.info(f"Corporate: coletou {len(raw_items)} itens")
        return raw_items
    
    def _fetch_earnings_calendar(self) -> List[Dict]:
        items = []
        
        today = datetime.now()
        next_week = today + timedelta(days=7)
        
        for ticker in self.TRACKED_TICKERS[:10]:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/calendar/earnings"
                params = {
                    "symbol": ticker,
                    "period1": int(today.timestamp()),
                    "period2": int(next_week.timestamp()),
                }
                
                response = self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    earnings = data.get("calendar", {}).get("earnings", {}).get("earningsDate", [])
                    
                    for earning in earnings:
                        items.append({
                            "type": "earnings_calendar",
                            "ticker": ticker,
                            "date": earning.get("earningsDate"),
                            "eps_estimate": earning.get("epsEstimate"),
                        })
            except Exception as e:
                logger.warning(f"Erro buscando earnings para {ticker}: {e}")
        
        return items
    
    def _fetch_quotes(self) -> List[Dict]:
        items = []
        
        tickers_str = ",".join(self.TRACKED_TICKERS[:10])
        
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote"
            params = {"symbols": tickers_str}
            
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quoteResponse", {}).get("result", [])
                
                for quote in quotes:
                    items.append({
                        "type": "quote",
                        "ticker": quote.get("symbol"),
                        "price": quote.get("regularMarketPrice"),
                        "change_pct": quote.get("regularMarketChangePercent"),
                        "volume": quote.get("regularMarketVolume"),
                        "market_cap": quote.get("marketCap"),
                        "pe_ratio": quote.get("trailingPE"),
                    })
        except Exception as e:
            logger.warning(f"Erro buscando quotes: {e}")
        
        return items
    
    def _fetch_corporate_news(self) -> List[Dict]:
        return []
    
    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        item_type = raw_item.get("type")
        
        if item_type == "earnings_calendar":
            return self._map_earnings_to_signal(raw_item)
        elif item_type == "quote":
            return self._map_quote_to_signal(raw_item)
        elif item_type == "news":
            return self._map_news_to_signal(raw_item)
        
        return None
    
    def _map_earnings_to_signal(self, earning: Dict) -> Optional[Dict]:
        ticker = earning.get("ticker", "")
        date = earning.get("date", "")
        eps = earning.get("eps_estimate")
        
        if not ticker:
            return None
        
        title = f"Earnings: {ticker} - {date}"
        content = f"Previsão EPS: {eps}" if eps else f"Earnings em {date}"
        
        return {
            "domain": self.DOMAIN,
            "type": "earnings_calendar",
            "source": "Yahoo Finance",
            "title": title,
            "content": content,
            "raw_data": earning,
            "relevance_score": 0.6,
            "metadata": {
                "ticker": ticker,
                "date": date,
                "eps_estimate": eps,
            }
        }
    
    def _map_quote_to_signal(self, quote: Dict) -> Optional[Dict]:
        ticker = quote.get("ticker", "")
        price = quote.get("price", 0)
        change_pct = quote.get("change_pct", 0)
        
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
        
        direction = "alta" if change_pct > 0 else "queda"
        title = f"{ticker}: ${price:.2f} ({change_pct:+.1f}%)"
        content = f"Ação {ticker} em {direction} de {abs_change:.1f}%. Market Cap: ${quote.get('market_cap', 0):,.0f}"
        
        return {
            "domain": self.DOMAIN,
            "type": "quote",
            "source": "Yahoo Finance",
            "title": title,
            "content": content,
            "raw_data": quote,
            "relevance_score": relevance,
            "metadata": {
                "ticker": ticker,
                "price": price,
                "change_pct": change_pct,
                "volume": quote.get("volume"),
            }
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

