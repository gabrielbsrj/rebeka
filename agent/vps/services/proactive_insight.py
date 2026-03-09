# agent/vps/services/proactive_insight.py
import asyncio
import logging
from typing import Set
from memory.causal_bank import CausalBank
from interfaces.chat_manager import ChatManager

logger = logging.getLogger(__name__)

class ProactiveInsightService:
    """
    Proactive Insight Service — Os olhos e a voz proativa da Rebeka.
    Monitora o Banco de Causalidade e comunica eventos importantes ao usuário.
    """
    def __init__(self, bank: CausalBank, chat_manager: ChatManager, check_interval: int = 60):
        self.bank = bank
        self.chat_manager = chat_manager
        self.check_interval = check_interval
        self.seen_signal_ids: Set[str] = set()
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info("Serviço de Insights Proativos iniciado.")
        
        # Trigger inicial: Rotina de Despertar
        # Pequeno delay para garantir que os outros monitores já rodaram o primeiro ciclo
        await asyncio.sleep(5)
        await self.trigger_morning_routine()
        
        while self.is_running:
            try:
                await self._check_new_insights()
            except Exception as e:
                logger.error(f"Erro no loop de insights: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_new_insights(self):
        # 1. Buscar sinais recentes filtrados por domínio relevante
        signals = []
        for domain in ["finance", "crypto", "macro", "commodities", "survival"]:
            try:
                domain_signals = self.bank.get_similar_signals(domain=domain, limit=5)
                signals.extend(domain_signals)
            except Exception as e:
                logger.error(f"Erro ao buscar sinais de {domain}: {e}")
        
        # 2. Filtrar por relevância e novidade
        for sig in signals:
            sig_id = sig.get('id')
            if not sig_id or sig_id in self.seen_signal_ids:
                continue
            
            # Marcar como visto
            self.seen_signal_ids.add(sig_id)
            
            # Só fala se a relevância for alta (> 0.7)
            if sig.get("relevance_score", 0) > 0.7:
                logger.info(f"Sinal relevante detectado: {sig['title']}")
                
                # Formatar mensagem para o chat
                emoji = "📉" if "queda" in sig["content"].lower() or "baixa" in sig["content"].lower() else "📈"
                if sig["domain"] == "macro": emoji = "🏛️"
                if sig["domain"] == "crypto": emoji = "₿"
                if sig["domain"] == "survival": emoji = "⚠️🚨"
                
                prefix = "**Possível Crise de Sobrevivência**" if sig["domain"] == "survival" else "**Insight de Mercado**"
                message = f"{emoji} {prefix}: {sig['title']}\n\n{sig['content']}"
                
                # Se for macro ou financeiro forte, disparar pesquisa profunda autônoma
                if sig["relevance_score"] > 0.9:
                    message += "\n\n*Nota: Este movimento parece estrutural. Estou iniciando uma pesquisa profunda no Perplexity para entender os fundamentos.*"
                    
                    # Disparar ferramenta local via SyncServer
                    from vps.sync_server import manager
                    query = f"Analise o impacto de: {sig['title']}. Conteúdo: {sig['content']}. Como isso afeta o mercado de {sig['domain']} nos próximos dias?"
                    
                    # Usar create_task para não travar o loop de insights
                    asyncio.create_task(manager.dispatch_tool("perplexity_search", {"query": query}))
                
                self.chat_manager.push_insight(message)

    async def trigger_morning_routine(self):
        """Consolida os sinais mais relevantes e gera um relatório de boas-vindas."""
        logger.info("Executando Rotina de Despertar...")
        
        # Carregar persona se existir
        import yaml
        import os
        
        persona_name = "Rebeka"
        persona_style = "profissional"
        persona_path = "agent/config/persona.yaml"
        
        if os.path.exists(persona_path):
            try:
                with open(persona_path, "r", encoding="utf-8") as f:
                    persona_data = yaml.safe_load(f)
                    persona_name = persona_data.get("identity", {}).get("name", "Rebeka")
                    persona_style = persona_data.get("behavior", {}).get("style", "profissional")
            except Exception as e:
                logger.error(f"Erro ao carregar persona: {e}")
        
        # 1. Pegar sinais de alta relevância (últimas 24h)
        recent_signals = []
        for domain in ["finance", "crypto", "macro", "survival"]:
            sigs = self.bank.get_similar_signals(domain, limit=3)
            recent_signals.extend(sigs)
            
        # 2. Formatar o relatório de acordo com a persona
        if persona_style == "descontraida":
            report = f"🌅 **Bom dia! Aqui é a {persona_name} acordando!** 😊\n\nDei uma olhada em como o mundo está hoje. Saca só o resumo:\n\n"
        elif persona_style == "filosofica":
            report = f"🌅 **Uma nova manhã. {persona_name} online.**\n\nObservei as correntes de eventos globais enquanto o sol nascia. Este é o panorama da causalidade atual:\n\n"
        else:
            report = f"🌅 **Bom dia. {persona_name} Despertando.**\n\nSistemas iniciados. Contexto global verificado. Resumo atual:\n\n"
        
        survival_sigs = [s for s in recent_signals if s["domain"] == "survival"]
        if survival_sigs:
            report += "🚨 **Estado Interno**: Detectei alertas de recursos. Verifique meus créditos e saldos.\n"
        else:
            if persona_style == "descontraida":
                report += "✅ **Estado Interno**: Tudo 100% comigo! Pronta pra rodar.\n"
            else:
                report += "✅ **Estado Interno**: Sistemas operacionais e recursos estáveis.\n"
            
        market_sigs = [s for s in recent_signals if s["domain"] != "survival" and s["relevance_score"] > 0.8]
        if market_sigs:
            report += "\n📈 **Movimentos Críticos**:\n"
            for s in market_sigs[:3]:
                report += f"- {s['title']}\n"
        else:
            report += "\n📊 **Mercado**: Sem volatilidade extrema detectada nas últimas horas.\n"
            
        if persona_style == "descontraida":
            report += "\n*Tô de olho em tudo aqui. Te aviso se rolar alguma loucura no mercado! 😉*"
        elif persona_style == "filosofica":
            report += "\n*Continuarei minha observação silente. Notificarei quando novos padrões romperem o ruído.*"
        else:
            report += "\n*Estou em modo de monitoramento proativo. Avisarei assim que detectar novos padrões críticos.*"
        
        self.chat_manager.push_insight(report)
        logger.info(f"Relatório de despertar enviado ao chat como {persona_name}.")

    def stop(self):
        self.is_running = False

