# agent/vps/monitors/financial_monitor.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Criação inicial — monitor de mercado via yfinance

"""
Monitor Financeiro de Alta Fidelidade (VPS).

INTENÇÃO: Monitora ativos financeiros (Ações, Cripto, Moedas) buscando
dados estruturados (preço, volume, variação) para alimentar o Banco de Causalidade.
"""

import logging
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class FinancialMonitor(BaseMonitor):
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 300):
        # Default de 5 minutos para dados de mercado
        super().__init__(causal_bank, poll_interval)
        
        # Ativos de interesse inicial
        self.tickers = [
            "^GSPC",   # S&P 500
            "BTC-USD", # Bitcoin
            "ETH-USD", # Ethereum
            "GC=F",    # Ouro
            "CL=F",    # Petróleo
            "EURUSD=X" # Euro/Dolar
        ]

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Busca dados reais via yfinance.
        """
        logger.info(f"Buscando cotações para: {self.tickers}")
        results = []
        
        try:
            # Busca todos de uma vez para eficiência
            data = yf.download(self.tickers, period="1d", interval="1m", progress=False)
            
            if data.empty:
                logger.warning("Nenhum dado retornado pelo yfinance.")
                return []

            for ticker in self.tickers:
                try:
                    # Tenta pegar o último preço e volume
                    # Nota: yfinance retorna um dataframe multi-index se forem muitos tickers
                    import math
                    last_price = data['Close'][ticker].iloc[-1]
                    prev_price = data['Close'][ticker].iloc[-2] if len(data) > 1 else last_price
                    
                    if math.isnan(last_price):
                        continue
                        
                    change_pct = ((last_price - prev_price) / prev_price) * 100 if prev_price != 0 and not math.isnan(prev_price) else 0
                    
                    results.append({
                        "ticker": ticker,
                        "price": float(last_price),
                        "change_pct": float(change_pct),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Erro ao processar ticker {ticker}: {e}")
                    
        except Exception as e:
            logger.error(f"Erro fatal no yfinance fetch: {e}")
            
        return results

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transforma a cotação em um sinal de causalidade.
        Só gera sinal se houver variação significativa (> 0.5% por exemplo) 
        ou para registro histórico periódico.
        """
        ticker = raw_item["ticker"]
        price = raw_item["price"]
        change = raw_item["change_pct"]
        
        # Determina relevância baseada na volatilidade repentina
        relevance = min(1.0, abs(change) / 2.0) # Variação de 2% = Relevância 1.0
        
        # Categorização simples
        domain = "crypto" if "BTC" in ticker or "ETH" in ticker else "finance"
        if ticker == "GC=F" or ticker == "CL=F": domain = "commodities"

        return {
            "domain": domain,
            "type": "market_movement",
            "source": "yfinance",
            "title": f"Movimentação em {ticker}",
            "content": f"O ativo {ticker} está cotado a {price:.2f} com variação de {change:.2f}% no intervalo.",
            "relevance_score": relevance,
            "raw_data": raw_item,
            "metadata": {
                "ticker": ticker,
                "price": price,
                "change_pct": change
            }
        }

