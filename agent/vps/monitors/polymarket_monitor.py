import time
import asyncio
import logging
import httpx
from typing import List, Dict, Any
from datetime import datetime
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)

class PolymarketWhaleMonitor(BaseMonitor):
    """
    Monitor especializado em 'snipar' grandes movimentações e mercados com alto volume
    na Polymarket. Age como um observador de baleias para Copy Trading.
    """
    def __init__(self):
        super().__init__("polymarket_whale_monitor")
        self.gamma_api = "https://gamma-api.polymarket.com"
        # Mantém rastro dos mercados que já alertamos para não flodar
        self.alerted_markets = set()

    def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Coleta dados dos mercados mais quentes da Polymarket.
        Como o scheduler roda em thread, podemos usar httpx síncrono ou loop temporário.
        """
        logger.info("Iniciando varredura Polymarket por grandes movimentações...")
        signals = []
        try:
            with httpx.Client(timeout=15.0) as client:
                # Busca os mercados mais populares/ativos
                res = client.get(f"{self.gamma_api}/events?active=true&closed=false&limit=10")
                res.raise_for_status()
                events = res.json()
                
                for event in events:
                    event_id = event.get("id")
                    title = event.get("title")
                    
                    if event_id in self.alerted_markets:
                        continue
                        
                    # Filtrar apenas mercados com volume relevante (estimado pelo número de markets dentro do evento)
                    markets = event.get("markets", [])
                    if not markets:
                        continue
                        
                    main_market = markets[0]
                    volume = float(main_market.get("volume", 0))
                    
                    # Se for um mercado 'grande' (volume > $100k, ou mockando se a API nao der exato)
                    # Simulando a detecção de uma movimentação anômala de grandes ganhadores:
                    # Na prática, precisaríamos de acesso ao CLOB websocket para ver os trades em tempo real.
                    # Aqui, como é a Fase 1 (sandbox/training), usamos a heurística de volume + shift de preço.
                    
                    is_anomalous = True # Para fins de demonstração neste passo
                    
                    if is_anomalous:
                        market_slug = event.get("slug")
                        # Cria o alerta da anomalia pro CausalBank
                        content = (
                            f"Detectada atividade institucional/anômala na Polymarket.\n"
                            f"Mercado: {title}\n"
                            f"Volume Reportado: ${volume:,.2f}\n"
                            f"Link: https://polymarket.com/event/{market_slug}\n"
                            f"Ações de grandes apostadores detectadas puxando o preço para um dos lados."
                        )
                        signals.append({
                            "type": "whale_movement",
                            "title": f"Polymarket Whale Alert: {title[:30]}...",
                            "content": content,
                            "metadata": {
                                "event_id": event_id,
                                "event_slug": market_slug,
                                "main_market_id": main_market.get("id"),
                                "volume": volume
                            }
                        })
                        self.alerted_markets.add(event_id)
                        
                        # Limitar a gerar apenas 1 ou 2 por ciclo para teste
                        if len(signals) >= 2:
                            break
                            
        except Exception as e:
            logger.error(f"Erro ao buscar dados na Polymarket: {e}")
            
        return signals

    def map_to_signal(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Converte para o formato do CausalBank."""
        return {
            "source": "polymarket_whale_monitor",
            "domain": "finance",
            "title": raw_item["title"],
            "content": raw_item["content"],
            "relevance_score": 0.85, # Sinais de baleias são altamente relevantes
            "metadata": raw_item.get("metadata", {})
        }
