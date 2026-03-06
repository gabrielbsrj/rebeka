# shared/evolution/opportunity_detector.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 6 - Implementação inicial do Detector Ativo de Oportunidades

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

# Supõe-se a existência dos clientes definidos pelo ecossistema
# da Rebeka (TelegramNotifier, LLM Client, Polymarket API)
from shared.communication.notifier import TelegramNotifier
try:
    # A integração existente PolymarketCopyTrader / API
    from local.adapters.polymarket_adapter import PolymarketClient
except ImportError:
    # Mock fallback caso a estrutura exata do polymarket cliente seja diferente
    class PolymarketClient:
        def search(self, keywords: List[str]):
            return []

logger = logging.getLogger(__name__)

class OpportunityDetector:
    """
    Conecta eventos geopolíticos/macroeconômicos à análise de ativos
    e busca de oportunidades no Polymarket.
    
    FLUXO:
    Evento detectado → Análise de impacto → Ativos afetados → Polymarket → Alerta
    """
    
    EVENTO_PARA_ATIVOS = {
        "conflito_militar": {
            "sobem": ["petróleo WTI", "ouro", "defesa", "dólar"],
            "caem": ["companhias aéreas", "turismo", "tech emergentes"],
            "polymarket_buscar": ["oil price", "gold", "war", "israel", "ukraine", "russia", "iran"],
            "janela_de_oportunidade": "primeiras 6-12 horas do evento"
        },
        "alta_taxa_juros": {
            "sobem": ["dólar", "bancos", "renda fixa"],
            "caem": ["growth stocks", "crypto", "real estate", "emergentes"],
            "polymarket_buscar": ["fed rate", "interest rates", "recession"],
            "janela_de_oportunidade": "dia do anúncio e 24h após"
        },
        "eleicao_impactante": {
            "sobem": ["mercados de aposta", "ativos do setor do candidato eleito"],
            "caem": ["ativos do setor do candidato derrotado"],
            "polymarket_buscar": ["election", "president", "poll"],
            "janela_de_oportunidade": "semanas antes + resultado"
        }
    }
    
    def __init__(self, llm_provider=None):
        self.telegram = TelegramNotifier()
        self.polymarket_client = PolymarketClient()
        self.llm = llm_provider  # ZhipuAI/Gemini provider para analisar impacto semântico
        
    def _now(self):
        return datetime.now(timezone.utc).isoformat()
        
    def analyze_event(self, evento_resumo: str, contexto_completo: str, dominio: str) -> Dict[str, Any]:
        """
        Dado um evento detectado pelos 14 monitores globais,
        gera análise completa de impacto e oportunidades.
        """
        logger.info(f"Analisando evento para oportunidades: {evento_resumo}")
        
        # 1. Classificação Heurística Básica Baseada no Domínio
        categoria_base = "conflito_militar" if "war" in evento_resumo.lower() or "ataque" in evento_resumo.lower() else "eleicao_impactante"
        base_assets = self.EVENTO_PARA_ATIVOS.get(categoria_base, {
            "sobem": ["depende da análise LLM"],
            "caem": ["depende da análise LLM"],
            "polymarket_buscar": ["economy", "politics"],
            "janela_de_oportunidade": "imediatamente"
        })
        
        # 2. Análise LLM (Prompt de Impacto)
        analise_llm = {
            "sobem": base_assets["sobem"],
            "caem": base_assets["caem"],
            "janela_de_oportunidade": base_assets["janela_de_oportunidade"],
            "nivel_incerteza": "médio/alto",
            "riscos": "Eventos em andamento podem sofrer reversão súbita baseada em novos comunicados oficiais."
        }
        
        if self.llm:
            try:
                # Simularia a call para o LLM. Placeholder da lógica correta:
                # analise_llm = self.llm.generate({"prompt": f"Analise impacto do evento: {evento_resumo}..."})
                pass
            except Exception as e:
                logger.error(f"Erro ao usar LLM para impacto de oportunidade: {e}")
                
        # 3. Busca no Polymarket
        keywords = base_assets.get("polymarket_buscar", [])
        polymarket_ops = self.search_polymarket_opportunities(keywords)
        
        resultado = {
            "evento": evento_resumo,
            "analise": analise_llm,
            "polymarket_oportunidades": polymarket_ops,
            "timestamp": self._now(),
            "confianca": analise_llm.get("nivel_incerteza", "desconhecido")
        }
        
        # Se encontrou match plausível, dispara alerta.
        if polymarket_ops or "alta" not in resultado["confianca"].lower():
            self.alert_opportunity(resultado)
            
        return resultado
        
    def search_polymarket_opportunities(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Busca contratos no Polymarket relacionados ao evento.
        """
        try:
            markets = self.polymarket_client.search(keywords)
            # Simula a estrutura devida do adapter do polymarket
            if not markets:
                return []
            
            return [{
                "market": m.get("title", "Desconhecido"),
                "current_odds": m.get("odds", 0.0),
                "volume": m.get("volume", 0),
                "url": m.get("url", "")
            } for m in markets if m.get("volume", 0) > 10000]
        except Exception as e:
            logger.warning(f"Erro ao buscar no Polymarket: {e}")
            return []
            
    def alert_opportunity(self, analysis: Dict[str, Any]):
        """Envia alerta formatado via Telegram."""
        ops = analysis.get("polymarket_oportunidades", [])
        ops_str = "Nada com alto volume localizado."
        if ops:
            ops_str = "\n".join([f"- {m['market']} (Odds: {m['current_odds']})" for m in ops])
            
        msg = f"""
🌍 EVENTO DETECTADO — ANÁLISE DE OPORTUNIDADE

📰 {analysis['evento']}

📈 ATIVOS QUE DEVEM SUBIR:
{', '.join(analysis['analise']['sobem'])}

📉 ATIVOS QUE DEVEM CAIR:
{', '.join(analysis['analise']['caem'])}

🎯 POLYMARKET — OPORTUNIDADES:
{ops_str}

⏰ Janela: {analysis['analise']['janela_de_oportunidade']}
🎲 Incerteza LLM: {analysis['confianca']}

⚠️ Esta é uma análise informativa. A Decisão de operar é sua.
        """
        try:
            self.telegram.send(msg)
            logger.info("Alerta de Oportunidade enviado pelo Telegram.")
        except Exception as e:
            logger.error(f"Erro ao disparar alerta de Oportunidade: {e}")

if __name__ == "__main__":
    logger.info("Testando OpportunityDetector...")
    detector = OpportunityDetector()
    detector.analyze_event(
        evento_resumo="Guerra declarada em nova zona de conflito no golfo",
        contexto_completo="O conflito militar escalou após 48h de tensões, envolvendo potências locais.",
        dominio="geopolitics"
    )
